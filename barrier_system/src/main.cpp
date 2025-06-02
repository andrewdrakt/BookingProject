#include <ESP8266WiFi.h>
#include <Servo.h>        
#include <ArduinoJson.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include "nonpublic.h"


#define RED_PIN    D5
#define GREEN_PIN  D6
#define BLUE_PIN   D2

ESP8266WebServer server(80);
Servo myservo;

bool barrierActive = false;
bool manualOpen = false;
unsigned long barrierOpenedAt = 0;
String deviceId;

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
  return;
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
    return;
  }  else if (command == 1) {  
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
    return;
  }  else if (command == 2) {  
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
    return;
  }  else {
    server.send(400, "application/json", "{\"message\": \"Неверная команда\"}");
    return;
  }
}

void checkCommandFromServer() {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient https;

  String url = "https://parkingbooking.online:8443/api/commands/?device_id=" + deviceId;
  if (https.begin(client, url)) {
    int httpCode = https.GET();
    
    if (httpCode == 200) {
      String response = https.getString();
      StaticJsonDocument<200> doc;
      DeserializationError err = deserializeJson(doc, response);
      if (!err) {
        if (doc.containsKey("status")) {
          int cmd = doc["status"];
          if (cmd == 0 || cmd == 1 || cmd == 2) {
            Serial.printf("Получена команда: %d\n", cmd);
            if (cmd == 0) {
              showOpen();
              myservo.write(90);
              barrierOpenedAt = millis();
              barrierActive = true;
              manualOpen = false;
              Serial.println("Открыт по команде с сервера");
            } else if (cmd == 1) {
              showOpen();
              myservo.write(90);
              barrierActive = true;
              manualOpen = true;
              Serial.println("Открыт вручную по команде с сервера");
            } else if (cmd == 2) {
              showClosed();
              myservo.write(0);
              barrierActive = false;
              manualOpen = false;
              Serial.println("Закрыт по команде с сервера");
            }
          }
        }
      }
    } else {
      Serial.printf("Ответ HTTP: %d\n", httpCode);
    }
    https.end();
  }
}



void setup() {
  Serial.begin(115200);
  myservo.attach(13, 544, 2400);
  myservo.write(0);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi подключён");
  Serial.println("IP: " + WiFi.localIP().toString());
  
  deviceId = WiFi.macAddress();
  deviceId.replace(":", "");
  Serial.print("MAC ESP: ");
  Serial.println(deviceId);
  server.on("/servo", HTTP_POST, handleControl);
  server.on("/servo", HTTP_OPTIONS, handleOptions);
  server.begin();

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  showClosed();
}
void loop() {
  server.handleClient();
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 3000) {
    lastCheck = millis();
    checkCommandFromServer();
  }

  if (barrierActive && !manualOpen && (millis() - barrierOpenedAt >= 15000)) {
    showClosed();
    myservo.write(0);
    barrierActive = false;
    Serial.println("Автоматическое закрытие через 15 сек");
  }
}


// // To check connection, comment code above and uncomment below
// #include "ESP8266WiFi.h"
// #include "nonpublic.h"
// // WiFi parameters to be configured

// void setup(void)
// {
//   Serial.begin(9600);
//   WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

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