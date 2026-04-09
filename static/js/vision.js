/**
 * 摄像头/视觉处理模块
 * 负责摄像头控制、截图、图片处理
 */

class VisionManager {
    constructor() {
        this.video = document.getElementById('cameraVideo');
        this.videoContainer = document.getElementById('videoContainer');
        this.videoPlaceholder = document.getElementById('videoPlaceholder');
        this.imagePreview = document.getElementById('imagePreview');
        this.previewImg = document.getElementById('previewImg');
        this.stream = null;
        this.isCameraOn = false;
        this.capturedImage = null;
    }

    /**
     * 切换摄像头状态
     */
    async toggleCamera() {
        if (this.isCameraOn) {
            await this.stopCamera();
        } else {
            await this.startCamera();
        }
    }

    /**
     * 启动摄像头
     */
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            });

            this.video.srcObject = this.stream;
            this.video.style.display = 'block';
            this.videoPlaceholder.style.display = 'none';
            this.isCameraOn = true;

            console.log('📷 摄像头已启动');
            return true;

        } catch (error) {
            console.error('摄像头启动失败:', error);
            alert('无法访问摄像头，请检查权限设置');
            return false;
        }
    }

    /**
     * 停止摄像头
     */
    async stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.video.srcObject = null;
        this.video.style.display = 'none';
        this.videoPlaceholder.style.display = 'flex';
        this.isCameraOn = false;
        
        console.log('📷 摄像头已关闭');
    }

    /**
     * 截图
     */
    captureImage() {
        if (!this.isCameraOn) {
            console.warn('摄像头未启动');
            return null;
        }

        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
        
        // 压缩图片
        const base64Image = canvas.toDataURL('image/jpeg', 0.8);
        this.capturedImage = base64Image.split(',')[1];
        
        // 显示预览
        this.showImagePreview(base64Image);
        
        return this.capturedImage;
    }

    /**
     * 从文件加载图片
     */
    async loadImageFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    // 压缩图片
                    const canvas = document.createElement('canvas');
                    const maxSize = 1024;
                    let width = img.width;
                    let height = img.height;
                    
                    if (width > height) {
                        if (width > maxSize) {
                            height *= maxSize / width;
                            width = maxSize;
                        }
                    } else {
                        if (height > maxSize) {
                            width *= maxSize / height;
                            height = maxSize;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    const base64Image = canvas.toDataURL('image/jpeg', 0.8);
                    this.capturedImage = base64Image.split(',')[1];
                    
                    // 显示预览
                    this.showImagePreview(base64Image);
                    
                    resolve(this.capturedImage);
                };
                
                img.onerror = reject;
                img.src = e.target.result;
            };
            
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    /**
     * 显示图片预览
     */
    showImagePreview(base64Url) {
        this.previewImg.src = base64Url;
        this.imagePreview.style.display = 'block';
    }

    /**
     * 清除图片
     */
    clearImage() {
        this.capturedImage = null;
        this.previewImg.src = '';
        this.imagePreview.style.display = 'none';
    }

    /**
     * 获取当前图片
     */
    getCurrentImage() {
        return this.capturedImage;
    }

    /**
     * 检查是否有图片
     */
    hasImage() {
        return !!this.capturedImage;
    }
}

// 创建全局实例
window.visionManager = new VisionManager();
