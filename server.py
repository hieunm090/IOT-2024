import asyncio
import websockets
import json
from datetime import datetime
import mysql.connector

# Cấu hình kết nối MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'parking_db',
}

# Danh sách kết nối WebSocket
clients = set()

# Hàm kết nối cơ sở dữ liệu MySQL
def connect_db():
    return mysql.connector.connect(**db_config)

# Phát sóng tới tất cả các khách hàng
async def broadcast(data):
    if clients:
        message = json.dumps(data)
        tasks = [asyncio.create_task(client.send(message)) for client in clients]
        await asyncio.gather(*tasks)  # Sử dụng gather để đảm bảo xử lý tất cả các coroutine

# Xử lý đặt chỗ đỗ xe
async def handle_booking(data, websocket):
    user_id = data.get('userId', 1)  # Giả định user_id = 1 nếu không có dữ liệu từ client
    slot = data['slot']
    start_time = datetime.fromisoformat(data['startTime'])
    end_time = datetime.fromisoformat(data['endTime'])

    duration_hours = (end_time - start_time).total_seconds() / 3600
    total_cost = round(duration_hours * 5.0, 2)  # Giá mỗi giờ là 5.0

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra trạng thái chỗ đỗ
        cursor.execute("SELECT status FROM parking_slots WHERE slot_id = %s", (slot,))
        result = cursor.fetchone()
        if not result or result['status'] != 'available':
            await websocket.send(json.dumps({"type": "error", "message": f"Slot {slot} đã được đặt."}))
            return

        # Cập nhật trạng thái slot và tạo hóa đơn
        cursor.execute("UPDATE parking_slots SET status = 'occupied' WHERE slot_id = %s", (slot,))
        cursor.execute("""
            INSERT INTO invoices (user_id, parking_slot_id, total_amount, payment_status, invoice_status)
            VALUES (%s, %s, %s, 'pending', '0')
        """, (user_id, slot, total_cost))
        db.commit()

        response = {
            "type": "bookingConfirmation",
            "slot": slot,
            "startTime": data['startTime'],
            "endTime": data['endTime'],
            "cost": total_cost,
        }
        await websocket.send(json.dumps(response))
        await broadcast({"type": "parkingStatus", "slot": slot, "status": "occupied"})
        print(f"Đặt chỗ thành công: Slot {slot}, User ID: {user_id}")
    except Exception as e:
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))
    finally:
        cursor.close()
        db.close()

# Xử lý thanh toán
async def handle_payment(data, websocket):
    user_id = data.get('userId', 1)  # Giả định user_id = 1 nếu không có từ client
    payment_method = data.get('method', 'credit_card')

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Lấy hóa đơn chờ thanh toán
        cursor.execute("""
            SELECT invoice_id, total_amount 
            FROM invoices 
            WHERE user_id = %s AND payment_status = 'pending' 
            ORDER BY issue_date DESC LIMIT 1
        """, (user_id,))
        invoice = cursor.fetchone()

        if not invoice:
            await websocket.send(json.dumps({"type": "error", "message": "Không có hóa đơn cần thanh toán."}))
            return

        invoice_id = invoice['invoice_id']
        amount = invoice['total_amount']

        # Ghi nhận thanh toán và cập nhật hóa đơn
        cursor.execute("""
            INSERT INTO payments (user_id, amount, payment_method) 
            VALUES (%s, %s, %s)
        """, (user_id, amount, payment_method))
        cursor.execute("""
            UPDATE invoices SET payment_status = 'paid', invoice_status = '1' WHERE invoice_id = %s
        """, (invoice_id,))
        db.commit()

        response = {
            "type": "paymentStatus",
            "message": f"Thanh toán thành công qua {payment_method}.",
            "status": "paid",
            "amount": amount
        }
        await websocket.send(json.dumps(response))
        print(f"User {user_id} đã thanh toán thành công.")
    except Exception as e:
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))
    finally:
        cursor.close()
        db.close()

# Xử lý quét RFID
async def handle_rfid_scan(data, websocket):
    rfid_code = data.get('rfidCode')
    db = connect_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra người dùng với RFID
        cursor.execute("""
            SELECT username 
            FROM users 
            WHERE id = (SELECT user_id FROM rfid_cards WHERE rfid_code = %s)
        """, (rfid_code,))
        user = cursor.fetchone()

        if user:
            response = {
                "type": "rfidStatus",
                "message": f"Chào mừng, {user['username']}! Quyền truy cập đã được cấp.",
                "status": "Cửa mở"
            }
        else:
            response = {
                "type": "rfidStatus",
                "message": "Thẻ RFID không hợp lệ.",
                "status": "Cửa đóng"
            }
        await websocket.send(json.dumps(response))
        print(f"RFID Scan: {rfid_code} - {response['message']}")
    except Exception as e:
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))
    finally:
        cursor.close()
        db.close()

# Xử lý trạng thái slot
async def handle_update_status(data):
    slot = data['slot']
    status = data['status']

    db = connect_db()
    cursor = db.cursor()

    try:
        cursor.execute("UPDATE parking_slots SET status = %s WHERE slot_id = %s", (status, slot))
        db.commit()
        await broadcast({"type": "parkingStatus", "slot": slot, "status": status})
        print(f"Cập nhật trạng thái Slot {slot} thành {status}.")
    except Exception as e:
        print(f"Lỗi cập nhật trạng thái Slot {slot}: {e}")
    finally:
        cursor.close()
        db.close()

# Xử lý kết nối WebSocket
async def handle_connection(websocket, path):
    clients.add(websocket)
    print(f"Kết nối mới từ {websocket.remote_address}")

    try:
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
        print(f"Kết nối đã đóng: {websocket.remote_address}")
    finally:
        clients.remove(websocket)

# Khởi chạy server WebSocket
async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        print("Máy chủ WebSocket đang chạy trên ws://0.0.0.0:8765")
        await asyncio.Future()  # Chạy mãi mãi

if __name__ == "__main__":
    asyncio.run(main())
