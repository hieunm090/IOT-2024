CREATE DATABASE parking_system;

USE parking_system;

-- Bảng quản lý người dùng
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng quản lý chỗ đỗ xe
CREATE TABLE parking_slots (
    slot_number INT AUTO_INCREMENT PRIMARY KEY,
    status ENUM('available', 'occupied') DEFAULT 'available',
    hourly_rate DECIMAL(10, 2) DEFAULT 5.00
);

-- Bảng hóa đơn
CREATE TABLE invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    user_id INT NOT NULL,
    slot_number INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('Paid', 'Unpaid') DEFAULT 'Unpaid',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (slot_number) REFERENCES parking_slots(slot_number)
);

-- Bảng thanh toán
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    invoice_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('credit_card', 'paypal', 'debit_card') NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

INSERT INTO parking_slots (slot_number, status) VALUES
(1, 'available'),
(2, 'available'),
(3, 'available'),
(4, 'available');
