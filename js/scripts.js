<script>
    let ws;

    // Initialize WebSocket and set up events
    function initWebSocket() {
        ws = new WebSocket('ws://localhost:8765'); // Change to server IP if not testing locally

        ws.onopen = function() {
            console.log('Connected to WebSocket server');
            updateStatus("Connected to server.");
        };

        // Handle messages from the server
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            handleServerMessage(message);
        };

        ws.onclose = function() {
            console.log('Disconnected from WebSocket server');
            updateStatus("Disconnected from server. Attempting to reconnect...");
            reconnectWebSocket();
        };

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    }

    function reconnectWebSocket() {
        setTimeout(() => {
            if (ws.readyState !== WebSocket.OPEN && ws.readyState !== WebSocket.CONNECTING) {
                console.log("Reconnecting...");
                updateStatus("Reconnecting...");
                initWebSocket();
            }
        }, 3000);
    }

    // Unified function to handle server messages
    function handleServerMessage(message) {
        switch (message.type) {
            case 'parkingStatus':
                updateStatus(`Slot ${message.slot}: ${message.status}`);
                break;
            case 'rfidStatus':
                document.getElementById('rfidMessage').innerText = message.message;
                break;
            case 'bookingConfirmation':
                updateStatus(`Booking confirmed for Slot ${message.slot} from ${message.startTime} to ${message.endTime}. Total Cost: $${message.cost}`);
                break;
            case 'availabilityStatus':
                updateStatus(`Slot ${message.slot} is ${message.status}.`);
                break;
            case 'error':
                console.error("Error from server:", message.message);
                updateStatus(`Error: ${message.message}`);
                break;
            default:
                console.warn("Unknown message type:", message.type);
        }
    }

    // Helper function to update the status display
    function updateStatus(message) {
        document.getElementById('slotStatus').innerText = message;
    }

    // Send WebSocket message with connection check
    function sendWebSocketMessage(data) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket is not open. Message not sent:', data);
            updateStatus("Unable to send message. WebSocket not connected.");
        }
    }

    // Check slot availability
    function checkAvailability() {
        const slot = document.getElementById('slot').value;
        sendWebSocketMessage({ type: 'checkAvailability', slot: slot });
    }

    // Calculate estimated cost
    function calculateCost() {
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;

        if (startTime && endTime) {
            const durationHours = (new Date(endTime) - new Date(startTime)) / 3600000;
            const hourlyRate = 5.0; // Update with actual hourly rate if needed
            const estimatedCost = (durationHours * hourlyRate).toFixed(2);

            document.getElementById('costEstimate').innerText = `Estimated Cost: $${estimatedCost}`;
        }
    }

    // Submit booking request
    function submitBooking(event) {
        event.preventDefault();
        const slot = document.getElementById('slot').value;
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;

        const bookingData = {
            type: 'booking',
            slot: slot,
            startTime: startTime,
            endTime: endTime
        };

        sendWebSocketMessage(bookingData);
        updateStatus("Booking submitted. Waiting for confirmation...");
    }

    // Request RFID scan
    function requestRFIDScan() {
        sendWebSocketMessage({ type: 'rfidScanRequest' });
        document.getElementById('rfidMessage').innerText = "Please scan your RFID card...";
    }

    // Update parking slot status
    function updateParkingStatus(slot, status) {
        sendWebSocketMessage({
            type: 'update_status',
            slot: slot,
            status: status
        });
        updateStatus(`Updating status for Slot ${slot} to ${status}...`);
    }

    // Initialize WebSocket on page load
    window.onload = initWebSocket;
</script>
