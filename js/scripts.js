let ws;

// Khởi tạo WebSocket và thiết lập các sự kiện
function initWebSocket() {
    // Thay thế `192.168.x.x` bằng địa chỉ IP của ESP32
    ws = new WebSocket('ws://192.168.x.x:81'); 

    // Sự kiện khi WebSocket kết nối thành công
    ws.onopen = function () {
        console.log('Đã kết nối với WebSocket server trên ESP32');
        updateStatus("Đã kết nối với ESP32 WebSocket server.");
    };

    // Sự kiện khi nhận tin nhắn từ server
    ws.onmessage = function (event) {
        try {
            const message = JSON.parse(event.data);
            handleServerMessage(message);
        } catch (error) {
            console.error('Lỗi khi xử lý tin nhắn WebSocket:', event.data);
            updateStatus("Lỗi khi xử lý tin nhắn từ server.");
        }
    };

    // Sự kiện khi WebSocket bị ngắt kết nối
    ws.onclose = function () {
        console.log('Mất kết nối với WebSocket server ESP32');
        updateStatus("Mất kết nối với server. Đang thử kết nối lại...");
        reconnectWebSocket();
    };

    // Sự kiện khi có lỗi WebSocket
    ws.onerror = function (error) {
        console.error('Lỗi WebSocket:', error);
        updateStatus("Có lỗi xảy ra. Kiểm tra kết nối WebSocket.");
    };
}

// Tự động kết nối lại nếu mất kết nối
function reconnectWebSocket() {
    setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN && ws.readyState !== WebSocket.CONNECTING) {
            console.log("Đang thử kết nối lại...");
            updateStatus("Đang kết nối lại...");
            initWebSocket();
        }
    }, 3000); // Thử lại sau 3 giây
}

// Xử lý tin nhắn từ ESP32
function handleServerMessage(message) {
    switch (message.type) {
        case 'parkingStatus':
            updateStatus(`Vị trí ${message.slot}: ${message.status}`);
            break;
        case 'rfidStatus':
            document.getElementById('rfidMessage').innerText = message.message;
            break;
        case 'bookingConfirmation':
            updateStatus(`Xác nhận đặt chỗ: Vị trí ${message.slot} từ ${message.startTime} đến ${message.endTime}. Tổng chi phí: $${message.cost}`);
            document.querySelector('.payment-section').style.display = 'block'; // Hiển thị phần thanh toán
            break;
        case 'availabilityStatus':
            updateStatus(`Vị trí ${message.slot} hiện tại ${message.status}`);
            break;
        case 'paymentStatus':
            updateStatus(`Thanh toán thành công: ${message.message}`);
            break;
        case 'error':
            console.error("Lỗi từ server:", message.message);
            updateStatus(`Lỗi: ${message.message}`);
            break;
        default:
            console.warn("Loại tin nhắn không xác định:", message.type);
    }
}

// Cập nhật trạng thái hiển thị trên giao diện
function updateStatus(message) {
    document.getElementById('slotStatus').innerText = message;
}

// Gửi tin nhắn WebSocket nếu kết nối đang mở
function sendWebSocketMessage(data) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        console.error('WebSocket chưa kết nối. Không thể gửi tin nhắn:', data);
        updateStatus("Không thể gửi tin nhắn. WebSocket chưa kết nối.");
    }
}

// Kiểm tra trạng thái vị trí đỗ xe
function checkAvailability() {
    const slot = document.getElementById('parkingSpot').value;
    if (slot) {
        sendWebSocketMessage({ type: 'checkAvailability', slot: slot });
    } else {
        updateStatus("Vui lòng chọn vị trí để kiểm tra.");
    }
}

// Tính toán chi phí dự kiến
function calculateCost() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;

    if (startTime && endTime) {
        const durationHours = (new Date(endTime) - new Date(startTime)) / 3600000;
        const hourlyRate = 5.0; // Giá mỗi giờ
        const estimatedCost = (durationHours * hourlyRate).toFixed(2);

        document.getElementById('costEstimate').innerText = `Chi phí dự kiến: $${estimatedCost}`;
    } else {
        document.getElementById('costEstimate').innerText = "Vui lòng nhập thời gian.";
    }
}

// Gửi yêu cầu đặt chỗ
function submitBooking(event) {
    event.preventDefault();
    const slot = document.getElementById('parkingSpot').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;

    if (slot && startTime && endTime) {
        const bookingData = {
            type: 'booking',
            slot: slot,
            startTime: startTime,
            endTime: endTime
        };

        sendWebSocketMessage(bookingData);
        updateStatus("Đang gửi yêu cầu đặt chỗ...");
    } else {
        updateStatus("Vui lòng nhập đầy đủ thông tin đặt chỗ.");
    }
}

// Gửi yêu cầu quét thẻ RFID
function requestRFIDScan() {
    sendWebSocketMessage({ type: 'rfidScanRequest' });
    document.getElementById('rfidMessage').innerText = "Vui lòng quét thẻ RFID...";
}

// Cập nhật trạng thái vị trí đỗ xe
function updateParkingStatus(slot, status) {
    if (slot) {
        sendWebSocketMessage({
            type: 'update_status',
            slot: slot,
            status: status
        });
        updateStatus(`Đang cập nhật trạng thái cho Vị trí ${slot} thành ${status}...`);
    } else {
        updateStatus("Vui lòng chọn vị trí để cập nhật.");
    }
}

// Khởi tạo WebSocket khi tải trang
window.onload = initWebSocket;
