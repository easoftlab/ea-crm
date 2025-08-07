// Chat functionality for Production Dashboard
class ChatManager {
    constructor() {
        this.socket = null;
        this.currentRoom = 'general';
        this.typingTimeout = null;
        this.isTyping = false;
        this.lastMessageId = 0;
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.loadInitialMessages();
    }
    
    initializeSocket() {
        // Connect to SocketIO server
        this.socket = io();
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to chat server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from chat server');
            this.updateConnectionStatus(false);
        });
        
        // Message events
        this.socket.on('new_message', (message) => {
            this.addMessage(message);
            this.playMessageSound();
            this.showToast(`New message from ${message.sender_name}`, 'info');
        });
        
        // Typing events
        this.socket.on('user_typing_start', (data) => {
            this.showTypingIndicator(data.user);
        });
        
        this.socket.on('user_typing_stop', (data) => {
            this.hideTypingIndicator(data.user);
        });
        
        // User online/offline events
        this.socket.on('user_online', (data) => {
            this.updateOnlineUsers();
            this.showToast(`${data.full_name} is now online`, 'success');
        });
        
        this.socket.on('user_offline', (data) => {
            this.updateOnlineUsers();
            this.showToast(`${data.username} went offline`, 'warning');
        });
        
        // Error handling
        this.socket.on('error', (data) => {
            console.error('Socket error:', data);
            this.showToast(data.message || 'Connection error', 'error');
        });
    }
    
    initializeEventListeners() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-message-btn');
        const attachButton = document.getElementById('attach-file-btn');
        const fileInput = document.getElementById('file-input');
        
        if (messageInput) {
            // Send message on Enter key
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Typing indicators
            messageInput.addEventListener('input', () => {
                this.handleTyping();
            });
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });
        }
        
        if (attachButton && fileInput) {
            attachButton.addEventListener('click', () => {
                fileInput.click();
            });
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.uploadFile(e.target.files[0]);
                }
            });
        }
    }
    
    sendMessage() {
        const messageInput = document.getElementById('message-input');
        const content = messageInput.value.trim();
        
        if (!content) return;
        
        // Send message via SocketIO
        this.socket.emit('send_message', {
            content: content,
            room: this.currentRoom
        });
        
        // Clear input
        messageInput.value = '';
        
        // Stop typing indicator
        this.stopTyping();
    }
    
    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('room', this.currentRoom);
        
        fetch('/production/api/chat/upload', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // The file upload will create a message that will be received via SocketIO
                this.showToast('File uploaded successfully', 'success');
            } else {
                this.showToast(data.error || 'Upload failed', 'error');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            this.showToast('Upload failed', 'error');
        });
    }
    
    addMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${message.sender_id == this.getCurrentUserId() ? 'own-message' : ''}`;
        
        const isOwnMessage = message.sender_id == this.getCurrentUserId();
        const messageClass = isOwnMessage ? 'own-message' : '';
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <strong>${message.sender_name}</strong>
                <small class="text-muted">${this.formatTime(message.created_at)}</small>
            </div>
            <div class="message-content">
                ${this.formatMessageContent(message)}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update last message ID for polling fallback
        this.lastMessageId = Math.max(this.lastMessageId, message.id);
    }
    
    formatMessageContent(message) {
        if (message.message_type === 'file') {
            return `
                <div class="file-message">
                    <i class="fas fa-file"></i>
                    <a href="${message.file_url}" target="_blank">${message.file_name}</a>
                    <small>(${this.formatFileSize(message.file_size)})</small>
                </div>
            `;
        } else if (message.message_type === 'image') {
            return `
                <div class="image-message">
                    <img src="${message.file_url}" alt="${message.file_name}" class="img-fluid" style="max-width: 200px;">
                </div>
            `;
        } else {
            // Highlight mentions
            let content = message.content;
            if (message.mentions && message.mentions.length > 0) {
                message.mentions.forEach(mention => {
                    const regex = new RegExp(`@${mention}`, 'g');
                    content = content.replace(regex, `<span class="mention">@${mention}</span>`);
                });
            }
            return content;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.socket.emit('typing_start', { room: this.currentRoom });
        }
        
        // Clear existing timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
        
        // Set new timeout
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 1000);
    }
    
    stopTyping() {
        if (this.isTyping) {
            this.isTyping = false;
            this.socket.emit('typing_stop', { room: this.currentRoom });
        }
        
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
            this.typingTimeout = null;
        }
    }
    
    showTypingIndicator(username) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        // Remove existing typing indicator for this user
        const existingIndicator = chatMessages.querySelector(`[data-typing-user="${username}"]`);
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Add new typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.setAttribute('data-typing-user', username);
        typingDiv.innerHTML = `
            <small class="text-muted">
                <i class="fas fa-circle"></i> ${username} is typing...
            </small>
        `;
        
        chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator(username) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const typingIndicator = chatMessages.querySelector(`[data-typing-user="${username}"]`);
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    updateOnlineUsers() {
        this.socket.emit('request_online_users');
    }
    
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    playMessageSound() {
        const messageSound = document.getElementById('message-sound');
        if (messageSound) {
            messageSound.play().catch(e => console.log('Could not play sound:', e));
        }
    }
    
    showToast(message, type = 'info') {
        if (window.notificationManager) {
            window.notificationManager.showToast(message, type);
        } else {
            // Fallback toast implementation
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
    
    loadInitialMessages() {
        // Load initial messages via AJAX (fallback)
        fetch(`/production/api/chat/messages?room=${this.currentRoom}`)
        .then(response => response.json())
        .then(data => {
            data.messages.forEach(message => {
                this.addMessage(message);
            });
        })
        .catch(error => {
            console.error('Error loading initial messages:', error);
        });
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    getCurrentUserId() {
        return parseInt(document.querySelector('meta[name="user-id"]')?.getAttribute('content') || '0');
    }
}

// Initialize chat manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('chat-messages')) {
        window.chatManager = new ChatManager();
    }
}); 