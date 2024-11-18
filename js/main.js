
(function ($) {
    "use strict";

    /*==================================================================
    [ Validate ]*/
    var input = $('.validate-input .input100');

    $('.validate-form').on('submit',function(){
        var check = true;

        for(var i=0; i<input.length; i++) {
            if(validate(input[i]) == false){
                showValidate(input[i]);
                check=false;
            }
        }

        return check;
    });


    $('.validate-form .input100').each(function(){
        $(this).focus(function(){
           hideValidate(this);
        });
    });

    function validate (input) {
        if($(input).attr('type') == 'email' || $(input).attr('name') == 'email') {
            if($(input).val().trim().match(/^([a-zA-Z0-9_\-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{1,5}|[0-9]{1,3})(\]?)$/) == null) {
                return false;
            }
        }
        else {
            if($(input).val().trim() == ''){
                return false;
            }
        }
    }

    function showValidate(input) {
        var thisAlert = $(input).parent();

        $(thisAlert).addClass('alert-validate');
    }

    function hideValidate(input) {
        var thisAlert = $(input).parent();

        $(thisAlert).removeClass('alert-validate');
    }
    
    

})(jQuery);

let ws;

// Khởi tạo WebSocket và thiết lập các sự kiện
function initWebSocket() {
    ws = new WebSocket('ws://localhost:8765'); // Cập nhật IP nếu không chạy cục bộ

    ws.onopen = function() {
        console.log('Đã kết nối đến WebSocket server');
        updateStatus("Đã kết nối đến server.");
    };

    ws.onmessage = function(event) {
        const message = JSON.parse(event.data);
        handleServerMessage(message);
    };

    ws.onclose = function() {
        console.log('Mất kết nối với WebSocket server');
        updateStatus("Mất kết nối với server. Đang thử kết nối lại...");
        reconnectWebSocket();
    };

    ws.onerror = function(error) {
        console.error('Lỗi WebSocket:', error);
    };
}

// Tự động kết nối lại nếu mất kết nối
function reconnectWebSocket() {
    setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
            console.log("Đang kết nối lại...");
            updateStatus("Đang kết nối lại...");
            initWebSocket();
        }
    }, 3000);
}

// Xử lý tin nhắn từ server
function handleServerMessage(message) {
    switch (message.type) {
        case 'parkingStatus':
            updateStatus(`Vị trí ${message.slot}: ${message.status}`);
            break;
        case 'bookingConfirmation':
            document.getElementById('statusMessage').innerText = `Xác nhận đặt chỗ cho Vị trí ${message.slot}. Tổng chi phí: $${message.cost}`;
            document.querySelector('.payment-section').style.display = 'block';
            break;
        case 'paymentStatus':
            document.getElementById('paymentStatusMessage').innerText = message.message;
            break;
        case 'rfidStatus':
            document.getElementById('rfidMessage').innerText = message.message;
            break;
        case 'error':
            document.getElementById('statusMessage').innerText = `Lỗi: ${message.message}`;
            break;
        default:
            console.warn("Loại tin nhắn không xác định:", message.type);
    }
}

// Gửi tin nhắn qua WebSocket
function sendWebSocketMessage(data) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        console.error('WebSocket chưa kết nối.');
    }
}

// Cập nhật trạng thái trên giao diện
function updateStatus(message) {
    document.getElementById('slotStatus').innerText = message;
}

// Các chức năng đặt chỗ, thanh toán, và quét thẻ
function submitBooking(event) {
    event.preventDefault();
    const slot = document.getElementById('parkingSpot').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;

    sendWebSocketMessage({ type: 'booking', slot, startTime, endTime });
}

function processPayment() {
    const paymentMethod = document.getElementById('paymentMethod').value;
    sendWebSocketMessage({ type: 'processPayment', method: paymentMethod });
}

function requestRFIDScan() {
    sendWebSocketMessage({ type: 'rfidScanRequest' });
}

function updateParkingStatus(slot, status) {
    sendWebSocketMessage({ type: 'update_status', slot, status });
}

// Khởi chạy WebSocket khi tải trang
window.onload = initWebSocket;
