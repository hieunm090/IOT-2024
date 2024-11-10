-- 1. Tạo cơ sở dữ liệu nếu chưa có
CREATE DATABASE IF NOT EXISTS parking_db;
USE parking_db;

-- 2. Tạo bảng "users" để quản lý thông tin người dùng
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,  -- Tên người dùng duy nhất
    password VARCHAR(255) NOT NULL,          -- Mật khẩu (nên mã hóa)
    balance DECIMAL(10, 2) DEFAULT 0.00,     -- Số dư tài khoản
    role ENUM('customer', 'admin') DEFAULT 'customer',  -- Phân quyền
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Thời gian tạo tài khoản
);

-- 3. Tạo bảng "rfid_cards" để lưu thông tin thẻ RFID
CREATE TABLE IF NOT EXISTS rfid_cards (
    rfid_id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_code VARCHAR(50) NOT NULL UNIQUE,   -- Mã thẻ RFID duy nhất
    user_id INT,                             -- ID người dùng liên kết
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Thời gian cấp thẻ
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Tạo bảng "parking_slots" để quản lý vị trí đỗ xe
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id INT PRIMARY KEY,                 -- ID chỗ đỗ xe
    status ENUM('available', 'occupied') DEFAULT 'available'  -- Trạng thái chỗ đỗ
);

-- 5. Tạo bảng "payments" để lưu thông tin giao dịch thanh toán
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('credit_card', 'paypal', 'bank_transfer') DEFAULT 'credit_card',
    payment_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. Tạo bảng "invoices" để lưu thông tin hóa đơn
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,                             -- ID người dùng
    parking_slot_id INT,                     -- ID chỗ đỗ xe đã đặt
    total_amount DECIMAL(10, 2) NOT NULL,    -- Tổng số tiền thanh toán
    payment_status ENUM('pending', 'paid') DEFAULT 'pending', -- Trạng thái thanh toán
    invoice_status ENUM('0', '1', '2') DEFAULT '0',  -- Trạng thái hóa đơn (0: chưa sử dụng, 1: đang sử dụng, 2: hết hạn)
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- Ngày lập hóa đơn
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parking_slot_id) REFERENCES parking_slots(slot_id) ON DELETE CASCADE
);

-- 7. Thêm dữ liệu mẫu vào bảng "users"
INSERT INTO users (username, password, balance, role)
VALUES 
    ('khanh', 'khanh', 100.00, 'customer'),
    ('khai', 'khai', 100.00, 'customer'),
    ('hieu', 'hieu', 100.00, 'customer'),
    ('tuan', 'tuan', 100.00, 'customer'),
    ('admin', '123456', 0.00, 'admin');

-- 8. Thêm dữ liệu mẫu vào bảng "rfid_cards"
INSERT INTO rfid_cards (rfid_code, user_id)
VALUES 
    ('4319C636', 1),  -- Thẻ của người dùng 'khanh'
    ('B3D9C336', 2),  -- Thẻ của người dùng 'khai'
    ('B3D2E336', 3),  -- Thẻ của người dùng 'hieu'
    ('BF4C321F', 4);  -- Thẻ của người dùng 'tuan'

-- 9. Thêm dữ liệu mẫu vào bảng "parking_slots"
INSERT INTO parking_slots (slot_id, status)
VALUES 
    (1, 'available'),
    (2, 'occupied'),
    (3, 'available'),
    (4, 'available');

-- 10. Thêm dữ liệu mẫu vào bảng "payments"
INSERT INTO payments (user_id, amount, payment_method)
VALUES 
    (1, 20.00, 'credit_card'), 
    (2, 30.00, 'paypal');

-- 11. Thêm dữ liệu mẫu vào bảng "invoices"
INSERT INTO invoices (user_id, parking_slot_id, total_amount, payment_status, invoice_status)
VALUES 
    (1, 1, 50.00, 'paid', '1'), 
    (2, 2, 30.00, 'pending', '0');
