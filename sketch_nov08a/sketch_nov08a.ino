#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <MFRC522.h>
#include <WebSocketsClient.h>
#include <WiFi.h>

#define I2C_ADDRESS 0x27
#define LCD_COLUMNS 16
#define LCD_ROWS 2
LiquidCrystal_I2C lcd(I2C_ADDRESS, LCD_COLUMNS, LCD_ROWS);

Servo servoIn, servoOut;

// Các chân sensor
#define ir_back 32
#define ir_car1 33
#define ir_car2 25
#define ir_car3 26

#define SS_PIN 5
#define RST_PIN 4
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Các chân cho cảm biến lửa và chuông
#define fireSensorPin 34
#define buzzerPin 27

const char* ssid = "your_SSID";          // Thay đổi với SSID WiFi của bạn
const char* password = "your_PASSWORD";   // Thay đổi với mật khẩu WiFi của bạn
IPAddress local_IP(192, 168, 43, 2);      // Địa chỉ IP cố định
IPAddress gateway(192, 168, 43, 1);       // Địa chỉ gateway (router)
IPAddress subnet(255, 255, 255, 0);       // Địa chỉ subnet

int S1 = 0, S2 = 0, S3 = 0;
int slot = 3; // Số lượng chỗ trống
int flag = 1; // Điều khiển cổng ra
bool carEntered = false; // Xe vào thông qua RFID
unsigned long openTime = 0;
bool isOpen = false;

// Khởi tạo WebSocket client
WebSocketsClient webSocket;

// Địa chỉ WebSocket Server Python
const char* serverIP = "192.168.43.39";   // Địa chỉ IP của WebSocket server Python
const uint16_t serverPort = 5000;         // Cổng WebSocket

void onWebSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    String message = String((char*)payload);  // Chuyển byte payload thành String
    Serial.printf("Received message: %s\n", message.c_str());

    if (type == WStype_DISCONNECTED) {
        Serial.println("[WS] Disconnected");
    } else if (type == WStype_CONNECTED) {
        Serial.println("[WS] Connected");
    } else if (type == WStype_TEXT) {
        if (message.indexOf("Access granted") >= 0) {
            openDoor();  // Mở cửa khi thanh toán thành công
        } else if (message.indexOf("exit_parking") >= 0) {
            closeDoor();  // Đóng cửa khi người dùng rời khỏi bãi đỗ
        } else {
            // Xử lý các lệnh khác từ WebSocket
            handleCommand(message);
        }
    }
}

void handleCommand(const String& command) {
    if (command == "open_in") {
        servoIn.write(180); // Mở cửa vào
    } else if (command == "close_in") {
        servoIn.write(90); // Đóng cửa vào
    } else if (command == "open_out") {
        servoOut.write(180); // Mở cửa ra
    } else if (command == "close_out") {
        servoOut.write(90); // Đóng cửa ra
    } else if (command == "buzzer_on") {
        digitalWrite(buzzerPin, HIGH); // Bật chuông
    } else if (command == "buzzer_off") {
        digitalWrite(buzzerPin, LOW); // Tắt chuông
    }
}

void setup() {
    Serial.begin(115200);
    delay(1500);
    Wire.begin(21, 22);
    lcd.init();
    lcd.backlight();

    SPI.begin();
    mfrc522.PCD_Init();

    pinMode(ir_car1, INPUT);
    pinMode(ir_car2, INPUT);
    pinMode(ir_car3, INPUT);
    pinMode(ir_back, INPUT);
    pinMode(fireSensorPin, INPUT);
    pinMode(buzzerPin, OUTPUT);
    digitalWrite(buzzerPin, LOW);

    servoIn.attach(13);
    servoOut.attach(12);
    servoIn.write(90); // Đóng cửa
    servoOut.write(90); // Đóng cửa

    lcd.setCursor(0, 0);
    lcd.print(" Car Parking Sys ");
    delay(2000);
    lcd.clear();

    Read_Sensor();
    updateSlotCount();

    WiFi.config(local_IP, gateway, subnet);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("Connected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    webSocket.begin(serverIP, serverPort);
    webSocket.onEvent(onWebSocketEvent);

    servoIn.write(0); // Đảm bảo servo đóng cửa ban đầu
    servoOut.write(0);

    Serial.println("Scan a RFID tag...");
}

void loop() {
    webSocket.loop(); // Xử lý các sự kiện WebSocket

    Read_Sensor();
    updateSlotCount();

    static int lastSlot = -1;
    if (slot != lastSlot) {
        updateLCD();
        lastSlot = slot;
    }

    sendSensorStatus();

    if (isNewCardPresent()) {
        String rfid_code = getRFIDCode();
        if (!rfid_code.isEmpty()) {
            Serial.print("RFID Code: ");
            Serial.println(rfid_code);

            String message = "rfid_code:" + rfid_code;
            webSocket.sendTXT(message);

            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
        }
        delay(500);
    }

    if (digitalRead(ir_back) == HIGH && flag == 1) {
        if (!isOpen) {
            servoOut.write(180); // Mở cửa ra
            openTime = millis() + 4000;
            isOpen = true;
        }
    } 

    if (isOpen && millis() > openTime) {
        servoOut.write(90); // Đóng cửa
        updateSlotCount();
        isOpen = false;
        flag = 0;
        Serial.println("Car exited. Gates closed.");
    } else if (digitalRead(ir_back) == LOW) {
        flag = 1;
    }
}

bool isNewCardPresent() {
    return mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial();
}

String getRFIDCode() {
    String rfid_code = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        rfid_code += String(mfrc522.uid.uidByte[i], HEX);
    }
    rfid_code.toUpperCase();
    return rfid_code;
}

void openDoor() {
    servoIn.write(90);  // Mở cửa vào
    servoOut.write(90); // Mở cửa ra
    delay(2000);
    closeDoor();
}

void closeDoor() {
    servoIn.write(0);  // Đóng cửa vào
    servoOut.write(0); // Đóng cửa ra
}

void sendSensorStatus() {
    String message = "update_slot:1:" + String(S1 ? "occupied" : "available");
    webSocket.sendTXT(message);
    message = "update_slot:2:" + String(S2 ? "occupied" : "available");
    webSocket.sendTXT(message);
    message = "update_slot:3:" + String(S3 ? "occupied" : "available");
    webSocket.sendTXT(message);
}

void Read_Sensor() {
    S1 = digitalRead(ir_car1);
    S2 = digitalRead(ir_car2);
    S3 = digitalRead(ir_car3);
}

void updateSlotCount() {
    slot = 3 - (S1 + S2 + S3);
}

void updateLCD() {
    lcd.setCursor(0, 0); lcd.print("Slots: ");
    lcd.print(slot);   
    lcd.print("   ");
    
    lcd.setCursor(0, 1);
    lcd.print(S1 ? "S1: O " : "S1: A ");
    lcd.print(S2 ? "S2: O " : "S2: A ");
    lcd.print(S3 ? "S3: O " : "S3: A ");
}
