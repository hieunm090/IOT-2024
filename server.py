import asyncio
import websockets
import json
from datetime import datetime
import mysql.connector

# Cấu hình kết nối MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',         # Thay đổi nếu cần
    'password': '',         # Thay đổi nếu có mật khẩu
    'database': 'parking_db',
}

# Danh sách kết nối WebSocket
clients = set()

# Hàm kết nối với cơ sở dữ liệu MySQL
def connect_db():
    return mysql.connector.connect(**db_config)

# Phát sóng tới tất cả các khách hàng
async def broadcast(data):
    if clients:
        message = json.dumps(data)
        await asyncio.wait([asyncio.create_task(client.send(message)) for client in clients])

# Xử lý yêu cầu đặt chỗ
async def handle_booking(data, websocket):
    slot = data['slot']
    start_time = datetime.fromisoformat(data['startTime'])
    end_time = datetime.fromisoformat(data['endTime'])
    
    duration_hours = (end_time - start_time).total_seconds() / 3600
    total_cost = round(duration_hours * 5.0, 2)  # Giả định giá mỗi giờ là 5.0

    db = connect_db()
    cursor = db.cursor()

    # Kiểm tra chỗ đỗ còn trống không
    cursor.execute("SELECT status FROM parking_slots WHERE slot_id = %s", (slot,))
    result = cursor.fetchone()
    if result[0] != 'available':
        await websocket.send(json.dumps({"type": "error", "message": f"Slot {slot} đã được đặt."}))
        db.close()
        return

    # Cập nhật trạng thái chỗ đỗ và tạo hóa đơn
    try:
        cursor.execute("UPDATE parking_slots SET status = 'occupied' WHERE slot_id = %s", (slot,))
        cursor.execute(
            "INSERT INTO invoices (user_id, parking_slot_id, total_amount, payment_status) VALUES (%s, %s, %s, 'pending')",
            (1, slot, total_cost)  # Giả định user_id là 1 cho thử nghiệm
        )
        db.commit()
    finally:
        db.close()

    response = {
        "type": "bookingConfirmation",
        "slot": slot,
        "startTime": data['startTime'],
        "endTime": data['endTime'],
        "cost": total_cost
    }
    await websocket.send(json.dumps(response))
    await broadcast({"type": "parkingStatus", "slot": slot, "status": "occupied"})
    print(f"Đã xác nhận đặt chỗ cho Slot {slot}")

# Xử lý yêu cầu thanh toán
async def handle_payment(data, websocket):
    payment_method = data.get('method')
    payment_details = data.get('details')
    total_cost = 50.00  # Số tiền mẫu, lấy từ hóa đơn nếu có

    # Xử lý giao dịch
    db = connect_db()
    cursor = db.cursor()
    
    # Giả lập thanh toán thành công và cập nhật trạng thái hóa đơn
    cursor.execute("UPDATE invoices SET payment_status = 'paid' WHERE user_id = %s AND payment_status = 'pending'", (1,))
    db.commit()
    db.close()

    response = {
        "type": "paymentStatus",
        "message": f"Thanh toán thành công với {payment_method}",
        "status": "paid"
    }
    await websocket.send(json.dumps(response))
    print(f"Thanh toán thành công qua {payment_method}")

# Xử lý quét RFID
async def handle_rfid_scan(data, websocket):
    rfid_code = data.get('rfidCode')
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT username FROM users WHERE id = (SELECT user_id FROM rfid_cards WHERE rfid_code = %s)", (rfid_code,))
    result = cursor.fetchone()

    if result:
        response = {
            "type": "rfidStatus",
            "message": f"Chào mừng, {result[0]}! Quyền truy cập đã được cấp.",
            "status": "Cửa mở"
        }
    else:
        response = {
            "type": "rfidStatus",
            "message": "Thẻ RFID không hợp lệ.",
            "status": "Cửa đóng"
        }

    await websocket.send(json.dumps(response))
    print("Đã xử lý quét RFID")

# Xử lý cập nhật trạng thái chỗ đỗ
async def handle_update_status(data):
    slot = data['slot']
    status = data['status']
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("UPDATE parking_slots SET status = %s WHERE slot_id = %s", (status, slot))
    db.commit()
    db.close()

    await broadcast({"type": "parkingStatus", "slot": slot, "status": status})
    print(f"Đã cập nhật trạng thái của Slot {slot} thành {status}")

# Xử lý kết nối WebSocket
async def handle_connection(websocket, path):
    clients.add(websocket)
    print("Kết nối mới đã được thiết lập")

    try:
        # Gửi trạng thái ban đầu
        await websocket.send(json.dumps({"type": "status", "message": "Welcome to Parking Succorer!"}))
        
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'booking':
                await handle_booking(data, websocket)
            elif data['type'] == 'processPayment':
                await handle_payment(data, websocket)
            elif data['type'] == 'rfidScanRequest':
                await handle_rfid_scan(data, websocket)
            elif data['type'] == 'update_status':
                await handle_update_status(data)

    except websockets.ConnectionClosed:
        print("Kết nối đã bị đóng")
    finally:
        clients.remove(websocket)
        print("Đã xóa kết nối")

# Điểm vào chính của máy chủ WebSocket
async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        print("Máy chủ WebSocket đang chạy trên ws://0.0.0.0:8765")
        await asyncio.Future()  # Chạy mãi mãi

if __name__ == "__main__":
    asyncio.run(main())
