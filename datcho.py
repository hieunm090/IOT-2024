import asyncio
import websockets
import json
import mysql.connector

# Kết nối đến MySQL
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",  
        password="",  
        database="parking_system"  
    )

# Kiểm tra tính sẵn sàng của vị trí
def check_slot_availability(slot):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM parking_slots WHERE slot_number = %s", (slot,))
    result = cursor.fetchone()
    conn.close()
    return result['status'] if result else None

# Cập nhật trạng thái vị trí
def update_slot_status(slot, status):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE parking_slots SET status = %s WHERE slot_number = %s", (status, slot))
    conn.commit()
    conn.close()

# Lưu thông tin đặt chỗ vào database
def save_booking(slot, start_time, end_time, cost):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookings (slot_number, start_time, end_time, cost) VALUES (%s, %s, %s, %s)",
        (slot, start_time, end_time, cost)
    )
    conn.commit()
    conn.close()

# Xử lý yêu cầu từ frontend
async def handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        response = {}

        if data['type'] == 'checkAvailability':
            slot_status = check_slot_availability(data['slot'])
            if slot_status:
                response = {"type": "parkingStatus", "slot": data['slot'], "status": slot_status}
            else:
                response = {"type": "error", "message": "Vị trí không tồn tại."}

        elif data['type'] == 'booking':
            slot = data['slot']
            start_time = data['startTime']
            end_time = data['endTime']
            hourly_rate = 5.0

            # Tính toán chi phí
            duration = (int(end_time) - int(start_time)) / 3600000
            cost = round(duration * hourly_rate, 2)

            slot_status = check_slot_availability(slot)
            if slot_status == "available":
                update_slot_status(slot, "occupied")
                save_booking(slot, start_time, end_time, cost)
                response = {
                    "type": "bookingConfirmation",
                    "slot": slot,
                    "startTime": start_time,
                    "endTime": end_time,
                    "cost": cost
                }
            else:
                response = {"type": "error", "message": f"Vị trí {slot} đã được đặt."}

        elif data['type'] == 'update_status':
            update_slot_status(data['slot'], data['status'])
            response = {
                "type": "parkingStatus",
                "slot": data['slot'],
                "status": data['status']
            }

        await websocket.send(json.dumps(response))

# Khởi chạy WebSocket server
start_server = websockets.serve(handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
