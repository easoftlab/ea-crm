// Dashboard functionality for Production Dashboard
class DashboardManager {
    constructor() {
        this.socket = null;
        this.activityStatus = document.querySelector('.activity-indicator');
        this.currentApp = document.querySelector('.current-app');
        this.sessionTime = document.querySelector('.session-time');
        this.startTime = Date.now();
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.startRealTimeUpdates();
        this.updateSessionTimer();
    }
    
    initializeSocket() {
        // Connect to SocketIO server
        this.socket = io();
        
        // Dashboard update events
        this.socket.on('dashboard_data_update', (data) => {
            this.updateTaskCounts(data);
            this.updateOnlineUsers(data);
            this.updateUnreadNotifications(data);
        });
        
        // Task update events
        this.socket.on('task_updated', (data) => {
            this.handleTaskUpdate(data);
        });
        
        // User online/offline events
        this.socket.on('user_online', (data) => {
            this.updateOnlineUsers();
        });
        
        this.socket.on('user_offline', (data) => {
            this.updateOnlineUsers();
        });
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Dashboard manager connected');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Dashboard manager disconnected');
            this.updateConnectionStatus(false);
        });
    }
    
    initializeEventListeners() {
        // Update user online status based on page visibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.updateUserOnlineStatus(false);
            } else {
                this.updateUserOnlineStatus(true);
            }
        });
        
        // Update user online status based on window focus
        window.addEventListener('focus', () => {
            this.updateUserOnlineStatus(true);
        });
        
        window.addEventListener('blur', () => {
            this.updateUserOnlineStatus(false);
        });
        
        // Handle task status updates
        document.addEventListener('click', (e) => {
            if (e.target.closest('.task-status-btn')) {
                const taskId = e.target.closest('.task-status-btn').dataset.taskId;
                const newStatus = e.target.closest('.task-status-btn').dataset.status;
                this.updateTaskStatus(taskId, newStatus);
            }
        });
        
        // Handle task assignments
        document.addEventListener('click', (e) => {
            if (e.target.closest('.assign-task-btn')) {
                const taskId = e.target.closest('.assign-task-btn').dataset.taskId;
                const userId = e.target.closest('.assign-task-btn').dataset.userId;
                this.assignTask(taskId, userId);
            }
        });
    }
    
    startRealTimeUpdates() {
        // Update dashboard data every 30 seconds as fallback
        setInterval(() => {
            this.updateDashboardData();
        }, 30000);
        
        // Update session timer every second
        setInterval(() => {
            this.updateSessionTimer();
        }, 1000);
    }
    
    updateDashboardData() {
        fetch('/production/api/dashboard_data')
        .then(response => response.json())
        .then(data => {
            this.updateTaskCounts(data);
            this.updateOnlineUsers(data);
            this.updateUnreadNotifications(data);
        })
        .catch(error => {
            console.error('Error updating dashboard data:', error);
        });
    }
    
    updateTaskCounts(data) {
        // Update task count displays
        const taskCountElements = {
            'pending_count': document.querySelector('.stat-card.pending h3'),
            'in_progress_count': document.querySelector('.stat-card.in-progress h3'),
            'completed_count': document.querySelector('.stat-card.completed h3'),
            'overdue_count': document.querySelector('.stat-card.overdue h3')
        };
        
        Object.entries(taskCountElements).forEach(([key, element]) => {
            if (element && data[key] !== undefined) {
                element.textContent = data[key];
                
                // Add animation for changes
                element.style.animation = 'pulse 0.5s ease-in-out';
                setTimeout(() => {
                    element.style.animation = '';
                }, 500);
            }
        });
    }
    
    updateOnlineUsers(data) {
        const onlineUsersElement = document.querySelector('.online-users small');
        if (onlineUsersElement && data.online_users_count !== undefined) {
            onlineUsersElement.textContent = `${data.online_users_count} online`;
        }
    }
    
    updateUnreadNotifications(data) {
        if (data.unread_notifications_count !== undefined) {
            // Update notification badge if it exists
            const notificationBadge = document.querySelector('.notification-badge');
            if (notificationBadge) {
                if (data.unread_notifications_count > 0) {
                    notificationBadge.textContent = data.unread_notifications_count;
                    notificationBadge.style.display = 'inline';
                } else {
                    notificationBadge.style.display = 'none';
                }
            }
        }
    }
    
    handleTaskUpdate(data) {
        // Update task display if it exists on the page
        const taskElement = document.querySelector(`[data-task-id="${data.task_id}"]`);
        if (taskElement) {
            const statusBadge = taskElement.querySelector('.task-status-badge');
            if (statusBadge) {
                statusBadge.textContent = data.status.replace('_', ' ').toUpperCase();
                statusBadge.className = `task-status-badge badge bg-${this.getStatusColor(data.status)}`;
            }
            
            // Show toast notification
            this.showToast(`Task ${data.task_id} status updated to ${data.status} by ${data.updated_by}`, 'info');
        }
    }
    
    updateTaskStatus(taskId, newStatus) {
        fetch(`/production/api/tasks/${taskId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ status: newStatus })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Emit task update via SocketIO
                this.socket.emit('task_status_update', {
                    task_id: taskId,
                    status: newStatus
                });
                
                this.showToast(data.message, 'success');
            } else {
                this.showToast(data.error || 'Failed to update task status', 'error');
            }
        })
        .catch(error => {
            console.error('Error updating task status:', error);
            this.showToast('Error updating task status', 'error');
        });
    }
    
    assignTask(taskId, userId) {
        fetch(`/production/api/tasks/${taskId}/assign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ assigned_to: userId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast(data.message, 'success');
            } else {
                this.showToast(data.error || 'Failed to assign task', 'error');
            }
        })
        .catch(error => {
            console.error('Error assigning task:', error);
            this.showToast('Error assigning task', 'error');
        });
    }
    
    updateUserOnlineStatus(isOnline = true) {
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
    
    updateSessionTimer() {
        if (this.sessionTime) {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            const seconds = elapsed % 60;
            
            this.sessionTime.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }
    
    updateActivityStatus(status) {
        if (this.activityStatus) {
            const icon = this.activityStatus.querySelector('i');
            const text = this.activityStatus.querySelector('span');
            
            if (status === 'active') {
                icon.className = 'fas fa-circle text-success';
                text.textContent = 'Active';
                this.activityStatus.className = 'activity-indicator active';
            } else {
                icon.className = 'fas fa-circle text-danger';
                text.textContent = 'Inactive';
                this.activityStatus.className = 'activity-indicator inactive';
            }
        }
    }
    
    updateCurrentApp(appName) {
        if (this.currentApp) {
            this.currentApp.textContent = appName || '-';
        }
    }
    
    updateProductivityScore(score) {
        const scoreElement = document.querySelector('.productivity-score');
        if (scoreElement) {
            scoreElement.textContent = `${score.toFixed(1)}%`;
            
            // Update color based on score
            if (score >= 80) {
                scoreElement.className = 'productivity-score text-success';
            } else if (score >= 60) {
                scoreElement.className = 'productivity-score text-warning';
            } else {
                scoreElement.className = 'productivity-score text-danger';
            }
        }
    }
    
    showToast(message, type = 'info') {
        if (window.notificationManager) {
            window.notificationManager.showToast(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    updateConnectionStatus(isConnected) {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            statusIndicator.className = `connection-status ${isConnected ? 'connected' : 'disconnected'}`;
            statusIndicator.textContent = isConnected ? '🟢 Connected' : '🔴 Disconnected';
        }
    }
    
    getStatusColor(status) {
        const colors = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        };
        return colors[status] || 'secondary';
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}

// Initialize dashboard manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboardManager = new DashboardManager();
});

// Add CSS for animations and styling
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    .activity-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    
    .activity-indicator.active {
        background-color: rgba(25, 135, 84, 0.1);
        color: #198754;
    }
    
    .activity-indicator.inactive {
        background-color: rgba(220, 53, 69, 0.1);
        color: #dc3545;
    }
    
    .chat-message {
        margin-bottom: 1rem;
        padding: 0.75rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
    }
    
    .chat-message.own-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    
    .notification-item {
        transition: background-color 0.2s ease;
    }
    
    .notification-item:hover {
        background-color: #f8f9fa;
    }
    
    .notification-item.unread {
        background-color: rgba(13, 110, 253, 0.05);
        border-left: 3px solid #0d6efd;
    }
    
    .notification-unread-indicator {
        width: 8px;
        height: 8px;
        background-color: #0d6efd;
        border-radius: 50%;
        margin-left: auto;
    }
    
    .stat-card {
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
    }
    
    .stat-card.pending {
        background-color: rgba(255, 193, 7, 0.1);
        border: 1px solid rgba(255, 193, 7, 0.3);
    }
    
    .stat-card.in-progress {
        background-color: rgba(13, 202, 240, 0.1);
        border: 1px solid rgba(13, 202, 240, 0.3);
    }
    
    .stat-card.completed {
        background-color: rgba(25, 135, 84, 0.1);
        border: 1px solid rgba(25, 135, 84, 0.3);
    }
    
    .stat-card.overdue {
        background-color: rgba(220, 53, 69, 0.1);
        border: 1px solid rgba(220, 53, 69, 0.3);
    }
    
    .connection-status {
        font-size: 0.875rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
    }
    
    .connection-status.connected {
        background-color: rgba(25, 135, 84, 0.1);
        color: #198754;
    }
    
    .connection-status.disconnected {
        background-color: rgba(220, 53, 69, 0.1);
        color: #dc3545;
    }
    
    .typing-indicator {
        padding: 0.5rem;
        font-style: italic;
        color: #6c757d;
    }
    
    .typing-indicator i {
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    .mention {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.125rem 0.25rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    
    .file-message {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.25rem;
    }
    
    .image-message img {
        border-radius: 0.25rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .toast-container {
        z-index: 1055;
    }
    
    .toast {
        min-width: 300px;
    }
    
    .toast-success {
        background-color: #d1e7dd;
        border-color: #badbcc;
    }
    
    .toast-error {
        background-color: #f8d7da;
        border-color: #f5c2c7;
    }
    
    .toast-warning {
        background-color: #fff3cd;
        border-color: #ffecb5;
    }
    
    .toast-info {
        background-color: #cff4fc;
        border-color: #b6effb;
    }
`;
document.head.appendChild(style); 