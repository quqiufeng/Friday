/**
 * 音频处理模块
 * 负责麦克风录音、音频播放、语音可视化
 */

class AudioManager {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        
        // 音频播放器
        this.audioPlayer = document.getElementById('audioPlayer');
        
        // 可视化
        this.canvas = document.getElementById('audioCanvas');
        this.canvasCtx = this.canvas?.getContext('2d');
        this.visualizerId = null;
    }

    /**
     * 初始化音频上下文
     */
    async initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    /**
     * 开始录音
     */
    async startRecording() {
        try {
            await this.initAudioContext();
            
            // 获取麦克风权限
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });

            // 创建 MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            // 设置分析器用于可视化
            const source = this.audioContext.createMediaStreamSource(this.stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);

            // 开始录音
            this.mediaRecorder.start(100); // 每100ms收集一次数据
            this.isRecording = true;

            // 开始可视化
            this.startVisualization();

            console.log('🎤 录音开始');
            return true;

        } catch (error) {
            console.error('录音启动失败:', error);
            alert('无法访问麦克风，请检查权限设置');
            return false;
        }
    }

    /**
     * 停止录音
     */
    stopRecording() {
        return new Promise((resolve) => {
            if (!this.mediaRecorder || !this.isRecording) {
                resolve(null);
                return;
            }

            this.mediaRecorder.onstop = async () => {
                // 停止可视化
                this.stopVisualization();
                
                // 合并音频数据
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                
                // 转换为 WAV 格式
                const wavBlob = await this.convertToWav(audioBlob);
                
                // 转换为 base64
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64Audio = reader.result.split(',')[1];
                    resolve(base64Audio);
                };
                reader.readAsDataURL(wavBlob);

                // 清理
                this.audioChunks = [];
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                    this.stream = null;
                }
            };

            this.mediaRecorder.stop();
            this.isRecording = false;
            console.log('🎤 录音停止');
        });
    }

    /**
     * 将 WebM 转换为 WAV
     */
    async convertToWav(webmBlob) {
        const arrayBuffer = await webmBlob.arrayBuffer();
        const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
        
        // 重采样到 16kHz
        const targetSampleRate = 16000;
        const offlineContext = new OfflineAudioContext(
            1, 
            audioBuffer.duration * targetSampleRate, 
            targetSampleRate
        );
        
        const source = offlineContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(offlineContext.destination);
        source.start();
        
        const resampledBuffer = await offlineContext.startRendering();
        
        // 转换为 WAV
        return this.audioBufferToWav(resampledBuffer);
    }

    /**
     * AudioBuffer 转 WAV Blob
     */
    audioBufferToWav(audioBuffer) {
        const numberOfChannels = audioBuffer.numberOfChannels;
        const sampleRate = audioBuffer.sampleRate;
        const format = 1; // PCM
        const bitDepth = 16;
        
        const bytesPerSample = bitDepth / 8;
        const blockAlign = numberOfChannels * bytesPerSample;
        
        const dataLength = audioBuffer.length * numberOfChannels * bytesPerSample;
        const buffer = new ArrayBuffer(44 + dataLength);
        const view = new DataView(buffer);
        
        // 写入 WAV 头
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + dataLength, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, format, true);
        view.setUint16(22, numberOfChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * blockAlign, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bitDepth, true);
        writeString(36, 'data');
        view.setUint32(40, dataLength, true);
        
        // 写入音频数据
        const offset = 44;
        const channelData = audioBuffer.getChannelData(0);
        for (let i = 0; i < audioBuffer.length; i++) {
            const sample = Math.max(-1, Math.min(1, channelData[i]));
            view.setInt16(offset + i * 2, sample * 0x7FFF, true);
        }
        
        return new Blob([buffer], { type: 'audio/wav' });
    }

    /**
     * 开始语音可视化
     */
    startVisualization() {
        if (!this.canvas || !this.analyser) return;
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        const draw = () => {
            this.visualizerId = requestAnimationFrame(draw);
            
            this.analyser.getByteFrequencyData(dataArray);
            
            const width = this.canvas.width;
            const height = this.canvas.height;
            
            this.canvasCtx.clearRect(0, 0, width, height);
            
            const barWidth = (width / bufferLength) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                barHeight = (dataArray[i] / 255) * height;
                
                const gradient = this.canvasCtx.createLinearGradient(0, height, 0, height - barHeight);
                gradient.addColorStop(0, '#1a7f37');
                gradient.addColorStop(1, '#4ade80');
                
                this.canvasCtx.fillStyle = gradient;
                this.canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }

    /**
     * 停止可视化
     */
    stopVisualization() {
        if (this.visualizerId) {
            cancelAnimationFrame(this.visualizerId);
            this.visualizerId = null;
        }
        if (this.canvasCtx && this.canvas) {
            this.canvasCtx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    /**
     * 播放音频
     */
    playAudio(base64Audio) {
        return new Promise((resolve) => {
            const audioUrl = `data:audio/wav;base64,${base64Audio}`;
            this.audioPlayer.src = audioUrl;
            
            this.audioPlayer.onended = () => {
                resolve();
            };
            
            this.audioPlayer.onerror = () => {
                console.error('音频播放失败');
                resolve();
            };
            
            this.audioPlayer.play().catch(err => {
                console.error('播放失败:', err);
                resolve();
            });
        });
    }

    /**
     * 停止播放
     */
    stopPlayback() {
        this.audioPlayer.pause();
        this.audioPlayer.currentTime = 0;
    }
}

// 创建全局实例
window.audioManager = new AudioManager();
