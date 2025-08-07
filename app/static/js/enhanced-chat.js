// Enhanced Chat System with Mentions, Presence, and Offline Support
class EnhancedChatManager {
    constructor() {
        this.socket = null;
        this.currentRoom = 'general';
        this.typingTimeout = null;
        this.isTyping = false;
        this.lastMessageId = 0;
        this.offlineQueue = [];
        this.isOnline = navigator.onLine;
        this.mentionUsers = [];
        this.onlineUsers = new Map();
        this.typingUsers = new Set();
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.initializeOfflineSupport();
        this.loadInitialMessages();
        this.loadOnlineUsers();
        this.initializeMentionSystem();
    }
    
    initializeSocket() {
        // Connect to SocketIO server
        this.socket = io({
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to chat server');
            this.isOnline = true;
            this.updateConnectionStatus(true);
            this.syncOfflineData();
            this.showToast('🟢 Connected to server', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from chat server');
            this.isOnline = false;
            this.updateConnectionStatus(false);
            this.showToast('🔴 Disconnected from server', 'warning');
        });
        
        this.socket.on('reconnect', () => {
            console.log('Reconnected to chat server');
            this.isOnline = true;
            this.updateConnectionStatus(true);
            this.syncOfflineData();
            this.showToast('🟢 Reconnected to server', 'success');
        });
        
        // Message events
        this.socket.on('new_message', (message) => {
            this.addMessage(message);
            this.playMessageSound();
            this.showDesktopNotification(message);
            this.showToast(`💬 New message from ${message.sender_name}`, 'info');
        });
        
        // Typing events
        this.socket.on('user_typing_start', (data) => {
            this.showTypingIndicator(data.user);
            this.typingUsers.add(data.user);
            this.updateTypingUsers();
        });
        
        this.socket.on('user_typing_stop', (data) => {
            this.hideTypingIndicator(data.user);
            this.typingUsers.delete(data.user);
            this.updateTypingUsers();
        });
        
        // User online/offline events
        this.socket.on('user_online', (data) => {
            this.onlineUsers.set(data.user_id, data);
            this.updateOnlineUsers();
            this.showToast(`🟢 ${data.full_name} is now online`, 'success');
            this.showDesktopNotification({
                title: 'User Online',
                body: `${data.full_name} is now online`,
                type: 'presence'
            });
        });
        
        this.socket.on('user_offline', (data) => {
            this.onlineUsers.delete(data.user_id);
            this.updateOnlineUsers();
            this.showToast(`🔴 ${data.username} went offline`, 'warning');
        });
        
        // Mention events
        this.socket.on('user_mentioned', (data) => {
            this.playMentionSound();
            this.showMentionNotification(data);
            this.showToast(`@${data.mentioned_by} mentioned you!`, 'warning');
        });
        
        // Read receipt events
        this.socket.on('message_read', (data) => {
            this.updateMessageReadStatus(data.message_id, data.read_by);
        });
        
        // Error handling
        this.socket.on('error', (data) => {
            console.error('Socket error:', data);
            this.showToast(data.message || 'Connection error', 'error');
        });
    }
    
    initializeEventListeners() {
        // Try both possible message input IDs
        const messageInput = document.getElementById('message-input') || document.getElementById('messenger-input');
        const sendButton = document.getElementById('send-message-btn');
        const attachButton = document.getElementById('attach-file-btn');
        const fileInput = document.getElementById('file-input');
        const mentionDropdown = document.getElementById('mention-dropdown');
        
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
                this.handleMentionInput();
            });
            
