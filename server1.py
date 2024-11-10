import asyncio
import websockets
import json
from datetime import datetime
import mysql.connector

# Địa chỉ và cổng máy chủ
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765

# Cấu hình kết nối đến cơ sở dữ liệu MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',         # User mặc định của XAMPP
    'password': '',          # Mật khẩu mặc định của XAMPP là rỗng
    'database': 'parking_db'  # Tên cơ sở dữ liệu
}

# Danh sách khách hàng kết nối
clients = set()

# Hàm kết nối cơ sở dữ liệu
def connect_db():
    return mysql.connector.connect(**db_config)

# Phát sóng dữ liệu tới tất cả các khách hàng
async def broadcast(data):
    if clients:
        message = json.dumps(data)
        await asyncio.wait([asyncio.create_task(client.send(message)) for client in clients])

# Lấy trạng thái chỗ đỗ từ cơ sở dữ liệu
def fetch_parking_spots():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT slot_id, status FROM parking_slots")
    spots = {str(row['slot_id']): row['status'] for row in cursor.fetchall()}
    db.close()
    return spots

# Xử lý đặt chỗ
async def handle_booking(data, websocket):
    slot = data['slot']
    start_time = datetime.fromisoformat(data['startTime'])
    end_time = datetime.fromisoformat(data['endTime'])

    parking_spots = fetch_parking_spots()
    if parking_spots.get(slot) != "available":
        await websocket.send(json.dumps({"type": "error", "message": f"Slot {slot} đã được chiếm dụng."}))
        return

    duration_hours = (end_time - start_time).total_seconds() / 3600
    total_cost = round(duration_hours * 5.0, 2)  # Giá mỗi giờ là 5.0

    # Giả lập thanh toán thành công
    payment_status = "successful"
    if payment_status != "successful":
        await websocket.send(json.dumps({"type": "error", "message": "Thanh toán thất bại."}))
        return

    # Thực hiện cập nhật cơ sở dữ liệu và phát sóng trạng thái
    db = connect_db()
    cursor = db.cursor()

    try:
        # Cập nhật trạng thái vị trí đỗ và thêm hóa đơn
        cursor.execute("UPDATE parking_slots SET status = 'occupied' WHERE slot_id = %s", (slot,))
        cursor.execute(
            "INSERT INTO invoices (user_id, parking_slot_id, total_amount, payment_status) VALUES (%s, %s, %s, 'paid')",
            (1, slot, total_cost)  # Giả định user_id là 1
        )
        db.commit()
    finally:
        db.close()

    response = {
        "type": "bookingConfirmation",
        "slot": slot,
        "startTime": data['startTime'],
        "endTime": data['endTime'],
        "cost": total_cost,
        "status": "confirmed",
        "rfidAccessGranted": True
    }
    await websocket.send(json.dumps(response))
    await broadcast({"type": "parkingStatus", "slot": slot, "status": "occupied"})
    print(f"Đã xác nhận đặt chỗ và xử lý thanh toán cho Slot {slot}")

# Xử lý quét RFID
async def handle_rfid_scan(data, websocket):
    rfid_id = data.get('rfidCode', '123456789')  # Mã RFID mặc định để thử nghiệm
    db = connect_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT username FROM users WHERE id = (SELECT user_id FROM rfid_cards WHERE rfid_code = %s)", (rfid_id,))
        result = cursor.fetchone()
    finally:
        db.close()

    if result:
        response = {
            "type": "rfidStatus",
            "message": f"Chào mừng, {result[0]}! Quyền truy cập đã được cấp.",
            "status": "Cửa mở"
        }
    else:
        response = {
            "type": "rfidStatus",
            "message": "Từ chối truy cập. Thẻ RFID không hợp lệ.",
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

    try:
        cursor.execute("UPDATE parking_slots SET status = %s WHERE slot_id = %s", (status, slot))
        db.commit()
    finally:
        db.close()

    await broadcast({"type": "parkingStatus", "slot": slot, "status": status})
    print(f"Đã cập nhật trạng thái chỗ đỗ {slot} thành {status}")

# Xử lý kết nối WebSocket
async def handle_connection(websocket, path):
    print("Kết nối mới đã được thiết lập")
    clients.add(websocket)

    try:
        # Gửi trạng thái chỗ đỗ từ cơ sở dữ liệu ban đầu
        parking_spots = fetch_parking_spots()
        await websocket.send(json.dumps({"type": "parkingStatus", "spots": parking_spots}))

        async for message in websocket:
            print(f"Đã nhận tin nhắn: {message}")
            data = json.loads(message)

            if data['type'] == 'booking':
                await handle_booking(data, websocket)
            elif data['type'] == 'rfidScanRequest':
                await handle_rfid_scan(data, websocket)
            elif data['type'] == 'update_status':
                await handle_update_status(data)

    except websockets.ConnectionClosed as e:
        print(f"Kết nối đã bị đóng: {e}")
    finally:
        clients.remove(websocket)
        print("Đã xóa kết nối")

# Điểm vào chính của máy chủ WebSocket
async def main():
    async with websockets.serve(handle_connection, SERVER_HOST, SERVER_PORT):
        print(f"Máy chủ WebSocket đang chạy trên ws://{SERVER_HOST}:{SERVER_PORT}")
        await asyncio.Future()  # Giữ máy chủ luôn hoạt động

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Máy chủ gặp lỗi: {e}")
