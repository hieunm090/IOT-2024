-- 1. Tạo cơ sở dữ liệu nếu chưa có
CREATE DATABASE IF NOT EXISTS parking_db;
USE parking_db;

-- 2. Tạo bảng "users" nếu chưa có
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,  -- Username thay vì email
    password VARCHAR(255) NOT NULL,          -- Mã hóa password (hoặc lưu trữ plaintext nếu bạn không cần mã hóa)
    balance DECIMAL(10, 2) DEFAULT 0.00,     -- Số dư tài khoản, không cần cho admin
    role ENUM('customer', 'admin') DEFAULT 'customer',  -- Phân quyền
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Thời gian tạo tài khoản
);

-- 3. Tạo bảng "rfid_cards" nếu chưa có
CREATE TABLE IF NOT EXISTS rfid_cards (
    rfid_id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_code VARCHAR(50) NOT NULL UNIQUE,   -- Mã thẻ RFID
    user_id INT,                             -- ID người dùng (khách hàng)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Thời gian tạo thẻ RFID
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Tạo bảng "parking_slots" nếu chưa có (Bỏ AUTO_INCREMENT)
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id INT PRIMARY KEY,   -- ID chỗ đỗ xe, không tự động tăng
    status ENUM('available', 'occupied') DEFAULT 'available'  -- Trạng thái của chỗ đỗ xe
);

-- 5. Tạo bảng "payments" nếu chưa có
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('credit_card', 'paypal', 'bank_transfer') DEFAULT 'credit_card',
    payment_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. Tạo bảng "invoices" để lưu thông tin hóa đơn (lịch sử thanh toán)
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,                            -- ID người dùng
    parking_slot_id INT,                    -- ID chỗ đỗ xe đã đặt
    total_amount DECIMAL(10, 2) NOT NULL,    -- Tổng số tiền cần thanh toán
    payment_status ENUM('pending', 'paid') DEFAULT 'pending', -- Trạng thái thanh toán (chờ thanh toán, đã thanh toán)
    invoice_status ENUM('0', '1', '2') DEFAULT '0',  -- Trạng thái hóa đơn (0: chưa sử dụng, 1: đang sử dụng, 2: hết hạn)
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- Ngày lập hóa đơn
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parking_slot_id) REFERENCES parking_slots(slot_id) ON DELETE CASCADE
);

-- 7. Dữ Liệu Mẫu (Ví dụ thêm người dùng, thẻ RFID, thanh toán, hóa đơn)

-- Thêm người dùng mẫu (Khách hàng)
INSERT INTO users (username, password, balance, role)
VALUES 
    ('khanh', 'khanh', 100.00, 'customer'),  -- Người dùng 'khanh'
    ('khai', 'khai', 100.00, 'customer'),    -- Người dùng 'khai'
    ('hieu', 'hieu', 100.00, 'customer'),    -- Người dùng 'hieu'
    ('tuan', 'tuan', 100.00, 'customer');    -- Người dùng 'tuan'

-- Thêm người dùng mẫu (Quản lý) không cần balance
INSERT INTO users (username, password, role)
VALUES 
    ('admin', '123456', 'admin');  -- Quản lý 'admin'

-- Thêm thẻ RFID cho người dùng
INSERT INTO rfid_cards (rfid_code, user_id)
VALUES 
    ('4319C636', 1),  -- Thẻ của 'khanh'
    ('B3D9C336', 2),    -- Thẻ của 'khai'
    ('B3D2E336', 3),    -- Thẻ của 'hieu'
    ('BF4C321F', 4);    -- Thẻ của 'tuan'

-- Thêm vị trí đỗ xe (Trạng thái có thể là 'available', 'occupied')
-- Chú ý: Bây giờ bạn sẽ phải tự quản lý giá trị cho `slot_id` khi thêm dữ liệu vào bảng này.
INSERT INTO parking_slots (slot_id, status)
VALUES 
    (1, 'available'), 
    (2, 'occupied');

-- Thêm giao dịch thanh toán
INSERT INTO payments (user_id, amount, payment_method)
VALUES 
    (1, 20.00, 'credit_card');  -- Giao dịch của 'khanh'

-- Thêm một hóa đơn mẫu cho người dùng
INSERT INTO invoices (user_id, parking_slot_id, total_amount, payment_status, invoice_status)
VALUES 
    (1, 1, 50.00, 'pending', '0');  -- Hóa đơn cho 'khanh' với vị trí đỗ xe đầu tiên