            // Mention dropdown navigation
            messageInput.addEventListener('keydown', (e) => {
                this.handleMentionNavigation(e);
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
        
        // Online/offline detection
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateConnectionStatus(true);
            this.syncOfflineData();
            this.showToast('🟢 Internet connection restored', 'success');
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateConnectionStatus(false);
            this.showToast('🔴 Internet connection lost', 'warning');
        });
    }
    
    initializeOfflineSupport() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then((registration) => {
                    console.log('Service Worker registered:', registration);
                    this.serviceWorker = registration;
                })
                .catch((error) => {
                    console.error('Service Worker registration failed:', error);
                });
        }
        
        // Initialize IndexedDB for offline storage
        this.initializeOfflineStorage();
    }
    
    initializeOfflineStorage() {
        const request = indexedDB.open('EA_CRM_Chat', 1);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            // Messages store
            if (!db.objectStoreNames.contains('messages')) {
                const messageStore = db.createObjectStore('messages', { keyPath: 'id', autoIncrement: true });
                messageStore.createIndex('room', 'room', { unique: false });
                messageStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
            
            // Offline messages store
            if (!db.objectStoreNames.contains('offline_messages')) {
                const offlineStore = db.createObjectStore('offline_messages', { keyPath: 'id', autoIncrement: true });
                offlineStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
            
            // User presence store
            if (!db.objectStoreNames.contains('user_presence')) {
                const presenceStore = db.createObjectStore('user_presence', { keyPath: 'user_id' });
                presenceStore.createIndex('is_online', 'is_online', { unique: false });
            }
        };
        
        request.onsuccess = (event) => {
            this.db = event.target.result;
            console.log('Offline storage initialized');
        };
    }
    
    initializeMentionSystem() {
        // Load users for mention suggestions
        this.loadMentionUsers();
        
        // Create mention dropdown
        this.createMentionDropdown();
    }
    
    loadMentionUsers() {
        fetch('/production/api/users/list')
            .then(response => response.json())
            .then(data => {
                this.mentionUsers = data.users || [];
                this.updateMentionDropdown();
            })
            .catch(error => {
                console.error('Error loading users for mentions:', error);
                // Fallback to mock users for testing
                this.mentionUsers = [
                    { id: 1, username: 'admin', full_name: 'Administrator', profile_image: '/static/images/default-avatar.png' },
                    { id: 2, username: 'john', full_name: 'John Doe', profile_image: '/static/images/default-avatar.png' },
                    { id: 3, username: 'jane', full_name: 'Jane Smith', profile_image: '/static/images/default-avatar.png' },
                    { id: 4, username: 'bob', full_name: 'Bob Johnson', profile_image: '/static/images/default-avatar.png' }
                ];
                this.updateMentionDropdown();
                console.log('Using fallback mock users for mentions');
            });
    }
    
    createMentionDropdown() {
        const messageInput = document.getElementById('message-input');
        if (!messageInput) return;
        
        // Create dropdown container
        const dropdown = document.createElement('div');
        dropdown.id = 'mention-dropdown';
        dropdown.className = 'mention-dropdown';
        dropdown.style.display = 'none';
        
        messageInput.parentNode.appendChild(dropdown);
    }
    
    updateMentionDropdown() {
        const dropdown = document.getElementById('mention-dropdown');
        if (!dropdown) return;
        
        dropdown.innerHTML = '';
        
        this.mentionUsers.forEach(user => {
            const item = document.createElement('div');
            item.className = 'mention-item';
            item.innerHTML = `
                <img src="${user.profile_image || '/static/images/default-avatar.png'}" alt="${user.full_name}" class="mention-avatar">
                <span class="mention-name">${user.full_name}</span>
                <span class="mention-username">@${user.username}</span>
            `;
            item.addEventListener('click', () => {
                this.insertMention(user.username);
            });
            dropdown.appendChild(item);
        });
    }
    
    handleMentionInput() {
        const messageInput = document.getElementById('message-input');
        const dropdown = document.getElementById('mention-dropdown');
        if (!messageInput || !dropdown) {
            console.log('Message input or dropdown not found');
            return;
        }
        
        const cursorPos = messageInput.selectionStart;
        const text = messageInput.value;
        const beforeCursor = text.substring(0, cursorPos);
        
        // Check if we're typing a mention
        const mentionMatch = beforeCursor.match(/@(\w*)$/);
        
        console.log('Mention input check:', {
            text: text,
            beforeCursor: beforeCursor,
            mentionMatch: mentionMatch,
            mentionUsers: this.mentionUsers.length
        });
        
        if (mentionMatch) {
            const query = mentionMatch[1].toLowerCase();
            const filteredUsers = this.mentionUsers.filter(user => 
                user.username.toLowerCase().includes(query) ||
                user.full_name.toLowerCase().includes(query)
            );
            
            console.log('Filtered users:', filteredUsers);
            
            if (filteredUsers.length > 0) {
                this.showMentionDropdown(filteredUsers);
            } else {
                dropdown.style.display = 'none';
            }
        } else {
            dropdown.style.display = 'none';
        }
    }
    
    showMentionDropdown(users) {
        const dropdown = document.getElementById('mention-dropdown');
        if (!dropdown) {
            console.log('Mention dropdown not found');
            return;
        }
        
        console.log('Showing mention dropdown with users:', users);
        
        dropdown.innerHTML = '';
        dropdown.style.display = 'block';
        
        users.forEach(user => {
            const item = document.createElement('div');
            item.className = 'mention-item';
            item.innerHTML = `
                <img src="${user.profile_image || '/static/images/default-avatar.png'}" alt="${user.full_name}" class="mention-avatar">
                <span class="mention-name">${user.full_name}</span>
                <span class="mention-username">@${user.username}</span>
            `;
            item.addEventListener('click', () => {
                this.insertMention(user.username);
            });
            dropdown.appendChild(item);
        });
        
        console.log('Mention dropdown displayed with', users.length, 'users');
    }
    
    insertMention(username) {
        const messageInput = document.getElementById('message-input');
        const dropdown = document.getElementById('mention-dropdown');
        if (!messageInput || !dropdown) return;
        
        const cursorPos = messageInput.selectionStart;
        const text = messageInput.value;
        const beforeCursor = text.substring(0, cursorPos);
        const afterCursor = text.substring(cursorPos);
        
        // Replace the @username with the full mention
        const newText = beforeCursor.replace(/@\w*$/, `@${username} `) + afterCursor;
        messageInput.value = newText;
        
        // Set cursor position after the mention
        const newCursorPos = beforeCursor.replace(/@\w*$/, `@${username} `).length;
        messageInput.setSelectionRange(newCursorPos, newCursorPos);
        messageInput.focus();
        
        dropdown.style.display = 'none';
    }
    
    handleMentionNavigation(event) {
        const dropdown = document.getElementById('mention-dropdown');
        if (!dropdown || dropdown.style.display === 'none') return;
        
        const items = dropdown.querySelectorAll('.mention-item');
        const activeItem = dropdown.querySelector('.mention-item.active');
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                if (!activeItem) {
                    items[0].classList.add('active');
                } else {
                    const nextItem = activeItem.nextElementSibling;
                    if (nextItem) {
                        activeItem.classList.remove('active');
                        nextItem.classList.add('active');
                    }
                }
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                if (activeItem) {
                    const prevItem = activeItem.previousElementSibling;
                    if (prevItem) {
                        activeItem.classList.remove('active');
                        prevItem.classList.add('active');
                    }
                }
                break;
                
            case 'Enter':
                event.preventDefault();
                if (activeItem) {
                    const username = activeItem.querySelector('.mention-username').textContent.substring(1);
                    this.insertMention(username);
                }
                break;
                
            case 'Escape':
                dropdown.style.display = 'none';
                break;
        }
    }
    
    sendMessage() {
        // Try both possible message input IDs
        const messageInput = document.getElementById('message-input') || document.getElementById('messenger-input');
        const content = messageInput.value.trim();
        
        if (!content) return;
        
        // Extract mentions from content
        const mentions = this.extractMentions(content);
        
        const messageData = {
            content: content,
            room: this.currentRoom,
            mentions: mentions
        };
        
        if (this.isOnline && this.socket && this.socket.connected) {
            // Send via SocketIO
            this.socket.emit('send_message', messageData);
        } else {
            // Queue for offline sync
            this.queueOfflineMessage(messageData);
        }
        
        // Clear input
        messageInput.value = '';
        
        // Stop typing indicator
        this.stopTyping();
    }
    
    extractMentions(content) {
        const mentionPattern = /@(\w+)/g;
        const mentions = [];
        let match;
        
        while ((match = mentionPattern.exec(content)) !== null) {
            mentions.push(match[1]);
        }
        
        return mentions;
    }
    
    queueOfflineMessage(messageData) {
        const offlineMessage = {
            ...messageData,
            timestamp: Date.now(),
            status: 'pending'
        };
        
        this.offlineQueue.push(offlineMessage);
        this.saveOfflineMessage(offlineMessage);
        
        // Show offline indicator
        this.showToast('📱 Message queued for sync when online', 'info');
        
        // Add to UI immediately
        this.addMessage({
            id: 'offline_' + Date.now(),
            sender_id: this.getCurrentUserId(),
            sender_name: this.getCurrentUserName(),
            content: messageData.content,
            created_at: new Date().toISOString(),
            status: 'pending'
        });
    }
    
    saveOfflineMessage(message) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['offline_messages'], 'readwrite');
        const store = transaction.objectStore('offline_messages');
        store.add(message);
    }
    
    syncOfflineData() {
        if (!this.db || this.offlineQueue.length === 0) return;
        
        console.log('Syncing offline messages...');
        
        const transaction = this.db.transaction(['offline_messages'], 'readwrite');
        const store = transaction.objectStore('offline_messages');
        const request = store.getAll();
        
        request.onsuccess = () => {
            const offlineMessages = request.result;
            
            offlineMessages.forEach(message => {
                if (this.socket && this.socket.connected) {
                    this.socket.emit('send_message', {
                        content: message.content,
                        room: message.room,
                        mentions: message.mentions
                    });
                    
                    // Remove from offline storage
                    store.delete(message.id);
                }
            });
            
            this.offlineQueue = [];
            this.showToast('🔄 Offline messages synced', 'success');
        };
    }
    
    addMessage(message) {
        // Try both possible message container IDs
        const chatMessages = document.getElementById('chat-messages') || document.getElementById('messenger-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${message.sender_id == this.getCurrentUserId() ? 'own-message' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        
        const isOwnMessage = message.sender_id == this.getCurrentUserId();
        const messageClass = isOwnMessage ? 'own-message' : '';
        const statusClass = message.status === 'pending' ? 'message-pending' : '';
        
        // Check if current user is mentioned in this message
        const currentUserId = this.getCurrentUserId();
        const currentUserName = this.getCurrentUserName();
        const isMentioned = this.isUserMentioned(message, currentUserId, currentUserName);
        const highlightClass = isMentioned ? 'message-highlighted' : '';
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <strong class="message-sender">${message.sender_name}</strong>
                <small class="text-muted">${this.formatTime(message.created_at)}</small>
                ${message.status === 'pending' ? '<span class="badge bg-warning">⏳ Pending</span>' : ''}
                ${isMentioned ? '<span class="mention-badge">@You</span>' : ''}
            </div>
            <div class="message-content ${statusClass}">
                ${this.formatMessageContent(message)}
                <div class="message-actions" style="display: none;">
                    <button class="message-action-btn" onclick="window.enhancedChatManager.replyMessage(${message.id})" title="Reply">
                        <i class="fas fa-reply"></i>
                    </button>
                    ${isOwnMessage ? `
                        <button class="message-action-btn" onclick="window.enhancedChatManager.editMessage(${message.id})" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="message-action-btn" onclick="window.enhancedChatManager.deleteMessage(${message.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                    <button class="message-action-btn" onclick="window.enhancedChatManager.copyMessage(${message.id})" title="Copy Text">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button class="message-action-btn" onclick="window.enhancedChatManager.forwardMessage(${message.id})" title="Forward">
                        <i class="fas fa-share"></i>
                    </button>
                    <button class="message-action-btn" onclick="window.enhancedChatManager.pinMessage(${message.id})" title="Pin">
                        <i class="fas fa-thumbtack"></i>
                    </button>
                </div>
            </div>
            <div class="message-footer">
                ${this.getReadReceipts(message)}
            </div>
        `;
        
        // Add highlighting class if mentioned
        if (isMentioned) {
            messageDiv.classList.add('message-highlighted');
        }
        
        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update last message ID for polling fallback
        this.lastMessageId = Math.max(this.lastMessageId, message.id);
        
        // Mark as read if not own message
        if (!isOwnMessage) {
            this.markMessageAsRead(message.id);
        }
        
        // Add message action event listeners
        this.addMessageActionListeners(messageDiv);
    }
    
    addMessageActionListeners(messageDiv) {
        const messageContent = messageDiv.querySelector('.message-content');
        const messageActions = messageDiv.querySelector('.message-actions');
        
        // Show actions on hover
        messageContent.addEventListener('mouseenter', () => {
            if (messageActions) {
                messageActions.style.display = 'flex';
            }
        });
        
        // Hide actions on mouse leave
        messageContent.addEventListener('mouseleave', () => {
            if (messageActions) {
                messageActions.style.display = 'none';
            }
        });
        
        // Right-click context menu
        messageContent.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showMessageContextMenu(e, messageDiv);
        });
    }
    
    showMessageContextMenu(event, messageDiv) {
        const messageId = messageDiv.getAttribute('data-message-id');
        const isOwnMessage = messageDiv.classList.contains('own-message');
        const messageContent = messageDiv.querySelector('.message-content').textContent;
        
        // Remove existing context menu
        const existingMenu = document.querySelector('.message-context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }
        
        // Create context menu
        const contextMenu = document.createElement('div');
        contextMenu.className = 'message-context-menu';
        contextMenu.style.cssText = `
            position: fixed;
            top: ${event.clientY}px;
            left: ${event.clientX}px;
            background: #2c2c2c;
            border-radius: 8px;
            padding: 8px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            min-width: 180px;
        `;
        
        const menuItems = [
            { icon: 'fas fa-reply', text: 'Reply', action: () => this.replyMessage(messageId) },
            { icon: 'fas fa-copy', text: 'Copy Text', action: () => this.copyMessage(messageId, messageContent) },
            { icon: 'fas fa-share', text: 'Forward', action: () => this.forwardMessage(messageId) },
            { icon: 'fas fa-thumbtack', text: 'Pin', action: () => this.pinMessage(messageId) }
        ];
        
        if (isOwnMessage) {
            menuItems.splice(1, 0, { icon: 'fas fa-edit', text: 'Edit', action: () => this.editMessage(messageId) });
            menuItems.push({ icon: 'fas fa-trash', text: 'Delete', action: () => this.deleteMessage(messageId) });
        }
        
        menuItems.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.style.cssText = `
                padding: 8px 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                color: white;
                font-size: 14px;
                transition: background-color 0.2s;
            `;
            menuItem.innerHTML = `<i class="${item.icon}"></i> ${item.text}`;
            menuItem.addEventListener('click', () => {
                item.action();
                contextMenu.remove();
            });
            menuItem.addEventListener('mouseenter', () => {
                menuItem.style.backgroundColor = '#404040';
            });
            menuItem.addEventListener('mouseleave', () => {
                menuItem.style.backgroundColor = 'transparent';
            });
            contextMenu.appendChild(menuItem);
        });
        
        document.body.appendChild(contextMenu);
        
        // Close menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                contextMenu.remove();
                document.removeEventListener('click', closeMenu);
            });
        }, 100);
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
    
    getReadReceipts(message) {
        if (message.read_by && message.read_by.length > 0) {
            const readBy = message.read_by.map(user => user.full_name).join(', ');
            return `<small class="text-muted">👁 Read by ${readBy}</small>`;
        }
        return '';
    }
    
    markMessageAsRead(messageId) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('mark_message_read', {
                message_id: messageId,
                room: this.currentRoom
            });
        }
    }
    
    updateMessageReadStatus(messageId, readBy) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageDiv) {
            const footer = messageDiv.querySelector('.message-footer');
            if (footer) {
                footer.innerHTML = `<small class="text-muted">👁 Read by ${readBy.full_name}</small>`;
            }
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
                <i class="fas fa-circle typing-dot"></i> ${username} is typing...
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
    
    updateTypingUsers() {
        const typingContainer = document.getElementById('typing-users');
        if (!typingContainer) return;
        
        if (this.typingUsers.size > 0) {
            const users = Array.from(this.typingUsers);
            typingContainer.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-circle typing-dot"></i> ${users.join(', ')} typing...
                </small>
            `;
            typingContainer.style.display = 'block';
        } else {
            typingContainer.style.display = 'none';
        }
    }
    
    updateOnlineUsers() {
        const onlineUsersContainer = document.getElementById('online-users');
        if (!onlineUsersContainer) return;
        
        const users = Array.from(this.onlineUsers.values());
        
        if (users.length > 0) {
            onlineUsersContainer.innerHTML = users.map(user => `
                <div class="online-user">
                    <img src="${user.profile_image || '/static/images/default-avatar.png'}" alt="${user.full_name}" class="user-avatar">
                    <span class="user-name">${user.full_name}</span>
                    <span class="online-indicator">🟢</span>
                </div>
            `).join('');
        } else {
            onlineUsersContainer.innerHTML = '<p class="text-muted">No users online</p>';
        }
    }
    
    showDesktopNotification(message) {
        if (window.notificationManager) {
            window.notificationManager.notifyNewMessage(message.sender_name, message.content);
        }
    }
    
    showMentionNotification(data) {
        if (window.notificationManager) {
            window.notificationManager.notifyMention(data.mentioned_by, data.message_content);
        }
    }
    
    playMessageSound() {
        if (window.notificationManager) {
            window.notificationManager.playSound('message');
        }
    }
    
    playMentionSound() {
        if (window.notificationManager) {
            window.notificationManager.playSound('mention');
        }
    }
    
    // ... existing methods from chat.js ...
    
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
            if (this.socket && this.socket.connected) {
                this.socket.emit('typing_start', { room: this.currentRoom });
            }
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
            if (this.socket && this.socket.connected) {
                this.socket.emit('typing_stop', { room: this.currentRoom });
            }
        }
        
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
            this.typingTimeout = null;
        }
    }
    
    scrollToBottom() {
        // Try both possible message container IDs
        const chatMessages = document.getElementById('chat-messages') || document.getElementById('messenger-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
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
    
    loadOnlineUsers() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('request_online_users');
        }
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    getCurrentUserId() {
        return parseInt(document.querySelector('meta[name="user-id"]')?.getAttribute('content') || '0');
    }
    
    getCurrentUserName() {
        const userElement = document.querySelector('meta[name="user-name"]');
        return userElement ? userElement.getAttribute('content') : 'Unknown User';
    }
    
    isUserMentioned(message, currentUserId, currentUserName) {
        // Check if user is mentioned in the message content
        if (message.content && currentUserName) {
            const mentionPattern = new RegExp(`@${currentUserName}`, 'i');
            if (mentionPattern.test(message.content)) {
                return true;
            }
        }
        
        // Check if user ID is in the mentions array
        if (message.mentions && Array.isArray(message.mentions)) {
            // Check by user ID
            if (message.mentions.includes(currentUserId)) {
                return true;
            }
            
            // Check by username
            if (message.mentions.includes(currentUserName)) {
                return true;
            }
        }
        
        // Check if message has a mentions field with user data
        if (message.mentions && Array.isArray(message.mentions)) {
            return message.mentions.some(mention => {
                if (typeof mention === 'object') {
                    return mention.id == currentUserId || mention.username === currentUserName;
                }
                return mention == currentUserId || mention === currentUserName;
            });
        }
        
        return false;
    }
    
    // Message Action Functions
    replyMessage(messageId) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        const messageContent = messageDiv.querySelector('.message-content').textContent;
        const messageInput = document.getElementById('message-input') || document.getElementById('messenger-input');
        
        if (messageInput) {
            messageInput.value = `> ${messageContent}\n\n`;
            messageInput.focus();
            this.showToast('💬 Reply mode activated', 'info');
        }
    }
    
    editMessage(messageId) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        const messageContent = messageDiv.querySelector('.message-content');
        const originalText = messageContent.textContent;
        
        // Create edit input
        const editInput = document.createElement('textarea');
        editInput.value = originalText;
        editInput.style.cssText = `
            width: 100%;
            min-height: 60px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            resize: vertical;
        `;
        
        // Create edit buttons
        const editButtons = document.createElement('div');
        editButtons.style.cssText = `
            display: flex;
            gap: 8px;
            margin-top: 8px;
        `;
        
        const saveBtn = document.createElement('button');
        saveBtn.textContent = 'Save';
        saveBtn.className = 'btn btn-sm btn-primary';
        saveBtn.onclick = () => this.saveMessageEdit(messageId, editInput.value);
        
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.className = 'btn btn-sm btn-secondary';
        cancelBtn.onclick = () => this.cancelMessageEdit(messageId, originalText);
        
        editButtons.appendChild(saveBtn);
        editButtons.appendChild(cancelBtn);
        
        // Replace content with edit form
        messageContent.innerHTML = '';
        messageContent.appendChild(editInput);
        messageContent.appendChild(editButtons);
        
        editInput.focus();
        editInput.select();
    }
    
    saveMessageEdit(messageId, newContent) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('edit_message', {
                message_id: messageId,
                content: newContent,
                room: this.currentRoom
            });
        } else {
            // Fallback to AJAX
            fetch('/production/api/chat/edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    message_id: messageId,
                    content: newContent,
                    room: this.currentRoom
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showToast('✅ Message edited successfully', 'success');
                } else {
                    this.showToast('❌ Failed to edit message', 'error');
                }
            })
            .catch(error => {
                console.error('Error editing message:', error);
                this.showToast('❌ Error editing message', 'error');
            });
        }
    }
    
    cancelMessageEdit(messageId, originalText) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        const messageContent = messageDiv.querySelector('.message-content');
        messageContent.innerHTML = originalText;
    }
    
    deleteMessage(messageId) {
        if (confirm('Are you sure you want to delete this message?')) {
            if (this.socket && this.socket.connected) {
                this.socket.emit('delete_message', {
                    message_id: messageId,
                    room: this.currentRoom
                });
            } else {
                // Fallback to AJAX
                fetch('/production/api/chat/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({
                        message_id: messageId,
                        room: this.currentRoom
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
                        if (messageDiv) {
                            messageDiv.remove();
                        }
                        this.showToast('✅ Message deleted successfully', 'success');
                    } else {
                        this.showToast('❌ Failed to delete message', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error deleting message:', error);
                    this.showToast('❌ Error deleting message', 'error');
                });
            }
        }
    }
    
    copyMessage(messageId) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        const messageContent = messageDiv.querySelector('.message-content').textContent.trim();
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(messageContent).then(() => {
                this.showToast('📋 Message copied to clipboard', 'success');
            }).catch(() => {
                this.fallbackCopyTextToClipboard(messageContent);
            });
        } else {
            this.fallbackCopyTextToClipboard(messageContent);
        }
    }
    
    fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showToast('📋 Message copied to clipboard', 'success');
        } catch (err) {
            this.showToast('❌ Failed to copy message', 'error');
        }
        
        document.body.removeChild(textArea);
    }
    
    forwardMessage(messageId) {
        // For now, just copy the message content
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        const messageContent = messageDiv.querySelector('.message-content').textContent;
        this.copyMessage(messageId);
        this.showToast('📤 Forward functionality coming soon', 'info');
    }
    
    pinMessage(messageId) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('pin_message', {
                message_id: messageId,
                room: this.currentRoom
            });
        } else {
            // Fallback to AJAX
            fetch('/production/api/chat/pin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    message_id: messageId,
                    room: this.currentRoom
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showToast('📌 Message pinned successfully', 'success');
                } else {
                    this.showToast('❌ Failed to pin message', 'error');
                }
            })
            .catch(error => {
                console.error('Error pinning message:', error);
                this.showToast('❌ Error pinning message', 'error');
            });
        }
    }
}

// Initialize enhanced chat manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with chat messages (either floating or full messenger)
    if (document.getElementById('chat-messages') || document.getElementById('messenger-messages')) {
        window.enhancedChatManager = new EnhancedChatManager();
    }
});