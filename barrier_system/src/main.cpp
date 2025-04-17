#include <ESP8266WiFi.h>
#include <Servo.h>        
#include <ArduinoJson.h>
#include <ESP8266WebServer.h>

// const char* ssid = "Velnet1617";
// const char* password = "map111617ok";
const char* ssid = "Barrier";
const char* password = "poiuytre";
#define RED_PIN    D5
#define GREEN_PIN  D6
#define BLUE_PIN   D2

ESP8266WebServer server(80);
Servo myservo;

bool barrierActive = false;
bool manualOpen = false;
unsigned long barrierOpenedAt = 0;

void setRGB(bool r, bool g, bool b) {
  digitalWrite(RED_PIN, !r);  
  digitalWrite(GREEN_PIN, !g);
  digitalWrite(BLUE_PIN, !b);
}

void showOpen() {
  
  setRGB(false, false, true);
}

void showClosed() {
  
  setRGB(false, true, false);
}

void showTestFlash() {
  setRGB(true, false, false);
  
  delay(300);
  showClosed(); 
}

void handleOptions() {
  server.send(200, "application/json", "{\"message\": \"OK\"}");
  showTestFlash();

}
void handleControl() {
  if (server.method() != HTTP_POST) {
    server.send(405, "application/json", "{\"message\": \"Метод не поддерживается\"}");
    return;
  }

  String body = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "application/json", "{\"message\": \"Неверный JSON\"}");
    return;
  }

  int command = doc["status"];

  if (command == 0) {  
    if (barrierActive) {
      server.send(200, "application/json", "{\"message\": \"Шлагбаум уже открыт\"}");
      Serial.println("Попытка повторно открыть — проигнорировано");
      return;
    }
    showOpen();
    myservo.write(90);
    barrierOpenedAt = millis();
    barrierActive = true;
    manualOpen = false;
    server.send(200, "application/json", "{\"message\": \"Открыт на 15 сек\"}");
    Serial.println("Шлагбаум открыт на 15 секунд");
  }

  else if (command == 1) {  
    if (barrierActive) {
      server.send(200, "application/json", "{\"message\": \"Шлагбаум уже открыт\"}");
      Serial.println("Попытка повторно открыть вручную — проигнорировано");
      return;
    }
    showOpen();
    myservo.write(90);
    barrierActive = true;
    manualOpen = true;
    server.send(200, "application/json", "{\"message\": \"Открыт вручную\"}");
    Serial.println("Шлагбаум открыт вручную");
  }

  else if (command == 2) {  
    if (!barrierActive) {
      server.send(200, "application/json", "{\"message\": \"Шлагбаум уже закрыт\"}");
      Serial.println("Попытка закрыть уже закрытый — проигнорировано");
      return;
    }
    showClosed();
    myservo.write(0);
    barrierActive = false;
    manualOpen = false;
    server.send(200, "application/json", "{\"message\": \"Закрыт вручную\"}");
    Serial.println("Шлагбаум закрыт вручную");
  }

  else {
    server.send(400, "application/json", "{\"message\": \"Неверная команда\"}");
  }
}

void setup() {
  Serial.begin(115200);
  myservo.attach(13, 544, 2400);
  Serial.print("Подключение к WiFi");
  myservo.write(0);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi подключен");
  Serial.print("IP адрес: ");
  Serial.println(WiFi.localIP());

  server.on("/servo", HTTP_POST, handleControl);
  server.begin();
  Serial.println("HTTP сервер запущен");

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  showClosed(); 
  server.on("/servo", HTTP_OPTIONS, handleOptions);
}

void loop() {
  server.handleClient();

  if (barrierActive && !manualOpen && (millis() - barrierOpenedAt >= 15000)) {
    showClosed();
    myservo.write(0);
    barrierActive = false;
    Serial.println("Шлагбаум закрыт автоматически через 15 секунд");
  }
}






// #include "ESP8266WiFi.h"

// // WiFi parameters to be configured
// const char* ssid = "Barrier";
// const char* password = "poiuytre";

// void setup(void)
// {
//   Serial.begin(9600);
//   WiFi.begin(ssid, password);

//   // while wifi not connected yet, print '.'
//   // then after it connected, get out of the loop
//   while (WiFi.status() != WL_CONNECTED) {
//      delay(500);
//      Serial.print(".");
//   }
//   Serial.println("");
//   Serial.println("WiFi connected");
//   Serial.println(WiFi.localIP());

// }
// void loop() {
//   // Nothing
// }