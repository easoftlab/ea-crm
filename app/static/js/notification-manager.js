class NotificationManager {
    constructor() {
        this.notificationPermission = 'default';
        this.soundEnabled = true;
        this.vibrationEnabled = true;
        this.toastQueue = [];
        this.isShowingToast = false;
        
        this.initialize();
    }
    
    initialize() {
        this.checkNotificationPermission();
        this.setupSoundElements();
        this.setupVibrationSupport();
        this.loadUserPreferences();
        
        // Request permission on first visit
        if (!localStorage.getItem('notification_permission_requested')) {
            setTimeout(() => {
                this.requestNotificationPermission();
            }, 3000);
        }
    }
    
    // Desktop Notifications (Feature #12)
    checkNotificationPermission() {
        if ('Notification' in window) {
            this.notificationPermission = Notification.permission;
        }
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && this.notificationPermission === 'default') {
            Notification.requestPermission().then((permission) => {
                this.notificationPermission = permission;
                if (permission === 'granted') {
                    this.showToast('🔔 Desktop notifications enabled', 'success');
                    localStorage.setItem('notification_permission_requested', 'true');
                } else {
                    this.showToast('🔕 Desktop notifications disabled', 'warning');
                }
            });
        }
    }
    
    showDesktopNotification(title, body, options = {}) {
        if (!('Notification' in window) || this.notificationPermission !== 'granted') {
            return false;
        }
        
        const defaultOptions = {
            icon: '/static/images/icon-192x192.png',
            badge: '/static/images/badge-72x72.png',
            tag: 'chat-message',
            requireInteraction: false,
            silent: false,
            data: {}
        };
        
        const notificationOptions = { ...defaultOptions, ...options };
        
        try {
            const notification = new Notification(title, notificationOptions);
            
            notification.onclick = () => {
                window.focus();
                notification.close();
                
                // Navigate to specific page if data contains URL
                if (notificationOptions.data.url) {
                    window.location.href = notificationOptions.data.url;
                }
            };
            
            return true;
        } catch (error) {
            console.error('Error showing desktop notification:', error);
            return false;
        }
    }
    
    // In-App Toast Notifications (Feature #13)
    showToast(message, type = 'info', options = {}) {
        const defaultOptions = {
            duration: 4000,
            position: 'bottom-right',
            showCloseButton: true,
            showReplyButton: false,
            replyCallback: null,
            markAsReadCallback: null
        };
        
        const toastOptions = { ...defaultOptions, ...options };
        
        // Add to queue if already showing a toast
        if (this.isShowingToast) {
            this.toastQueue.push({ message, type, options: toastOptions });
            return;
        }
        
        this.createToastElement(message, type, toastOptions);
    }
    
    createToastElement(message, type, options) {
        this.isShowingToast = true;
        
        const toast = document.createElement('div');
        toast.className = `notification-toast notification-toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            ${options.position.includes('bottom') ? 'bottom: 20px' : 'top: 20px'};
            ${options.position.includes('right') ? 'right: 20px' : 'left: 20px'};
            background: ${this.getToastColor(type)};
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10001;
            max-width: 400px;
            min-width: 300px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.4;
            transform: translateX(${options.position.includes('right') ? '100%' : '-100%'});
            opacity: 0;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
        `;
        
        // Toast content
        const content = document.createElement('div');
        content.style.flex = '1';
        content.innerHTML = `
            <div style="font-weight: 500; margin-bottom: 4px;">${this.getToastIcon(type)} ${message}</div>
        `;
        
        // Action buttons container
        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '8px';
        actions.style.alignItems = 'center';
        
        // Reply button
        if (options.showReplyButton && options.replyCallback) {
            const replyBtn = document.createElement('button');
            replyBtn.innerHTML = '<i class="fas fa-reply"></i>';
            replyBtn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            `;
            replyBtn.onclick = () => {
                options.replyCallback();
                this.removeToast(toast);
            };
            actions.appendChild(replyBtn);
        }
        
        // Mark as read button
        if (options.markAsReadCallback) {
            const readBtn = document.createElement('button');
            readBtn.innerHTML = '<i class="fas fa-check"></i>';
            readBtn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            `;
            readBtn.onclick = () => {
                options.markAsReadCallback();
                this.removeToast(toast);
            };
            actions.appendChild(readBtn);
        }
        
        // Close button
        if (options.showCloseButton) {
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '<i class="fas fa-times"></i>';
            closeBtn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                margin-left: 8px;
            `;
            closeBtn.onclick = () => this.removeToast(toast);
            actions.appendChild(closeBtn);
        }
        
        toast.appendChild(content);
        toast.appendChild(actions);
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        }, 10);
        
        // Auto remove after duration
        setTimeout(() => {
            this.removeToast(toast);
        }, options.duration);
    }
    
    removeToast(toast) {
        toast.style.transform = `translateX(${toast.style.left === '20px' ? '-100%' : '100%'})`;
        toast.style.opacity = '0';
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.isShowingToast = false;
            
            // Show next toast in queue
            if (this.toastQueue.length > 0) {
                const nextToast = this.toastQueue.shift();
                this.showToast(nextToast.message, nextToast.type, nextToast.options);
            }
        }, 300);
    }
    
    getToastColor(type) {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8',
            mention: '#e83e8c',
            message: '#6f42c1'
        };
        return colors[type] || colors.info;
    }
    
    getToastIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
            mention: '@',
            message: '💬'
        };
        return icons[type] || icons.info;
    }
    
    // Sound + Vibration (Feature #14)
    setupSoundElements() {
        // Create audio elements if they don't exist
        const soundTypes = ['message', 'mention', 'task', 'notification'];
        
        soundTypes.forEach(type => {
            if (!document.getElementById(`${type}-sound`)) {
                const audio = document.createElement('audio');
                audio.id = `${type}-sound`;
                audio.preload = 'auto';
                audio.src = `/static/sounds/${type}.wav`;
                document.body.appendChild(audio);
            }
        });
    }
    
    setupVibrationSupport() {
        this.vibrationEnabled = 'vibrate' in navigator;
    }
    
    playSound(type) {
        if (!this.soundEnabled) return;
        
        const audio = document.getElementById(`${type}-sound`);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(e => console.log(`Could not play ${type} sound:`, e));
        }
    }
    
    vibrate(pattern = [100, 50, 100]) {
        if (!this.vibrationEnabled) return;
        
        try {
            navigator.vibrate(pattern);
        } catch (error) {
            console.log('Vibration not supported or blocked');
        }
    }
    
    // Combined notification methods
    notifyNewMessage(senderName, messageContent, options = {}) {
        const title = `New message from ${senderName}`;
        const body = messageContent.length > 100 ? messageContent.substring(0, 100) + '...' : messageContent;
        
        // Desktop notification
        this.showDesktopNotification(title, body, {
            tag: 'chat-message',
            data: { url: '/production/messenger' }
        });
        
        // In-app toast
        this.showToast(`${senderName}: ${body}`, 'message', {
            showReplyButton: true,
            replyCallback: () => {
                window.location.href = '/production/messenger';
            }
        });
        
        // Sound and vibration
        this.playSound('message');
        this.vibrate([100, 50, 100]);
    }
    
    notifyMention(mentionedBy, messageContent, options = {}) {
        const title = `You were mentioned by ${mentionedBy}`;
        const body = messageContent.length > 100 ? messageContent.substring(0, 100) + '...' : messageContent;
        
        // Desktop notification
        this.showDesktopNotification(title, body, {
            tag: 'mention',
            requireInteraction: true,
            data: { url: '/production/messenger' }
        });
        
        // In-app toast
        this.showToast(`@${mentionedBy} mentioned you: ${body}`, 'mention', {
            showReplyButton: true,
            replyCallback: () => {
                window.location.href = '/production/messenger';
            }
        });
        
        // Sound and vibration
        this.playSound('mention');
        this.vibrate([200, 100, 200, 100, 200]);
    }
    
    notifyTaskUpdate(taskTitle, updateType, options = {}) {
        const title = `Task Update: ${taskTitle}`;
        const body = `Task has been ${updateType}`;
        
        // Desktop notification
        this.showDesktopNotification(title, body, {
            tag: 'task-update',
            data: { url: '/production/tasks' }
        });
        
        // In-app toast
        this.showToast(`${taskTitle} - ${updateType}`, 'info', {
            markAsReadCallback: () => {
                // Mark task notification as read
                console.log('Task notification marked as read');
            }
        });
        
        // Sound and vibration
        this.playSound('notification');
        this.vibrate([100, 50, 100, 50]);
    }
    
    // User preferences
    loadUserPreferences() {
        this.soundEnabled = localStorage.getItem('sound_enabled') !== 'false';
        this.vibrationEnabled = localStorage.getItem('vibration_enabled') !== 'false';
    }
    
    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('sound_enabled', this.soundEnabled);
        this.showToast(`Sound ${this.soundEnabled ? 'enabled' : 'disabled'}`, 'info');
    }
    
    toggleVibration() {
        this.vibrationEnabled = !this.vibrationEnabled;
        localStorage.setItem('vibration_enabled', this.vibrationEnabled);
        this.showToast(`Vibration ${this.vibrationEnabled ? 'enabled' : 'disabled'}`, 'info');
    }
    
    // Utility methods
    isNotificationSupported() {
        return 'Notification' in window;
    }
    
    isVibrationSupported() {
        return 'vibrate' in navigator;
    }
    
    getNotificationStatus() {
        return {
            desktop: this.notificationPermission,
            sound: this.soundEnabled,
            vibration: this.vibrationEnabled && this.isVibrationSupported()
        };
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
}); 