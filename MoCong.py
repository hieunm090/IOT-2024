import asyncio
import mysql.connector
import websockets

# Ham ket noi co so du lieu MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",         # Dia chi host MySQL
        user="root",              # Ten nguoi dung MySQL
        password="",              # Mat khau MySQL
        database="parking_db"     # Ten co so du lieu
    )

# Xu ly tin nhan nhan tu client WebSocket
async def message_received(websocket, message):
    # In ra thông điệp mà client gửi tới server
    print(f"Message received from client: {message}")

    # Xu ly neu nhan thong diep co chua ma RFID
    if "rfid_code:" in message:
        rfid_code = message.split(":")[1].strip()  # Lay phan sau dau ":"
        
        # Ket noi voi co so du lieu va truy van thong tin nguoi dung
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                
                # Truy van lay user_id tu bang rfid_cards
                cursor.execute("SELECT user_id FROM rfid_cards WHERE rfid_code = %s", (rfid_code,))
                user = cursor.fetchone()  # Lay ket qua tra ve
                
                if user:
                    user_id = user[0]
                    print(f"User ID: {user_id}")
                    
                    # Kiem tra trang thai thanh toan va hoa don
                    cursor.execute(""" 
                        SELECT payment_status, invoice_status 
                        FROM invoices WHERE user_id = %s ORDER BY issue_date DESC LIMIT 1
                    """, (user_id,))
                    invoice = cursor.fetchone()  # Lay ket qua tra ve
                    
                    if invoice:
                        payment_status, invoice_status = invoice
                        
                        # Kiem tra trang thai hoa don va thanh toan
                        if invoice_status == '0':  # Hoa don chua su dung
                            if payment_status == 'paid':
                                # Cap nhat trang thai hoa don thanh '1' (dang su dung)
                                cursor.execute(""" 
                                    UPDATE invoices SET invoice_status = '1' 
                                    WHERE user_id = %s AND invoice_status = '0'""", (user_id,))
                                connection.commit()
                                await websocket.send("Access granted to parking lot")
                            else:
                                await websocket.send("Payment pending. Access denied")
                        elif invoice_status == '1':  # Dang su dung
                            await websocket.send("Already in use. Access denied")
                        else:  # Hoa don da het han
                            await websocket.send("Invoice expired. Access denied")
                    else:
                        # Neu khong tim thay hoa don
                        await websocket.send("No invoice found for this user.")
                else:
                    # Neu khong tim thay nguoi dung
                    await websocket.send("RFID code not found.")
            except mysql.connector.Error as e:
                await websocket.send(f"Database error: {str(e)}")
            finally:
                # Dam bao dong cursor va connection
                cursor.close()
                connection.close()

    # Xu ly khi nhan tin nhan de cap nhat trang thai khi nguoi dung roi khoi bai do xe
    elif "exit_parking:" in message:
        rfid_code = message.split(":")[1].strip()  # Lay phan sau dau ":"

        if not rfid_code:
            await websocket.send('RFID code is required to exit parking.')
            return

        # Cap nhat trang thai hoa don va vi tri do xe
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            try:
                cursor.execute("SELECT user_id FROM rfid_cards WHERE rfid_code = %s", (rfid_code,))
                user = cursor.fetchone()

                if not user:
                    await websocket.send({"error": "RFID not found"})
                    return

                user_id = user[0]

                # Cap nhat trang thai hoa don thanh '2' (het han)
                cursor.execute(""" 
                    UPDATE invoices SET invoice_status = '2' 
                    WHERE user_id = %s AND invoice_status = '1'""", (user_id,))
                connection.commit()

                # Cap nhat trang thai vi tri do xe thanh 'available' khi nguoi dung roi di
                cursor.execute(""" 
                    UPDATE parking_slots 
                    SET status = 'available' 
                    WHERE slot_id IN (
                        SELECT parking_slot_id 
                        FROM invoices 
                        WHERE user_id = %s AND invoice_status = '2'
                    )
                """, (user_id,))
                
                connection.commit()
                await websocket.send({"message": "Exit registered. Slot is now available."})

            except Exception as e:
                await websocket.send({"error": str(e)})
            finally:
                cursor.close()
                connection.close()

    # Xu ly thong tin ve trang thai cac slot do xe tu ESP32
    elif "update_slot:" in message:
        # Lay thong tin tu thong diep
        parts = message.split(":")
        if len(parts) == 3:
            slot_id = int(parts[1])  # ID cua slot
            status = parts[2].strip()  # Trang thai slot ('occupied' hoac 'available')

            # Cap nhat trang thai slot trong co so du lieu
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(""" 
                        UPDATE parking_slots 
                        SET status = %s 
                        WHERE slot_id = %s
                    """, (status, slot_id))
                    connection.commit()
                    print(f"Slot {slot_id} updated to {status}")
                    await websocket.send(f"Slot {slot_id} updated to {status}")
                except mysql.connector.Error as e:
                    await websocket.send(f"Database error: {str(e)}")
                finally:
                    cursor.close()
                    connection.close()

    else:
        await websocket.send("Invalid message format.")

# WebSocket server - Ham nay se chay server WebSocket va xu ly ket noi
async def websocket_server(websocket, path):
    print(f"Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            # Xu ly khi nhan tin nhan tu client
            await message_received(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {websocket.remote_address} disconnected.")

# Khoi chay server WebSocket
async def main():
    server = await websockets.serve(websocket_server, '0.0.0.0', 5000)
    print("WebSocket server running on port 5000...")
    await server.wait_closed()

# Chay server WebSocket
asyncio.run(main())
