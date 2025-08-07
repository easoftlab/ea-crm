class FacebookNotifications {
    constructor() {
        this.socket = null;
        this.notificationsList = document.getElementById('notifications-list');
        this.notificationsCount = document.getElementById('notifications-count');
        this.markAllReadBtn = document.getElementById('mark-all-read-btn');
        this.notificationsToggle = document.getElementById('notifications-toggle');
        this.notificationsDropdown = document.getElementById('notifications-dropdown');
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.loadInitialNotifications();
        this.requestNotificationPermission();
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Facebook notifications connected to SocketIO');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Facebook notifications disconnected from SocketIO');
        });
        
        this.socket.on('new_notification', (notification) => {
            this.addNotificationToUI(notification);
            this.updateNotificationCount();
            this.showDesktopNotification(notification);
            this.playNotificationSound();
        });
        
        this.socket.on('notification_marked_read', (data) => {
            this.markNotificationAsRead(data.notification_id);
        });
    }
    
    initializeEventListeners() {
        // Mark all notifications as read
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.markAllNotificationsAsRead();
            });
        }
        
        // Mark individual notification as read
        if (this.notificationsList) {
            this.notificationsList.addEventListener('click', (e) => {
                const notificationItem = e.target.closest('.notification-item');
                if (notificationItem) {
                    const notificationId = notificationItem.dataset.notificationId;
                    if (notificationId) {
                        this.markNotificationAsRead(notificationId);
                    }
                }
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.notificationsToggle.contains(e.target) && !this.notificationsDropdown.contains(e.target)) {
                this.notificationsDropdown.style.display = 'none';
            }
        });
    }
    
    loadInitialNotifications() {
        fetch('/production/api/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.notifications) {
                    this.renderNotifications(data.notifications);
                    this.updateNotificationCount();
                }
            })
            .catch(error => {
                console.error('Error loading notifications:', error);
            });
    }
    
    renderNotifications(notifications) {
        if (!this.notificationsList) return;
        
        this.notificationsList.innerHTML = '';
        
        if (notifications.length === 0) {
            this.notificationsList.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #666;">
                    <i class="fas fa-bell" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>
                    <p>No notifications yet</p>
                </div>
            `;
            return;
        }
        
        notifications.forEach(notification => {
            this.addNotificationToUI(notification);
        });
    }
    
    addNotificationToUI(notification) {
        if (!this.notificationsList) return;
        
        const notificationElement = document.createElement('div');
        notificationElement.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
        notificationElement.dataset.notificationId = notification.id;
        
        const iconClass = this.getNotificationIcon(notification.type);
        const iconColor = this.getNotificationColor(notification.type);
        
        notificationElement.innerHTML = `
            <div class="notification-icon" style="background: ${iconColor};">
                <i class="${iconClass}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                <div class="notification-message">${this.escapeHtml(notification.message)}</div>
                <div class="notification-time">${notification.time_ago || this.formatTime(notification.created_at)}</div>
            </div>
            ${!notification.is_read ? '<div class="notification-dot"></div>' : ''}
        `;
        
        // Add to the top of the list
        if (this.notificationsList.firstChild) {
            this.notificationsList.insertBefore(notificationElement, this.notificationsList.firstChild);
        } else {
            this.notificationsList.appendChild(notificationElement);
        }
    }
    
    markNotificationAsRead(notificationId) {
        // Update UI immediately
        const notificationElement = this.notificationsList.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notificationElement) {
            notificationElement.classList.remove('unread');
            const dot = notificationElement.querySelector('.notification-dot');
            if (dot) dot.remove();
        }
        
        // Send to server via SocketIO
        if (this.socket && this.socket.connected) {
            this.socket.emit('notification_read', { notification_id: notificationId });
        } else {
            // Fallback to AJAX
            fetch('/production/api/notifications/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ notification_id: notificationId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateNotificationCount();
                }
            })
            .catch(error => {
                console.error('Error marking notification as read:', error);
            });
        }
    }
    
    markAllNotificationsAsRead() {
        // Update UI immediately
        const unreadNotifications = this.notificationsList.querySelectorAll('.notification-item.unread');
        unreadNotifications.forEach(item => {
            item.classList.remove('unread');
            const dot = item.querySelector('.notification-dot');
            if (dot) dot.remove();
        });
        
        // Send to server
        fetch('/production/api/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateNotificationCount();
            }
        })
        .catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
    }
    
    updateNotificationCount() {
        if (!this.notificationsCount) return;
        
        const unreadCount = this.notificationsList.querySelectorAll('.notification-item.unread').length;
        
        if (unreadCount > 0) {
            this.notificationsCount.textContent = unreadCount > 99 ? '99+' : unreadCount;
            this.notificationsCount.style.display = 'flex';
        } else {
            this.notificationsCount.style.display = 'none';
        }
    }
    
    showDesktopNotification(notification) {
        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/static/images/default-profile.png',
                badge: '/static/images/default-profile.png'
            });
        }
    }
    
    playNotificationSound() {
        const audio = document.getElementById('notification-sound');
        if (audio) {
            audio.play().catch(e => console.log('Could not play notification sound'));
        }
    }
    
    requestNotificationPermission() {
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            'task_assigned': 'fas fa-tasks',
            'task_completed': 'fas fa-check-circle',
            'task_status_change': 'fas fa-edit',
            'mention': 'fas fa-at',
            'message': 'fas fa-comment',
            'file_upload': 'fas fa-file-upload',
            'deadline': 'fas fa-clock',
            'overdue': 'fas fa-exclamation-triangle',
            'default': 'fas fa-bell'
        };
        return icons[type] || icons.default;
    }
    
    getNotificationColor(type) {
        const colors = {
            'task_assigned': '#667eea',
            'task_completed': '#28a745',
            'task_status_change': '#ffc107',
            'mention': '#e74c3c',
            'message': '#17a2b8',
            'file_upload': '#6f42c1',
            'deadline': '#fd7e14',
            'overdue': '#dc3545',
            'default': '#6c757d'
        };
        return colors[type] || colors.default;
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize Facebook notifications when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('notifications-toggle')) {
        window.facebookNotifications = new FacebookNotifications();
    }
}); 