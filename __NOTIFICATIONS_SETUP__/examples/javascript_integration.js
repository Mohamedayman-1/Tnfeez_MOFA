/**
 * Vanilla JavaScript WebSocket Integration
 * Real-time notification service for Oracle FBDI workflows
 */

class NotificationService {
    constructor(websocketUrl = 'ws://127.0.0.1:8000/ws/notifications/') {
        this.websocketUrl = websocketUrl;
        this.socket = null;
        this.callbacks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
        this.pingInterval = null;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        console.log('Connecting to WebSocket:', this.websocketUrl);
        
        this.socket = new WebSocket(this.websocketUrl);

        this.socket.onopen = (event) => {
            console.log('✅ WebSocket connected');
            this.reconnectAttempts = 0;
            this.trigger('connected', event);
            this.startPingPong();
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📩 Message received:', data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        this.socket.onclose = (event) => {
            console.log('❌ WebSocket closed:', event.code, event.reason);
            this.stopPingPong();
            this.trigger('disconnected', event);
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('⚠️ WebSocket error:', error);
            this.trigger('error', error);
        };
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.stopPingPong();
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.trigger('reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * this.reconnectAttempts;
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Start ping/pong for keep-alive
     */
    startPingPong() {
        this.pingInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.send({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop ping/pong
     */
    stopPingPong() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    /**
     * Send message to server
     */
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected. Cannot send message.');
        }
    }

    /**
     * Handle incoming messages
     */
    handleMessage(data) {
        const eventType = data.type;

        switch (eventType) {
            case 'connection_established':
                this.trigger('connectionEstablished', data);
                break;

            case 'oracle_upload_started':
                this.trigger('uploadStarted', data);
                break;

            case 'oracle_upload_progress':
                this.trigger('uploadProgress', data);
                break;

            case 'oracle_upload_completed':
                this.trigger('uploadCompleted', data);
                break;

            case 'oracle_upload_failed':
                this.trigger('uploadFailed', data);
                break;

            case 'notification':
                this.trigger('notification', data);
                break;

            case 'pong':
                // Pong received, connection alive
                break;

            default:
                console.log('Unknown message type:', eventType);
                this.trigger('unknown', data);
        }
    }

    /**
     * Register event callback
     */
    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }

    /**
     * Remove event callback
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event] = this.callbacks[event].filter(cb => cb !== callback);
        }
    }

    /**
     * Trigger event callbacks
     */
    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} callback:`, error);
                }
            });
        }
    }
}

// ============================================================================
// Usage Example
// ============================================================================

// Initialize notification service
const notifications = new NotificationService();

// Register event handlers
notifications.on('connected', () => {
    console.log('Connected to notification service');
    showToast('Connected to real-time updates', 'success');
});

notifications.on('disconnected', () => {
    console.log('Disconnected from notification service');
    showToast('Disconnected from real-time updates', 'warning');
});

notifications.on('uploadStarted', (data) => {
    console.log('Upload started:', data);
    showToast(`Upload started for transaction ${data.transaction_id}`, 'info');
    showProgressBar(0);
});

notifications.on('uploadProgress', (data) => {
    console.log('Upload progress:', data);
    const percentage = (data.step_number / data.total_steps) * 100;
    updateProgressBar(percentage, data.message);
    showToast(`${data.step}: ${data.message}`, 'info');
});

notifications.on('uploadCompleted', (data) => {
    console.log('Upload completed:', data);
    updateProgressBar(100, 'Completed!');
    showToast('Upload completed successfully!', 'success');
    setTimeout(hideProgressBar, 3000);
    refreshTransactionList();
});

notifications.on('uploadFailed', (data) => {
    console.error('Upload failed:', data);
    showToast(`Upload failed: ${data.error}`, 'error');
    hideProgressBar();
});

// Connect to WebSocket
notifications.connect();

// ============================================================================
// Helper Functions (implement these based on your UI framework)
// ============================================================================

function showToast(message, type = 'info') {
    // Implement toast notification
    console.log(`[${type.toUpperCase()}] ${message}`);
}

function showProgressBar(percentage) {
    const progressBar = document.getElementById('upload-progress');
    if (progressBar) {
        progressBar.style.display = 'block';
        progressBar.querySelector('.progress-fill').style.width = percentage + '%';
    }
}

function updateProgressBar(percentage, message) {
    const progressBar = document.getElementById('upload-progress');
    if (progressBar) {
        progressBar.querySelector('.progress-fill').style.width = percentage + '%';
        progressBar.querySelector('.progress-text').textContent = message;
    }
}

function hideProgressBar() {
    const progressBar = document.getElementById('upload-progress');
    if (progressBar) {
        progressBar.style.display = 'none';
    }
}

function refreshTransactionList() {
    // Reload transaction data
    console.log('Refreshing transaction list...');
}

// ============================================================================
// Cleanup on page unload
// ============================================================================

window.addEventListener('beforeunload', () => {
    notifications.disconnect();
});

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationService;
}
