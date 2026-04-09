/**
 * 主应用逻辑
 */

document.addEventListener('DOMContentLoaded', () => {
    const micBtn = document.getElementById('micBtn');
    const sendBtn = document.getElementById('sendBtn');
    const textInput = document.getElementById('textInput');
    const chatContainer = document.getElementById('chatContainer');
    const voiceVisualizer = document.getElementById('voiceVisualizer');
    const toggleCamera = document.getElementById('toggleCamera');
    const uploadBtn = document.getElementById('uploadBtn');
    const imageInput = document.getElementById('imageInput');
    const clearImage = document.getElementById('clearImage');

    let isRecording = false;
    let isProcessing = false;

    window.wsManager.connect();

    window.wsManager.on('connected', () => {
        console.log('WebSocket 已连接，可以开始对话');
    });

    window.wsManager.on('text_response', (message) => {
        addMessage('ai', message.text);
        isProcessing = false;
        updateUIState();
    });

    window.wsManager.on('audio_response', async (message) => {
        if (message.audio) {
            await window.audioManager.playAudio(message.audio);
        }
    });

    window.wsManager.on('asr_result', (message) => {
        if (message.text) {
            textInput.value = message.text;
            textInput.style.height = 'auto';
            textInput.style.height = textInput.scrollHeight + 'px';
        }
    });

    micBtn.addEventListener('click', async () => {
        if (isRecording) {
            const audioData = await window.audioManager.stopRecording();
            isRecording = false;
            micBtn.classList.remove('active');
            voiceVisualizer.style.display = 'none';

            if (audioData) {
                window.wsManager.sendAudio(audioData);
                addMessage('user', '🎤 语音消息');
                isProcessing = true;
                updateUIState();
            }
        } else {
            const success = await window.audioManager.startRecording();
            if (success) {
                isRecording = true;
                micBtn.classList.add('active');
                voiceVisualizer.style.display = 'flex';
            }
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    textInput.addEventListener('input', () => {
        textInput.style.height = 'auto';
        textInput.style.height = textInput.scrollHeight + 'px';
    });

    toggleCamera.addEventListener('click', () => {
        window.visionManager.toggleCamera();
    });

    uploadBtn.addEventListener('click', () => {
        imageInput.click();
    });

    imageInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await window.visionManager.loadImageFromFile(file);
        }
    });

    clearImage.addEventListener('click', () => {
        window.visionManager.clearImage();
        imageInput.value = '';
    });

    function sendMessage() {
        const text = textInput.value.trim();
        if (!text && !window.visionManager.hasImage()) return;
        if (isProcessing) return;

        const imageData = window.visionManager.getCurrentImage();

        if (imageData) {
            window.wsManager.sendImage(imageData, text);
            addMessage('user', text || '📷 图片');
            window.visionManager.clearImage();
        } else {
            window.wsManager.sendText(text);
            addMessage('user', text);
        }

        textInput.value = '';
        textInput.style.height = 'auto';

        isProcessing = true;
        updateUIState();
    }

    function addMessage(role, text) {
        const welcomeMsg = chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'none';
        }

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
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

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

    console.log('🚀 Friday AI 助手已启动');
});