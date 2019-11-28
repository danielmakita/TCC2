import sys
import threading
import time

from struct import *
from RF24 import *
from RF24Network import *

from datetime import datetime

from telegram.ext import Updater, InlineQueryHandler, CommandHandler
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QTimer

import sys
from urllib.request import urlopen

# CE Pin, CSN Pin, SPI Speed
radio = RF24(RPI_V2_GPIO_P1_15, RPI_V2_GPIO_P1_24, BCM2835_SPI_SPEED_8MHZ)
network = RF24Network(radio)

octlit = lambda n:int(n, 8)

# Endereco do no coordenador 00
this_node = octlit("00")
# Endereco do filho do coordenador 01
other_node = octlit("01")

radio.begin()
time.sleep(0.1) # Delay para garantir que o radio foi inicializado
network.begin(110, this_node) # Configurando canal 110
radio.printDetails() # Imprimindo detalhes do radio

nodeAddrs = [1, 9, 17] # Enderecos em decimal dos nos da rede

#ThingSpeak API write key O2TR9UYCP211DHN2
thingSpeakAPI = 'O2TR9UYCP211DHN2'
baseURL = 'https://api.thingspeak.com/update?api_key=%s' % thingSpeakAPI 
	
g_timeStamp = ''
g_statusTime = ''
g_output=''
g_temp01 = 0
g_humid01 = 0
g_temp011 = 0
g_humid011 = 0
g_temp021 = 0
g_humid021 = 0

# Metodo para receber e decodificar o comando
def receiveDecodeCommand():
    while True:
        command, node , parameter = map(int, input("Command and parameter: ").split())
        #print('command: ', command, 'node: ', node, 'parameter: ', parameter)
        node = octlit(str(node))
        
        if command == 1 and (node in nodeAddrs): # Configurando Arduino como Slave
            print('Comando para configurar Arduino: ', node, ' como SLAVE')
            sendCommand(command, node, 0)
        elif command == 2 and (node in nodeAddrs): # Configurando Arduino como Mestre
            print('Comando para configurar Arduino: ', node, ' como MESTRE')
            sendCommand(command, node, 0)
        elif command == 10 and (node in nodeAddrs): # Solicitando x leituras do Arduino
        		print('Solicita: ', parameter, ' leituras dos sensores do Arduino: ', node)
        		sendCommand(command, node, parameter)
        elif command == 20 and (node in nodeAddrs): # Alterando a frequencia de leitura do Arduino
        		print('Alterar frequencia de leitura do Arduino: ', node, 'para: ', parameter, 'seg')
        		sendCommand(command, node, parameter)
        else: 
            print("Digite um Comando ou No valido")

# Metodo criado para enviar comandos 
def sendCommand(command, node, parameter):
    payload = pack('<LL', command, parameter)
    ok = network.write(RF24NetworkHeader(node), payload)
    if ok == False :
    	print('Nao foi possivel enviar comando ao Arduino: ', node)

# Metodo para receber dados
def receivePayload():
	global g_temp01, g_humid01, g_temp011, g_humid011, g_temp021, g_humid021, g_timeStamp
	while True:
		network.update()
		while network.available():
			header, payload = network.read(8) # frame de 8 bytes 
			temperature, humidity = unpack('<LL', bytes(payload)) # 1 byte de temperatura e 1 de umidade
			if header.from_node != 0:
				dateTimeObj = datetime.now()
				dateObj = dateTimeObj.date()
				timeObj = dateTimeObj.time()
				g_timeStamp = dateObj.strftime('%b %d %Y ') + timeObj.strftime('%H:%M:%S - ')
				print( g_timeStamp + 'Received Temperature:\t', temperature, '\tHumidity: ', humidity, '\tfrom Node: ', oct(header.from_node))			
				
				if header.from_node == 1:
					g_temp01 = temperature
					g_humid01 = humidity
				elif header.from_node == 9:
					g_temp011 = temperature
					g_humid011 = humidity
				elif header.from_node == 17:
					g_temp021 = temperature
					g_humid021 = humidity
				
				g_output = str(g_timeStamp) + 'Node 01 Temperature ' + str(g_temp01) + ' Humidity: ' + str(g_humid01) + '\n\n' + str(g_timeStamp) + 'Node 011 Temperature ' + str(g_temp011) + ' Humidity: ' + str(g_humid011) + '\n\n' + str(g_timeStamp) + 'Node 021 Temperature ' + str(g_temp021) + ' Humidity: ' + str(g_humid021) + '\n\n' 	

