/**
 * 主应用逻辑
 * 整合音频、视觉、WebSocket 模块
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM 元素
    const micBtn = document.getElementById('micBtn');
    const sendBtn = document.getElementById('sendBtn');
    const textInput = document.getElementById('textInput');
    const chatContainer = document.getElementById('chatContainer');
    const voiceVisualizer = document.getElementById('voiceVisualizer');
    const toggleCamera = document.getElementById('toggleCamera');
    const uploadBtn = document.getElementById('uploadBtn');
    const imageInput = document.getElementById('imageInput');
    const clearImage = document.getElementById('clearImage');

    // 状态
    let isRecording = false;
    let isProcessing = false;

    // 初始化 WebSocket
    window.wsManager.connect();

    // 注册 WebSocket 消息处理器
    window.wsManager.on('connected', () => {
        console.log('WebSocket 已连接，可以开始对话');
    });

    window.wsManager.on('text_response', (message) => {
        addMessage('ai', message.text);
        isProcessing = false;
        updateUIState();
    });

    window.wsManager.on('audio_response', async (message) => {
        // 播放语音回复
        if (message.audio) {
            await window.audioManager.playAudio(message.audio);
        }
    });

    window.wsManager.on('asr_result', (message) => {
        // 显示语音识别结果
        if (message.text) {
            textInput.value = message.text;
            textInput.style.height = 'auto';
            textInput.style.height = textInput.scrollHeight + 'px';
        }
    });

    // ============ 事件绑定 ============

    // 麦克风按钮
    micBtn.addEventListener('click', async () => {
        if (isRecording) {
            // 停止录音
            const audioData = await window.audioManager.stopRecording();
            isRecording = false;
            micBtn.classList.remove('active');
            voiceVisualizer.style.display = 'none';

            if (audioData) {
                // 发送语音
                window.wsManager.sendAudio(audioData);
                addMessage('user', '🎤 语音消息');
                isProcessing = true;
                updateUIState();
            }
        } else {
            // 开始录音
            const success = await window.audioManager.startRecording();
            if (success) {
                isRecording = true;
                micBtn.classList.add('active');
                voiceVisualizer.style.display = 'flex';
            }
        }
    });

    // 发送按钮
    sendBtn.addEventListener('click', sendMessage);

    // 文本输入框 - 回车发送
    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 文本输入框 - 自动调整高度
    textInput.addEventListener('input', () => {
        textInput.style.height = 'auto';
        textInput.style.height = textInput.scrollHeight + 'px';
    });

    // 摄像头按钮
    toggleCamera.addEventListener('click', () => {
        window.visionManager.toggleCamera();
    });

    // 上传图片按钮
    uploadBtn.addEventListener('click', () => {
        imageInput.click();
    });

    // 图片选择
    imageInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await window.visionManager.loadImageFromFile(file);
        }
    });

    // 清除图片
    clearImage.addEventListener('click', () => {
        window.visionManager.clearImage();
        imageInput.value = '';
    });

    // ============ 功能函数 ============

    /**
     * 发送消息
     */
    function sendMessage() {
        const text = textInput.value.trim();
        if (!text && !window.visionManager.hasImage()) return;
        if (isProcessing) return;

        // 获取图片
        const imageData = window.visionManager.getCurrentImage();

        if (imageData) {
            // 发送图片+文本
            window.wsManager.sendImage(imageData, text);
            addMessage('user', text || '📷 图片');
            window.visionManager.clearImage();
        } else {
            // 发送纯文本
            window.wsManager.sendText(text);
            addMessage('user', text);
        }

        // 清空输入
        textInput.value = '';
        textInput.style.height = 'auto';

        isProcessing = true;
        updateUIState();
    }

    /**
     * 添加消息到聊天窗口
     */
    function addMessage(role, text) {
        // 隐藏欢迎消息
        const welcomeMsg = chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'none';
        }

        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = role === 'user' ? '我' : 'AI';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = text;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        chatContainer.appendChild(messageDiv);

        // 滚动到底部
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    /**
     * 更新 UI 状态
     */
    function updateUIState() {
        sendBtn.disabled = isProcessing;
        micBtn.disabled = isProcessing;
        textInput.disabled = isProcessing;

        if (isProcessing) {
            sendBtn.innerHTML = '<span class="loading"></span>';
        } else {
            sendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"/>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
            `;
        }
    }

    // 初始化
    console.log('🚀 Friday AI 助手已启动');
});
