// Notification system for Production Dashboard
class NotificationManager {
    constructor() {
        this.socket = null;
        this.notificationsList = document.getElementById('notifications-list');
        this.markAllReadBtn = document.getElementById('mark-all-read-btn');
        this.notificationBadge = document.querySelector('.notification-badge');
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.requestNotificationPermission();
        this.loadInitialNotifications();
    }
    
    initializeSocket() {
        // Connect to SocketIO server
        this.socket = io();
        
        // Notification events
        this.socket.on('new_notification', (notification) => {
            this.addNotificationToList(notification);
            this.playNotificationSound();
            this.showDesktopNotification(notification.title, notification.message);
            this.updateNotificationBadge();
        });
        
        this.socket.on('notification_marked_read', (data) => {
            this.markNotificationAsRead(data.notification_id);
        });
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Notification manager connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Notification manager disconnected');
        });
    }
    
    initializeEventListeners() {
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', () => {
                this.markAllNotificationsRead();
            });
        }
        
        // Mark individual notifications as read when clicked
        if (this.notificationsList) {
            this.notificationsList.addEventListener('click', (e) => {
                const notificationItem = e.target.closest('.notification-item');
                if (notificationItem) {
                    const notificationId = notificationItem.dataset.notificationId;
                    if (notificationId) {
                        this.markNotificationRead(notificationId);
                    }
                }
            });
        }
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, reduce polling frequency
                this.updateUserOnlineStatus(false);
            } else {
                // Page is visible, resume normal operation
                this.updateUserOnlineStatus(true);
            }
        });
    }
    
    requestNotificationPermission() {
        if ('Notification' in window) {
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    console.log('Notification permission:', permission);
                });
            }
        }
    }
    
    loadInitialNotifications() {
        // Load initial notifications via AJAX
        fetch('/production/api/notifications')
        .then(response => response.json())
        .then(data => {
            this.updateNotificationsList(data.notifications);
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
        });
    }
    
    updateNotificationsList(notifications) {
        if (!this.notificationsList) return;
        
        // Clear existing notifications
        this.notificationsList.innerHTML = '';
        
        if (notifications.length === 0) {
            this.notificationsList.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p>No new notifications</p>
                </div>
            `;
            return;
        }
        
        // Add notifications to list
        notifications.forEach(notification => {
            this.addNotificationToList(notification);
        });
        
        this.updateNotificationBadge();
    }
    
    addNotificationToList(notification) {
        if (!this.notificationsList) return;
        
        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification-item p-3 border-bottom ${notification.is_read ? 'read' : 'unread'}`;
        notificationDiv.setAttribute('data-notification-id', notification.id);
        
        notificationDiv.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="notification-icon me-3">
                    <i class="fas ${this.getNotificationIcon(notification.type)} text-${this.getNotificationColor(notification.type)}"></i>
                </div>
                <div class="notification-content flex-grow-1">
                    <div class="notification-title fw-bold">${notification.title}</div>
                    <div class="notification-message text-muted small">${notification.message}</div>
                    <div class="notification-time text-muted small">${this.formatTimeAgo(notification.created_at)}</div>
                </div>
                ${!notification.is_read ? '<div class="notification-unread-indicator"></div>' : ''}
            </div>
        `;
        
        // Add to the top of the list
        this.notificationsList.insertBefore(notificationDiv, this.notificationsList.firstChild);
        
        // Limit the number of notifications shown
        const notifications = this.notificationsList.querySelectorAll('.notification-item');
        if (notifications.length > 20) {
            notifications[notifications.length - 1].remove();
        }
    }
    
    markNotificationRead(notificationId) {
        fetch('/production/api/notifications/mark-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ notification_id: notificationId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.markNotificationAsRead(notificationId);
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }
    
    markNotificationAsRead(notificationId) {
        const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notificationItem) {
            notificationItem.classList.remove('unread');
            notificationItem.classList.add('read');
            
            const unreadIndicator = notificationItem.querySelector('.notification-unread-indicator');
            if (unreadIndicator) {
                unreadIndicator.remove();
            }
        }
        
        this.updateNotificationBadge();
    }
    
    markAllNotificationsRead() {
        fetch('/production/api/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mark all notifications as read in the UI
                const unreadNotifications = document.querySelectorAll('.notification-item.unread');
                unreadNotifications.forEach(item => {
                    item.classList.remove('unread');
                    item.classList.add('read');
                    const unreadIndicator = item.querySelector('.notification-unread-indicator');
                    if (unreadIndicator) {
                        unreadIndicator.remove();
                    }
                });
                
                this.updateNotificationBadge();
                this.showToast('All notifications marked as read', 'success');
            }
        })
        .catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
    }
    
    updateNotificationBadge() {
        if (!this.notificationBadge) return;
        
        const unreadCount = document.querySelectorAll('.notification-item.unread').length;
        
        if (unreadCount > 0) {
            this.notificationBadge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            this.notificationBadge.style.display = 'inline';
        } else {
            this.notificationBadge.style.display = 'none';
        }
    }
    
    showDesktopNotification(title, body, icon = null) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: icon || '/static/images/default-profile.png',
                badge: '/static/images/default-profile.png',
                tag: 'production-notification'
            });
        }
    }
    
    playNotificationSound() {
        const notificationSound = document.getElementById('notification-sound');
        if (notificationSound) {
            notificationSound.play().catch(e => console.log('Could not play notification sound:', e));
        }
    }
    
    showToast(message, type = 'info') {
        const toastContainer = this.getToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} show`;
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas ${this.getToastIcon(type)} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }
    
    getToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.cssText = 'z-index: 1055;';
            document.body.appendChild(container);
        }
        return container;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'task_assigned': 'fa-tasks',
            'task_completed': 'fa-check-circle',
            'task_status_change': 'fa-sync',
            'mention': 'fa-at',
            'deadline': 'fa-clock',
            'file_upload': 'fa-upload',
            'system': 'fa-cog'
        };
        return icons[type] || 'fa-bell';
    }
    
    getNotificationColor(type) {
        const colors = {
            'task_assigned': 'primary',
            'task_completed': 'success',
            'task_status_change': 'info',
            'mention': 'warning',
            'deadline': 'danger',
            'file_upload': 'info',
            'system': 'secondary'
        };
        return colors[type] || 'info';
    }
    
    getToastIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    }
    
    formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) {
            return 'Just now';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }
    }
    
    updateUserOnlineStatus(isOnline) {
        fetch('/production/api/users/update-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ is_online: isOnline })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('User online status updated:', isOnline);
            }
        })
        .catch(error => {
            console.error('Error updating user online status:', error);
        });
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
}); 