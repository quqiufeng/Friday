/**
 * WebSocket 通信模块
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.messageHandlers = new Map();
        this.connectionStatusEl = document.getElementById('connectionStatus');
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        console.log('🔌 正在连接 WebSocket...', wsUrl);
        this.updateStatus('connecting', '连接中...');
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket 已连接');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateStatus('connected', '已连接');
                this.emit('connected');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('消息解析失败:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                this.updateStatus('error', '连接错误');
            };
            
            this.ws.onclose = () => {
                console.log('🔌 WebSocket 已断开');
                this.isConnected = false;
                this.updateStatus('disconnected', '已断开');
                this.attemptReconnect();
            };
            
        } catch (error) {
            console.error('WebSocket 连接失败:', error);
            this.updateStatus('error', '连接失败');
            this.attemptReconnect();
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('重连次数已达上限');
            this.updateStatus('error', '连接失败，请刷新页面');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`⏳ ${this.reconnectAttempts}秒后尝试重连...`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }

    send(message) {
        if (!this.isConnected) {
            console.error('WebSocket 未连接');
            return false;
        }
        
        try {
            this.ws.send(JSON.stringify(message));
            return true;
        } catch (error) {
            console.error('发送消息失败:', error);
            return false;
        }
    }

    sendText(text) {
        return this.send({
            type: 'text',
            text: text
        });
    }

    sendAudio(base64Audio) {
        return this.send({
            type: 'audio',
            data: base64Audio
        });
    }

    sendImage(base64Image, text = '') {
        return this.send({
            type: 'image',
            data: base64Image,
            text: text
        });
    }

    handleMessage(message) {
        const { type } = message;
        this.emit(type, message);
        
        switch (type) {
            case 'text_response':
                console.log('💬 AI 回复:', message.text);
                break;
            case 'audio_response':
                console.log('🔊 收到语音回复');
                break;
            case 'asr_result':
                console.log('🎤 语音识别:', message.text);
                break;
            case 'error':
                console.error('❌ 服务器错误:', message.message);
                break;
        }
    }

    on(event, handler) {
        if (!this.messageHandlers.has(event)) {
            this.messageHandlers.set(event, []);
        }
        this.messageHandlers.get(event).push(handler);
    }

    off(event, handler) {
        if (this.messageHandlers.has(event)) {
            const handlers = this.messageHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.messageHandlers.has(event)) {
            this.messageHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error('事件处理器错误:', error);
                }
            });
        }
    }

    updateStatus(status, text) {
        if (this.connectionStatusEl) {
            const dot = this.connectionStatusEl.querySelector('.status-dot');
            const textEl = this.connectionStatusEl.querySelector('.status-text');
            
            dot.className = 'status-dot ' + status;
            textEl.textContent = text;
        }
    }
}

window.wsManager = new WebSocketManager();