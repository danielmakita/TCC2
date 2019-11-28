#include <RF24Network.h>
#include <RF24.h>
#include <SPI.h>

#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

#define DHTPIN 3     // Digital pin connected to the DHT sensor 
#define DHTTYPE    DHT11     // DHT 11

RF24 radio(7,8);                // nRF24L01(+) radio attached using Getting Started board 

RF24Network network(radio);      // Network uses that radio
const uint16_t this_node = 021;    // Address of our node in Octal format ( 04,031, etc)
const uint16_t other_node = 00;   // Address of the other node in Octal format

uint32_t readingDelay = 4000;

struct payload_t {                 // Structure of our payload
  unsigned long command;
  unsigned long parameter;
};

struct payload_to_send{
  unsigned long temperature;
  unsigned long humidity;  
};
boolean slave = false; //By default Arduino is the slave of the sensor network

/* DHT */
DHT_Unified dht(DHTPIN, DHTTYPE);
uint32_t delayMS;
payload_to_send payload_sensor = {30, 90};

void initDHT(){
  dht.begin();
  sensor_t sensor;
  dht.temperature().getSensor(&sensor);
  dht.humidity().getSensor(&sensor);
  delayMS = sensor.min_delay / 1000;
}

void readDHT(){
  sensors_event_t event;
  dht.temperature().getEvent(&event);
  
  payload_sensor.temperature = event.temperature;
  if (isnan(event.temperature)) {
    Serial.println(F("Error reading temperature!"));
  }

  // Get humidity event and print its value.
  dht.humidity().getEvent(&event);
  payload_sensor.humidity = event.relative_humidity;
  if (isnan(event.relative_humidity)) {
    Serial.println(F("Error reading humidity!"));
  }
}

void sendData(uint8_t samples){
  int i=0;
  RF24NetworkHeader header2(/*to node*/ other_node);
  Serial.print("Sending my data from node 01 to node 00 .."); 
  
  for(i = 0; i < samples; i++){
    bool ok = network.write(header2,&payload_sensor,sizeof(payload_sensor));
    if (ok){
      Serial.print(" Temp: ");
      Serial.print(payload_sensor.temperature);
      Serial.print(" Humidity: ");
      Serial.println(payload_sensor.humidity);
    }
    else
      Serial.println(" failed..");
    delay(100);
  }
}


void setup(void){
  Serial.begin(115200);
  Serial.println("RF24Network/examples/helloworld_rx/");
 
  SPI.begin();
  radio.begin();
  network.begin(/*channel*/ 110, /*node address*/ this_node);
  
  initDHT(); // Initializing DHT sensor
}


void loop(void){
  network.update();                  // Check the network regularly

  while (network.available()){     // Is there anything ready for us?
    RF24NetworkHeader headerR;        // If so, grab it and print it out
    payload_t payload;
    network.read(headerR,&payload,sizeof(payload));

    Serial.print("Received command: ");
    Serial.print(payload.command);
    Serial.print(" param: ");
    Serial.print(payload.parameter);
    Serial.print(" from: ");
    Serial.println(headerR.from_node);
    
    if (payload.command == 1){
      slave = true;
      Serial.println("Arduino changing to Slave mode - Answer by RPI request");
    }
    else if (payload.command == 2) {
      slave = false;
      readingDelay = payload.parameter * 1000; //Reading
      Serial.print("Arduino changing to Master mode - Sending periodically freq ");
      Serial.print(readingDelay);
      Serial.println("x ms");
    }
    else if (payload.command == 10 && slave) {
      Serial.println("Arduino received reading request from RPI");
      Serial.println(payload.parameter);
      sendData(payload.parameter);
    }
    /*else if (payload.command == 20 && !slave) {
      Serial.println("Arduino received freq changing command");  
      readingDelay = payload.parameter; //Reading
    }*/
    else{
      Serial.println("Invalid command or invalid command given Arduinos operational mode");  
    }
  }
  
  if(!slave){ /* Se o arduino for Mestre, enviar periodicamente os dados */
    readDHT();  
    sendData(1);
  }
    
  delay(readingDelay);

}
