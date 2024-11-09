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
#define ir_car1 26
#define ir_car2 25
#define ir_car3 33

#define SS_PIN 5
#define RST_PIN 2
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Các chân cho cảm biến lửa và chuông
#define fireSensorPin 34
#define buzzerPin 27

const char* ssid = "AndroidAPD0B9";  // Thay đổi với SSID WiFi của bạn
const char* password = "khanh111";   // Thay đổi với mật khẩu WiFi của bạn
IPAddress local_IP(192, 168, 43, 2); // Địa chỉ IP cố định
IPAddress gateway(192, 168, 43, 1);   // Địa chỉ gateway (router)
IPAddress subnet(255, 255, 255, 0);   // Địa chỉ subnet
int S1 = 0, S2 = 0, S3 = 0;
int lastS1 = -1, lastS2 = -1, lastS3 = -1; // Biến lưu trạng thái trước đó
int slot = 3; // Số lượng chỗ trống
int flag = 1; // Điều khiển cổng ra
bool carEntered = false; // Xe vào thông qua RFID
unsigned long servoCloseTime = 0;
unsigned long fireOpenTime = 0; // Thời gian mở cửa khi có lửa
bool fireDetected = false; // Cờ báo có lửa

// Khởi tạo WebSocket client
WebSocketsClient webSocket;

// Địa chỉ WebSocket Server Python
const char* serverIP = "192.168.43.39"; // Địa chỉ IP của WebSocket server Python
const uint16_t serverPort = 5000; // Cổng WebSocket

// Cập nhật thời gian gửi dữ liệu qua WebSocket
unsigned long lastSendTime = 0; // Thời gian lần gửi trước đó
unsigned long sendInterval = 1000; // Đặt khoảng thời gian giữa các lần gửi (1000 ms = 1 giây)

void onWebSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    String message = String((char*)payload);  // Chuyển byte payload thành String

    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("[WS] Connected");
            break;
        case WStype_TEXT:
            Serial.print("[WS] Received message: ");
            Serial.println(message);

            // Phân biệt các loại tin nhắn từ server
            if (message.indexOf("Access granted") >= 0) {
                Serial.println("Access granted. Opening door...");
                openDoor();  // Mở cửa khi thanh toán thành công
            }
            else if (message.indexOf("exit_parking") >= 0) {
                Serial.println("User exit registered. Closing door...");
                closeDoor();  // Đóng cửa khi người dùng rời khỏi bãi đỗ
            }
            else if (message.indexOf("Slot") >= 0)
            {
              Serial.println(message);
            }
            break;
    }
}

// Kết nối WiFi và WebSocket
void setup() {
    Serial.begin(9600);
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

    // Cấu hình địa chỉ IP tĩnh
    WiFi.config(local_IP, gateway, subnet);
  
    // Kết nối WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("Connected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Bắt đầu WebSocket
    webSocket.begin(serverIP, serverPort);
    webSocket.onEvent(onWebSocketEvent);

    // Thiết lập vị trí ban đầu của servo là 0 độ (cửa đóng)
    servoIn.write(0);  // Đảm bảo servo ở vị trí 0 độ (cửa đóng) khi bắt đầu
    servoOut.write(0);  // Đảm bảo cửa ra đóng

    Serial.println("Scan a RFID tag...");
}

void loop() {
    webSocket.loop(); // Xử lý các sự kiện WebSocket

    Read_Sensor();
    updateSlotCount();

    // Cập nhật LCD khi số lượng chỗ trống thay đổi
    static int lastSlot = -1;
    if (slot != lastSlot) {
        updateLCD();
        lastSlot = slot; // Cập nhật số chỗ trước đó
    }

    // Kiểm tra và gửi trạng thái các cảm biến IR lên WebSocket chỉ khi có thay đổi
    if (millis() - lastSendTime > sendInterval) {
        sendSensorStatusIfChanged();
        lastSendTime = millis(); // Cập nhật thời gian gửi
    }

    // Kiểm tra xem có thẻ RFID nào được quét không
    if (isNewCardPresent()) {
        // Lấy và xử lý UID của thẻ RFID
        String rfid_code = getRFIDCode();
        if (rfid_code != "") {
            // In ra mã RFID
            Serial.print("RFID Code: ");
            Serial.println(rfid_code);

            // Gửi mã RFID qua WebSocket
            String message = "rfid_code:" + rfid_code;
            webSocket.sendTXT(message);  // Gửi tin nhắn với mã RFID

            // Dừng việc quét thẻ sau khi đã gửi
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
        }
        delay(500);  // Thời gian chờ giữa các lần quét
    }

    // Kiểm tra cảm biến IR cho việc ra xe
    static unsigned long openTime = 0; // Thời gian mở cửa
    static bool isOpen = false; // Cờ để kiểm tra cửa đang mở

    if (digitalRead(ir_back) == HIGH && flag == 1) {
        if (!isOpen) {
            servoOut.write(180); // Mở cửa ra
            openTime = millis() + 4000; // Đặt thời gian mở
            isOpen = true;
        }
    } 
    if (isOpen && millis() > openTime) {
        servoOut.write(90); // Đóng cửa
        updateSlotCount();
        isOpen = false; // Reset cờ
        flag = 0; // Đặt flag để tránh mở liên tục
        Serial.println("Car exited. Gates closed.");
    } else if (digitalRead(ir_back) == LOW) {
        flag = 1; // Reset flag
    }
}

// Hàm kiểm tra thẻ mới có xuất hiện hay không
bool isNewCardPresent() {
  return mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial();
}

// Hàm lấy mã RFID từ thẻ quét
String getRFIDCode() {
  String rfid_code = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfid_code += String(mfrc522.uid.uidByte[i], HEX);  // Chuyển mỗi byte thành chuỗi hex
  }
  rfid_code.toUpperCase();  // Chuyển mã RFID về chữ in hoa
  return rfid_code;
}

// Hàm mở cửa (điều khiển servo)
void openDoor() {
  servoIn.write(90);  // Mở cửa (servo quay 90 độ, tùy vào vị trí servo của bạn)
  delay(2000);  // Giữ cửa mở trong 2 giây
  closeDoor();  // Đóng cửa sau 2 giây
}

// Hàm đóng cửa
void closeDoor() {
  servoIn.write(0);  // Đóng cửa (servo quay về vị trí ban đầu)
}

// Hàm gửi trạng thái cảm biến IR lên WebSocket server nếu có thay đổi
void sendSensorStatusIfChanged() {
  if (S1 != lastS1) {
    String message = "update_slot:1:" + String(S1 ? "available" : "occupied");
    webSocket.sendTXT(message);
    lastS1 = S1; // Cập nhật trạng thái cũ
  }

  if (S2 != lastS2) {
    String message = "update_slot:2:" + String(S2 ? "available" : "occupied");
    webSocket.sendTXT(message);
    lastS2 = S2; // Cập nhật trạng thái cũ
  }

  if (S3 != lastS3) {
    String message = "update_slot:3:" + String(S3 ? "available" : "occupied");
    webSocket.sendTXT(message);
    lastS3 = S3; // Cập nhật trạng thái cũ
  }
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