# Interface Grafica
class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()# Call the inherited classes __init__ method
        uic.loadUi('TCC.ui', self) #Load the .ui file

        self.sendBtn = self.findChild(QtWidgets.QPushButton, 'sendButton')
        self.sendBtn.clicked.connect(self.sendButtonPressed)

        self.readBtn = self.findChild(QtWidgets.QPushButton, 'readButton')
        self.readBtn.clicked.connect(self.readButtonPressed)

        self.commandRaspberryTxt = self.findChild(QtWidgets.QTextBrowser, 'commandRaspberryText')
        self.commandTelegramTxt = self.findChild(QtWidgets.QTextBrowser, 'commandTelegramText')
        self.outputTxt = self.findChild(QtWidgets.QTextBrowser, 'outputText')

        self.cmdBox = self.findChild(QtWidgets.QComboBox, 'commandBox')
        self.nodeBox = self.findChild(QtWidgets.QComboBox, 'nodeBox')
        self.paramBox = self.findChild(QtWidgets.QComboBox, 'parameterBox')

        self.qTimer = QTimer()
        self.qTimer.setInterval(5000)
        self.qTimer.timeout.connect(self.readButtonPressed)
        self.qTimer.start()

        self.show() # Mostrar a interface
        
    # Metodo chamado quando botao send e pressionado
    def sendButtonPressed(self):
        if self.cmdBox.currentText() == 'Read':
            cmdOutput = 'Requesting: ' + self.paramBox.currentText() + 'x sample from Arduino: ' +  self.nodeBox.currentText()
            sendCommand(10, int(self.nodeBox.currentText()), int(self.paramBox.currentText()))
        elif self.cmdBox.currentText() == 'Slave':
            cmdOutput = 'Setting Arduino: ' + self.nodeBox.currentText() + ' as Slave'
            sendCommand(1, int(self.nodeBox.currentText()), 0)
        elif self.cmdBox.currentText() == 'Master':
            cmdOutput = 'Setting Arduino: '+ self.nodeBox.currentText() + ' as Master' + ' with sampling frequency of ' + self.paramBox.currentText() + ' seconds'
            sendCommand(2, int(self.nodeBox.currentText()), int(self.paramBox.currentText()))
        self.commandRaspberryTxt.setText(cmdOutput)

    # Metodo chamado quando o botao read e pressionado
    def readButtonPressed(self):        
        global g_temp01, g_humid01, g_temp011, g_humid011, g_temp021, g_humid021, g_timeStamp, g_output, g_statusTime
        g_output = '\n\n' + str(g_timeStamp) + 'Node 01 Temperature ' + str(g_temp01) + ' Humidity: ' + str(g_humid01) + '\n\n' + str(g_timeStamp) + 'Node 011 Temperature ' + str(g_temp011) + ' Humidity: ' + str(g_humid011) + '\n\n' + str(g_timeStamp) + 'Node 021 Temperature ' + str(g_temp021) + ' Humidity: ' + str(g_humid021) + '\n\n' 	
        self.outputText.setText(g_output)				
        self.commandTelegramText.setText('\nLast Status request from Telegram: \n\n' + g_statusTime)
    
                                    
# Metodo para retornar log de horario
def status(update, context):
        global g_statusTime
        dateTimeObj = datetime.now()
        dateObj = dateTimeObj.date()
        timeObj = dateTimeObj.time()
        g_statusTime = dateObj.strftime('%b %d %Y ') + timeObj.strftime('%H:%M:%S')
        update.message.reply_text(g_output)
        
# Metodo inicializador da GUI
def GUI():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()
    
# Metodo que envia os dados para o ThingSpeak
def thingSpeak():
    global g_temp01, g_humid01, g_temp011, g_humid011, g_temp021, g_humid021
    while True:
        conn = urlopen(baseURL + '&field1=%s&field2=%s&field3=%s&field4=%s&field5=%s&field6=%s' % (g_temp01, g_humid01, g_temp011, g_humid011, g_temp021, g_humid021))
        #print (conn.read())
        conn.close()
        time.sleep(20)
        
def main():
    #Thread para receber comandos do usuario por linha de comando
    #input_thread = threading.Thread(target = receiveDecodeCommand)
    #input_thread.daemon = True
    #input_thread.start()
    
    #ThingSpeak Thread
    thingSpeak_thread = threading.Thread(target = thingSpeak)
    thingSpeak_thread.daemon = True
    thingSpeak_thread.start()

    #Thread para receber dados
    receive_thread = threading.Thread(target = receivePayload)
    receive_thread.daemon = True
    receive_thread.start()

    #GUI Thread
    gui_thread = threading.Thread(target = GUI)
    gui_thread.daemon = True
    gui_thread.start() 
	    
    #Thread do Telegram 
    updater = Updater('939667550:AAG1IpdILnWjyjvcGQEULCCG_6AUNFfNZlg', use_context = True)
    updater.dispatcher.add_handler(CommandHandler('status', status))
    updater.start_polling()

    while True:
        pass
		
if __name__ == "__main__":
    main()