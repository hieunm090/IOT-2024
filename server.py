import asyncio
import websockets
import json
from datetime import datetime

# Địa chỉ và cổng máy chủ
SERVER_HOST = '0.0.0.0'  # Lắng nghe trên tất cả các IP của máy chủ
SERVER_PORT = 8765

# Danh sách các khách hàng kết nối để truyền phát dữ liệu
clients = set()

# Trạng thái chỗ đỗ xe và hóa đơn
invoices = []
parking_spots = {"1": "available", "2": "available", "3": "available", "4": "available"}

# Danh sách ID RFID được cấp quyền
authorized_ids = {
    "123456789": "Alice",
    "987654321": "Bob",
}

# Thông tin giá cả
pricing_per_hour = 5.0  # Giá cho mỗi giờ

# Hàm phát sóng dữ liệu tới tất cả các khách hàng
async def broadcast(data):
    if clients:
        message = json.dumps(data)
        await asyncio.wait([asyncio.create_task(client.send(message)) for client in clients])

# Xử lý kết nối WebSocket
async def handle_connection(websocket, path):
    print("Kết nối mới đã được thiết lập")
    clients.add(websocket)

    try:
        # Gửi dữ liệu ban đầu về trạng thái chỗ đỗ xe và danh sách hóa đơn
        await websocket.send(json.dumps({"type": "parkingStatus", "spots": parking_spots}))
        await websocket.send(json.dumps({"type": "invoiceList", "invoices": invoices}))

        async for message in websocket:
            print(f"Đã nhận tin nhắn: {message}")
            data = json.loads(message)

            # Xử lý yêu cầu đặt chỗ
            if data['type'] == 'booking':
                slot = data['slot']
                start_time = datetime.fromisoformat(data['startTime'])
                end_time = datetime.fromisoformat(data['endTime'])
                
                # Kiểm tra tình trạng chỗ đỗ
                if parking_spots[slot] == "available":
                    # Tính chi phí tổng cộng
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    total_cost = round(duration_hours * pricing_per_hour, 2)
                    
                    # Giả lập trạng thái thanh toán
                    payment_status = "successful"

                    if payment_status == "successful":
                        parking_spots[slot] = "occupied"  # Cập nhật trạng thái chỗ đỗ thành "occupied"
                        
                        # Tạo hóa đơn và lưu trữ
                        invoice = {
                            "slot": slot,
                            "startTime": data['startTime'],
                            "endTime": data['endTime'],
                            "cost": total_cost,
                            "status": "paid"
                        }
                        invoices.append(invoice)

                        # Gửi xác nhận đặt chỗ tới người dùng
                        response = {
                            "type": "bookingConfirmation",
                            "slot": slot,
                            "startTime": data['startTime'],
                            "endTime": data['endTime'],
                            "cost": total_cost,
                            "status": "confirmed",
                            "rfidAccessGranted": True  # Cấp quyền truy cập RFID
                        }
                        await websocket.send(json.dumps(response))
                        
                        # Phát bản cập nhật trạng thái chỗ đỗ tới tất cả các khách hàng
                        await broadcast({"type": "parkingStatus", "slot": slot, "status": "occupied"})
                        print(f"Đã xác nhận đặt chỗ và xử lý thanh toán cho Slot {slot}")
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Thanh toán thất bại. Vui lòng thử lại."
                        }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"Slot {slot} đã được chiếm dụng."
                    }))

            # Xử lý yêu cầu quét RFID
            elif data['type'] == 'rfidScanRequest':
                rfid_id = data.get('rfidCode', '123456789')  # Nhận RFID từ yêu cầu hoặc giả lập nếu không có
                user = authorized_ids.get(rfid_id)
                
                if user:
                    response = {
                        "type": "rfidStatus",
                        "message": f"Chào mừng, {user}! Quyền truy cập đã được cấp.",
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

            # Xử lý yêu cầu cập nhật trạng thái chỗ đỗ
            elif data['type'] == 'update_status':
                slot = data['slot']
                status = data['status']
                parking_spots[slot] = status
                await broadcast({"type": "parkingStatus", "slot": slot, "status": status})
                print(f"Đã cập nhật trạng thái chỗ đỗ {slot} thành {status}")

    except websockets.ConnectionClosed as e:
        print(f"Kết nối đã bị đóng: {e}")
    finally:
        clients.remove(websocket)
        print("Đã xóa kết nối")

# Điểm vào chính của máy chủ WebSocket
async def main():
    async with websockets.serve(handle_connection, SERVER_HOST, SERVER_PORT):
        print(f"Máy chủ WebSocket đang chạy trên ws://{SERVER_HOST}:{SERVER_PORT}")
        await asyncio.Future()  # Chạy mãi mãi

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Máy chủ gặp lỗi: {e}")
