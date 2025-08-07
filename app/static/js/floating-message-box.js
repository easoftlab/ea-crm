class FloatingMessageBox {
    constructor() {
        this.socket = null;
        this.messagesContainer = document.getElementById('message-box-messages');
        this.messageInput = document.getElementById('message-box-input');
        this.floatingIcon = document.getElementById('floating-message-icon');
        this.modal = document.getElementById('message-box-modal');
        this.currentRoom = 'general';
        this.typingTimeout = null;
        this.isTyping = false;
        this.lastMessageId = 0;
        this.mentionUsers = [];
        
        this.initializeSocket();
        this.initializeEventListeners();
        this.loadInitialMessages();
        this.initializeMentionSystem();
        this.initializeMediaHandling();
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Floating message box connected to SocketIO');
            this.socket.emit('join_room', { room: this.currentRoom });
        });
        
        this.socket.on('disconnect', () => {
            console.log('Floating message box disconnected from SocketIO');
        });
        
        this.socket.on('new_message', (message) => {
            this.addMessageToUI(message);
            this.showNotificationBadge();
            
            // Use new notification manager
            const currentUserId = this.getCurrentUserId();
            if (message.sender_id != currentUserId && window.notificationManager) {
                window.notificationManager.notifyNewMessage(message.sender_name, message.content);
            } else {
                this.playNotificationSound();
            }
        });
        
        this.socket.on('user_typing_start', (data) => {
            this.showTypingIndicator(data.user);
        });
        
        this.socket.on('user_typing_stop', (data) => {
            this.hideTypingIndicator(data.user);
        });
        
        this.socket.on('error', (data) => {
            console.error('SocketIO error:', data);
        });
        
        // Listen for mention notifications
        this.socket.on('user_mentioned', (data) => {
            if (window.notificationManager) {
                window.notificationManager.notifyMention(data.mentioned_by, data.message_content);
            }
        });
        
        // Listen for task update notifications
        this.socket.on('task_updated', (data) => {
            if (window.notificationManager) {
                window.notificationManager.notifyTaskUpdate(data.task_title, data.update_type);
            }
        });
        
        // Edit and Delete event listeners
        this.socket.on('message_edited', (data) => {
            const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
            if (messageElement) {
                const contentText = messageElement.querySelector('.message-content-text');
                const editedIndicator = messageElement.querySelector('.message-edited-indicator');
                
                // Update content
                contentText.textContent = data.content;
                
                // Add or update edited indicator
                if (!editedIndicator) {
                    const indicator = document.createElement('div');
                    indicator.className = 'message-edited-indicator';
                    indicator.style.cssText = 'font-size: 11px; color: #999; font-style: italic; margin-top: 4px;';
                    indicator.textContent = '(edited)';
                    contentText.parentElement.appendChild(indicator);
                }
            }
        });
        
        this.socket.on('message_deleted', (data) => {
            const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
            if (messageElement) {
                const contentText = messageElement.querySelector('.message-content-text');
                const messageActions = messageElement.querySelector('.message-actions');
                
                // Update content to show deleted message
                contentText.textContent = '[Message deleted]';
                contentText.style.color = '#999';
                contentText.style.fontStyle = 'italic';
                
                // Remove action buttons
                if (messageActions) {
                    messageActions.remove();
                }
                
                // Add deletion info
                const deletionInfo = document.createElement('div');
                deletionInfo.style.cssText = 'font-size: 11px; color: #999; margin-top: 4px;';
                deletionInfo.textContent = `Deleted by ${data.deleted_by}`;
                contentText.parentElement.appendChild(deletionInfo);
            }
        });
        
        // Threaded Replies event listeners
        this.socket.on('thread_reply_sent', (data) => {
            this.addThreadReplyToUI(data);
        });
        
        this.socket.on('thread_replies_loaded', (data) => {
            this.displayThreadReplies(data);
        });
        
        // Pin Messages event listeners
        this.socket.on('message_pin_status_changed', (data) => {
            this.updateMessagePinStatus(data);
        });
        
        this.socket.on('pinned_messages_loaded', (data) => {
            this.displayPinnedMessages(data);
        });
    }
    
    initializeEventListeners() {
        // Send message on Enter key
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Typing indicators
            this.messageInput.addEventListener('input', () => {
                this.handleTyping();
                this.handleMentionInput();
            });
            
            // Mention dropdown navigation (with higher priority for Enter key)
            this.messageInput.addEventListener('keydown', (e) => {
                const dropdown = document.getElementById('mention-dropdown');
                const isDropdownVisible = dropdown && dropdown.style.display === 'block';
                
                if (e.key === 'Enter' && !e.shiftKey) {
                    // If dropdown is visible, let the navigation handler deal with it
                    if (isDropdownVisible) {
                        this.handleMentionNavigation(e);
                    } else {
                        // Check if we're typing a mention but dropdown is not visible
                        const cursorPos = this.messageInput.selectionStart;
                        const text = this.messageInput.value;
                        const beforeCursor = text.substring(0, cursorPos);
                        const mentionMatch = beforeCursor.match(/@([a-zA-Z0-9_]+)$/);
                        
                        if (mentionMatch) {
                            // Try to find a matching user and insert it
                            const query = mentionMatch[1].toLowerCase();
                            const matchingUser = this.mentionUsers.find(user => 
                                user.username.toLowerCase().includes(query) ||
                                user.full_name.toLowerCase().includes(query)
                            );
                            
                            if (matchingUser) {
                                e.preventDefault();
                                this.insertMention(matchingUser.username);
                                return;
                            }
                        }
                        
                        // If no dropdown and no mention match, send message normally
                        e.preventDefault();
                        this.sendMessage();
                    }
                } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Escape') {
                    // Handle other navigation keys only if dropdown is visible
                    if (isDropdownVisible) {
                        this.handleMentionNavigation(e);
                    }
                }
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('mention-dropdown');
            const messageInput = document.getElementById('message-box-input');
            
            if (dropdown && dropdown.style.display === 'block') {
                // Check if click is outside dropdown and input
                if (!dropdown.contains(e.target) && e.target !== messageInput) {
                    dropdown.style.display = 'none';
                }
            }
        });
        
        // Auto-scroll to bottom when modal opens
        const floatingIcon = document.getElementById('floating-message-icon');
        if (floatingIcon) {
            floatingIcon.addEventListener('click', () => {
                // Auto-scroll after modal opens
                setTimeout(() => {
                    this.scrollToBottom();
                }, 200);
            });
        }
        
        // Maximize button to open full messenger
        const maximizeButton = document.getElementById('message-box-maximize');
        if (maximizeButton) {
            maximizeButton.addEventListener('click', () => {
                // Navigate to full messenger page
                window.location.href = '/production/messenger';
            });
        }
    }
    
    loadInitialMessages() {
        fetch(`/production/api/chat/messages?room=${this.currentRoom}`)
            .then(response => response.json())
            .then(data => {
                if (data.messages) {
                    data.messages.forEach(message => {
                        this.addMessageToUI(message);
                    });
                    this.scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Error loading messages:', error);
            });
    }
    
    sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content) return;
        
        if (this.socket && this.socket.connected) {
            this.socket.emit('send_message', { 
                content: content, 
                room: this.currentRoom 
            });
        } else {
            // Fallback to AJAX
            fetch('/production/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    content: content,
                    room: this.currentRoom
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.addMessageToUI(data.message);
                    this.scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Error sending message:', error);
            });
        }
        
        this.messageInput.value = '';
        this.stopTyping();
    }
    
    addMessageToUI(message) {
        if (!this.messagesContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message-item';
        messageElement.style.cssText = `
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        `;
        
        const isCurrentUser = message.sender_id == document.querySelector('meta[name="user-id"]').getAttribute('content');
        
        // Check if current user is mentioned in this message
        const currentUserId = this.getCurrentUserId();
        const currentUserName = this.getCurrentUserName();
        const isMentioned = this.isUserMentioned(message, currentUserId, currentUserName);
        
        // Add highlighting class if mentioned
        if (isMentioned) {
            messageElement.classList.add('message-highlighted');
        }
        
        messageElement.innerHTML = `
            <div class="message-avatar" style="
                width: 35px;
                height: 35px;
                border-radius: 50%;
                background: ${isCurrentUser ? '#667eea' : '#e9ecef'};
                display: flex;
                align-items: center;
                justify-content: center;
                color: ${isCurrentUser ? 'white' : '#666'};
                font-weight: bold;
                font-size: 14px;
                flex-shrink: 0;
            ">${message.sender_name ? message.sender_name.charAt(0).toUpperCase() : 'U'}</div>
            <div class="message-content" style="flex: 1;">
                <div class="message-header" style="
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 4px;
                ">
                    <span class="message-sender" style="
                        font-weight: 600;
                        font-size: 13px;
                        color: #333;
                    ">${message.sender_name || 'Unknown'}</span>
                    <span class="message-time" style="
                        font-size: 11px;
                        color: #999;
                    ">${this.formatTime(message.created_at)}</span>
                    ${isMentioned ? '<span class="mention-badge">@You</span>' : ''}
                </div>
                <div class="message-text" style="
                    background: ${isCurrentUser ? '#667eea' : 'white'};
                    color: ${isCurrentUser ? 'white' : '#333'};
                    padding: 8px 12px;
                    border-radius: 15px;
                    font-size: 14px;
                    line-height: 1.4;
                    max-width: 80%;
                    word-wrap: break-word;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    position: relative;
                ">
                    <div class="message-content-text">${this.escapeHtml(message.content)}</div>
                    ${message.is_edited ? '<div class="message-edited-indicator" style="font-size: 11px; color: #999; font-style: italic; margin-top: 4px;">(edited)</div>' : ''}
                    ${message.message_type === 'file' ? this.createMediaAttachment(message) : ''}
                    
                    <!-- Message Actions Menu -->
                    <div class="message-actions" style="
                        position: absolute;
                        top: -8px;
                        right: -8px;
                        background: white;
                        border: 1px solid #e9ecef;
                        border-radius: 20px;
                        padding: 4px;
                        display: none;
                        gap: 4px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    ">
                        <button class="message-action-btn task-button" title="Convert to Task" onclick="window.floatingMessageBox.showConvertToTaskModal(${message.id}, '${this.escapeHtml(message.content)}')">
                            <i class="fas fa-tasks"></i>
                        </button>
                        <button class="message-action-btn reminder-button" title="Set Reminder" onclick="window.floatingMessageBox.showSetReminderModal(${message.id}, '${this.escapeHtml(message.content)}')">
                            <i class="fas fa-bell"></i>
                        </button>
                        <button class="message-action-btn thread-button" title="Reply in thread" onclick="window.floatingMessageBox.showThreadReplies(${message.id})">
                            <i class="fas fa-reply"></i>
                        </button>
                        <button class="message-action-btn pin-button" title="Pin message" onclick="window.floatingMessageBox.pinMessage(${message.id})">
                            <i class="fas fa-thumbtack"></i>
                        </button>
                        ${isCurrentUser ? `
                            <button class="message-action-btn" title="Edit message" onclick="window.floatingMessageBox.editMessage(${message.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="message-action-btn" title="Delete message" onclick="window.floatingMessageBox.deleteMessage(${message.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageElement);
        
        // Add event listeners for message actions
        const messageText = messageElement.querySelector('.message-text');
        const messageActions = messageElement.querySelector('.message-actions');
        
        if (messageText && messageActions) {
            // Show message actions on hover
            messageText.addEventListener('mouseenter', () => {
                messageActions.style.display = 'flex';
            });
            
            messageText.addEventListener('mouseleave', () => {
                messageActions.style.display = 'none';
            });
        }
        
        this.scrollToBottom();
    }
    
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            if (this.socket && this.socket.connected) {
                this.socket.emit('typing_start', { room: this.currentRoom });
            }
        }
        
        clearTimeout(this.typingTimeout);
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
        clearTimeout(this.typingTimeout);
    }
    
    showTypingIndicator(username) {
        // Remove existing typing indicator
        const existingIndicator = this.messagesContainer.querySelector('.typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.style.cssText = `
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-style: italic;
            color: #666;
            font-size: 12px;
        `;
        indicator.innerHTML = `
            <div style="
                width: 35px;
                height: 35px;
                border-radius: 50%;
                background: #e9ecef;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                font-size: 12px;
            ">${username.charAt(0).toUpperCase()}</div>
            <div>${username} is typing...</div>
        `;
        
        this.messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }
    
    hideTypingIndicator(username) {
        const indicator = this.messagesContainer.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }
    
    showNotificationBadge() {
        if (this.floatingIcon) {
            this.floatingIcon.classList.add('has-notifications');
        }
    }
    
    playNotificationSound() {
        if (window.notificationManager) {
            window.notificationManager.playSound('notification');
        }
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
    
    initializeMentionSystem() {
        console.log('Initializing mention system...');
        
        // Check if we're on the messenger page to avoid conflicts
        if (window.location.pathname.includes('/messenger')) {
            console.log('On messenger page, skipping floating message box mention system to avoid conflicts');
            return;
        }
        
        // Load users for mention suggestions
        this.loadMentionUsers();
        
        // Create mention dropdown
        this.createMentionDropdown();
        
        // Add input event listener for real-time mention detection
        if (this.messageInput) {
            this.messageInput.addEventListener('input', (e) => {
                this.handleMentionInput();
            });
            
            // Add keydown listener for navigation
            this.messageInput.addEventListener('keydown', (e) => {
                this.handleMentionNavigation(e);
            });
        }
        
        console.log('Mention system initialized');
    }
    
    loadMentionUsers() {
        console.log('Loading mention users...');
        fetch('/production/api/messenger/users/mention')
            .then(response => {
                console.log('API response status:', response.status);
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error(`API returned ${response.status}`);
                }
            })
            .then(data => {
                console.log('API data received:', data);
                if (data.success) {
                    this.mentionUsers = data.users || [];
                    this.updateMentionDropdown();
                    console.log('Loaded', this.mentionUsers.length, 'users for mentions');
                } else {
                    throw new Error(data.error || 'Failed to load users');
                }
            })
            .catch(error => {
                console.error('Error loading users for mentions:', error);
                // Fallback to mock users for testing
                this.mentionUsers = [
                    { id: 1, username: 'admin', name: 'Administrator', avatar: null },
                    { id: 2, username: 'john', name: 'John Doe', avatar: null },
                    { id: 3, username: 'jane', name: 'Jane Smith', avatar: null },
                    { id: 4, username: 'bob', name: 'Bob Johnson', avatar: null }
                ];
                this.updateMentionDropdown();
                console.log('Using fallback mock users for mentions');
            });
    }
    
    createMentionDropdown() {
        const messageInput = document.getElementById('message-box-input');
        if (!messageInput) {
            console.log('Message input not found for mention dropdown');
            return;
        }
        
        console.log('Creating mention dropdown for message input:', messageInput);
        
        // Use existing dropdown instead of creating a new one
        let dropdown = document.getElementById('mention-dropdown');
        if (!dropdown) {
            console.log('Existing mention dropdown not found, creating new one');
            dropdown = document.createElement('div');
            dropdown.id = 'mention-dropdown';
            dropdown.className = 'mention-dropdown';
            dropdown.style.cssText = `
                position: absolute;
                bottom: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 0.5rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                max-height: 300px;
                overflow-y: auto;
                z-index: 9999;
                display: none;
                min-width: 100%;
                margin-bottom: 0.5rem;
            `;
            
            // Append to the modal container instead of the input parent
            const modal = document.getElementById('message-box-modal');
            if (modal) {
                modal.appendChild(dropdown);
                console.log('Mention dropdown created and appended to modal');
            } else {
                messageInput.parentNode.appendChild(dropdown);
                console.log('Mention dropdown created and appended to input parent (fallback)');
            }
        } else {
            console.log('Using existing mention dropdown');
            // Update the existing dropdown styles
            dropdown.style.cssText = `
                position: absolute;
                bottom: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 0.5rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                max-height: 300px;
                overflow-y: auto;
                z-index: 9999;
                display: none;
                min-width: 100%;
                margin-bottom: 0.5rem;
            `;
        }
    }
    
    updateMentionDropdown() {
        const dropdown = document.getElementById('mention-dropdown');
        if (!dropdown) {
            console.log('Mention dropdown not found for update');
            return;
        }
        
        // Clear existing content but keep header
        const list = dropdown.querySelector('.mention-dropdown-list');
        if (list) {
            list.innerHTML = '';
        } else {
            // If no list exists, clear everything and recreate structure
            dropdown.innerHTML = '';
            const header = document.createElement('div');
            header.className = 'mention-dropdown-header';
            header.innerHTML = `
                <i class="fas fa-at text-primary"></i>
                <span>Mention someone</span>
            `;
            dropdown.appendChild(header);
            
            const newList = document.createElement('div');
            newList.className = 'mention-dropdown-list';
            dropdown.appendChild(newList);
        }
        
        const mentionList = dropdown.querySelector('.mention-dropdown-list');
        
        if (this.mentionUsers.length === 0) {
            mentionList.innerHTML = '<div class="mention-item"><span class="text-muted">No users found</span></div>';
            return;
        }
        
        this.mentionUsers.forEach(user => {
            const item = document.createElement('div');
            item.className = 'mention-item';
            item.style.cssText = `
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.75rem 1rem;
                cursor: pointer;
                transition: background-color 0.2s;
                border-bottom: 1px solid #f8f9fa;
            `;
            
            const avatar = user.avatar || user.name.charAt(0).toUpperCase();
            
            item.innerHTML = `
                <div class="mention-avatar" style="width: 32px; height: 32px; border-radius: 50%; background: #0d6efd; color: white; display: flex; align-items: center; justify-content: center; font-weight: 500; font-size: 0.875rem;">
                    ${user.avatar ? `<img src="${user.avatar}" alt="${user.name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">` : avatar}
                </div>
                <div class="mention-user-info" style="flex: 1;">
                    <div class="mention-user-name" style="font-weight: 500; color: #495057; margin-bottom: 0.125rem;">${user.name}</div>
                    <div class="mention-user-username" style="font-size: 0.75rem; color: #6c757d;">@${user.username}</div>
                </div>
                <i class="fas fa-chevron-right" style="color: #6c757d; font-size: 0.75rem;"></i>
            `;
            
            item.addEventListener('click', () => {
                this.insertMention(user.username);
            });
            
            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = '#f8f9fa';
            });
            
            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = '';
            });
            
            mentionList.appendChild(item);
        });
        
        console.log('Updated mention dropdown with', this.mentionUsers.length, 'users');
    }
    
    handleMentionInput() {
        const messageInput = document.getElementById('message-box-input');
        const dropdown = document.getElementById('mention-dropdown');
        if (!messageInput || !dropdown) {
            console.log('Message input or dropdown not found');
            return;
        }
        
        const cursorPos = messageInput.selectionStart;
        const text = messageInput.value;
        const beforeCursor = text.substring(0, cursorPos);
        
        // Check if we're typing a mention - improved regex to catch more patterns
        const mentionMatch = beforeCursor.match(/@([a-zA-Z0-9_]*)$/);
        
        console.log('Mention input check:', {
            text: text,
            beforeCursor: beforeCursor,
            mentionMatch: mentionMatch,
            mentionUsers: this.mentionUsers.length
        });
        
        if (mentionMatch) {
            const query = mentionMatch[1].toLowerCase();
            // If query is empty (just @), show all users
            const filteredUsers = this.mentionUsers.filter(user => 
                user && user.username && user.full_name &&
                (query === '' || 
                 user.username.toLowerCase().includes(query) ||
                 user.full_name.toLowerCase().includes(query))
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
        const messageInput = document.getElementById('message-box-input');
        if (!dropdown || !messageInput) {
            console.log('Mention dropdown or message input not found');
            return;
        }
        
        console.log('Showing mention dropdown with users:', users);
        
        // Position the dropdown below the input
        const inputContainer = messageInput.closest('.message-box-input');
        
        if (inputContainer) {
            // Make sure the input container has relative positioning
            inputContainer.style.position = 'relative';
            
            // Force minimal styling by removing all existing styles first
            dropdown.removeAttribute('style');
            dropdown.style.cssText = `
                position: absolute !important;
                bottom: 100% !important;
                left: 0 !important;
                right: 0 !important;
                background: white !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                max-height: 160px !important;
                overflow-y: auto !important;
                z-index: 9999 !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                min-width: 100% !important;
                margin-bottom: 0 !important;
                width: 100% !important;
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            `;
        } else {
            // Fallback positioning
            dropdown.removeAttribute('style');
            dropdown.style.cssText = `
                position: absolute !important;
                bottom: 100% !important;
                left: 0 !important;
                right: 0 !important;
                background: white !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                max-height: 160px !important;
                overflow-y: auto !important;
                z-index: 9999 !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                min-width: 100% !important;
                margin-bottom: 0 !important;
                width: 100% !important;
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            `;
        }
        dropdown.innerHTML = '';
        users.forEach(user => {
            const imgSrc = (user.profile_image && user.profile_image !== 'https://via.placeholder.com/150x150/007bff/ffffff?text=User') ? user.profile_image : '/static/images/default-avatar.png';
            const item = document.createElement('div');
            item.className = 'mention-item';
            item.style.cssText = `
                padding: 8px 12px;
                cursor: pointer;
                border-bottom: none;
                display: flex;
                align-items: center;
                gap: 6px;
                background: #fff;
                min-height: 32px;
                transition: background-color 0.15s ease;
            `;
            item.innerHTML = `
                <img src="${imgSrc}" alt="${user.full_name}" style="width: 18px; height: 18px; border-radius: 50%; object-fit: cover;">
                <span style="font-weight: 500; margin-right: 6px; font-size: 13px;">${user.full_name}</span>
                <span class="mention-username" style="color: #888; font-size: 11px;">@${user.username}</span>
            `;
            item.addEventListener('click', () => {
                this.insertMention(user.username);
            });
            dropdown.appendChild(item);
        });
        if (users.length > 0) {
            dropdown.style.display = 'block';
        } else {
            dropdown.style.display = 'none';
        }
        console.log('Mention dropdown displayed with', users.length, 'users');
    console.log('Dropdown element:', dropdown);
    console.log('Dropdown style:', dropdown.style.cssText);
    console.log('Dropdown computed style:', window.getComputedStyle(dropdown));
    console.log('Dropdown position:', dropdown.getBoundingClientRect());
    }
    
    insertMention(username) {
        const messageInput = document.getElementById('message-box-input');
        const dropdown = document.getElementById('mention-dropdown');
        if (!messageInput || !dropdown) return;
        
        const cursorPos = messageInput.selectionStart;
        const text = messageInput.value;
        const beforeCursor = text.substring(0, cursorPos);
        const afterCursor = text.substring(cursorPos);
        
        // Replace the @username with the full mention - improved regex
        const newText = beforeCursor.replace(/@[a-zA-Z0-9_]*$/, `@${username} `) + afterCursor;
        messageInput.value = newText;
        
        // Set cursor position after the mention
        const newCursorPos = beforeCursor.replace(/@[a-zA-Z0-9_]*$/, `@${username} `).length;
        messageInput.setSelectionRange(newCursorPos, newCursorPos);
        
        // Close dropdown and focus input
        dropdown.style.display = 'none';
        messageInput.focus();
        
        console.log('Mention inserted:', username);
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
                } else if (items.length > 0) {
                    // If no active item but dropdown has items, select the first one
                    const username = items[0].querySelector('.mention-username').textContent.substring(1);
                    this.insertMention(username);
                }
                // Close dropdown after selection
                dropdown.style.display = 'none';
                break;
                
            case 'Escape':
                event.preventDefault();
                dropdown.style.display = 'none';
                break;
        }
    }
    
    // Edit and Delete Message Functions
    editMessage(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;
        
        const messageText = messageElement.querySelector('.message-text');
        const contentText = messageElement.querySelector('.message-content-text');
        const currentContent = contentText.textContent;
        
        // Create edit input
        const editInput = document.createElement('textarea');
        editInput.className = 'message-edit-input';
        editInput.value = currentContent;
        editInput.rows = Math.max(1, Math.ceil(currentContent.length / 50));
        
        // Create edit actions
        const editActions = document.createElement('div');
        editActions.className = 'message-edit-actions';
        editActions.innerHTML = `
            <button class="message-edit-btn message-edit-save" onclick="window.floatingMessageBox.saveMessageEdit(${messageId})">
                <i class="fas fa-check"></i> Save
            </button>
            <button class="message-edit-btn message-edit-cancel" onclick="window.floatingMessageBox.cancelMessageEdit(${messageId})">
                <i class="fas fa-times"></i> Cancel
            </button>
        `;
        
        // Replace content with edit input
        contentText.style.display = 'none';
        messageText.appendChild(editInput);
        messageText.appendChild(editActions);
        messageText.classList.add('message-edit-mode');
        
        // Focus and select text
        editInput.focus();
        editInput.select();
    }
    
    saveMessageEdit(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;
        
        const editInput = messageElement.querySelector('.message-edit-input');
        const newContent = editInput.value.trim();
        
        if (!newContent) {
            alert('Message cannot be empty');
            return;
        }
        
        // Send edit request via Socket.IO
        if (this.socket) {
            this.socket.emit('edit_message', {
                message_id: messageId,
                content: newContent
            });
        }
        
        // Exit edit mode
        this.cancelMessageEdit(messageId);
    }
    
    cancelMessageEdit(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;
        
        const messageText = messageElement.querySelector('.message-text');
        const contentText = messageElement.querySelector('.message-content-text');
        const editInput = messageElement.querySelector('.message-edit-input');
        const editActions = messageElement.querySelector('.message-edit-actions');
        
        // Remove edit elements
        if (editInput) editInput.remove();
        if (editActions) editActions.remove();
        
        // Show original content
        contentText.style.display = 'block';
        messageText.classList.remove('message-edit-mode');
    }
    
    deleteMessage(messageId) {
        if (!confirm('Are you sure you want to delete this message? This action cannot be undone.')) {
            return;
        }
        
        // Send delete request via Socket.IO
        if (this.socket) {
            this.socket.emit('delete_message', {
                message_id: messageId
            });
        }
    }
    
    // Threaded Replies Functions
    showThreadReplies(messageId) {
        // Create thread modal
        const threadModal = document.createElement('div');
        threadModal.className = 'thread-modal';
        threadModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        threadModal.innerHTML = `
            <div class="thread-content" style="
                background: white;
                border-radius: 8px;
                width: 90%;
                max-width: 600px;
                max-height: 80%;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            ">
                <div class="thread-header" style="
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <h3 style="margin: 0;">Thread Replies</h3>
                    <button onclick="this.closest('.thread-modal').remove()" style="
                        background: none;
                        border: none;
                        font-size: 20px;
                        cursor: pointer;
                    ">&times;</button>
                </div>
                <div class="thread-messages" style="
                    flex: 1;
                    overflow-y: auto;
                    padding: 15px;
                "></div>
                <div class="thread-input" style="
                    padding: 15px;
                    border-top: 1px solid #eee;
                ">
                    <textarea placeholder="Reply to thread..." style="
                        width: 100%;
                        min-height: 60px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        resize: vertical;
                    "></textarea>
                    <button onclick="window.floatingMessageBox.sendThreadReply(${messageId}, this.previousElementSibling)" style="
                        margin-top: 8px;
                        padding: 8px 16px;
                        background: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    ">Send Reply</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(threadModal);
        
        // Load thread replies
        if (this.socket) {
            this.socket.emit('get_thread_replies', {
                parent_message_id: messageId
            });
        }
    }
    
    sendThreadReply(parentMessageId, inputElement) {
        const content = inputElement.value.trim();
        if (!content) return;
        
        if (this.socket) {
            this.socket.emit('send_thread_reply', {
                parent_message_id: parentMessageId,
                content: content,
                room: this.currentRoom
            });
        }
        
        inputElement.value = '';
    }
    
    addThreadReplyToUI(data) {
        const threadMessages = document.querySelector('.thread-messages');
        if (!threadMessages) return;
        
        const replyElement = document.createElement('div');
        replyElement.className = 'thread-reply';
        replyElement.style.cssText = `
            margin-bottom: 10px;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
        `;
        
        replyElement.innerHTML = `
            <div style="font-weight: bold; color: #007bff;">${data.sender_name}</div>
            <div style="margin-top: 4px;">${this.escapeHtml(data.content)}</div>
            <div style="font-size: 11px; color: #999; margin-top: 4px;">${this.formatTime(data.created_at)}</div>
        `;
        
        threadMessages.appendChild(replyElement);
        threadMessages.scrollTop = threadMessages.scrollHeight;
    }
    
    displayThreadReplies(data) {
        const threadMessages = document.querySelector('.thread-messages');
        if (!threadMessages) return;
        
        threadMessages.innerHTML = '';
        
        data.replies.forEach(reply => {
            const replyElement = document.createElement('div');
            replyElement.className = 'thread-reply';
            replyElement.style.cssText = `
                margin-bottom: 10px;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
            `;
            
            replyElement.innerHTML = `
                <div style="font-weight: bold; color: #007bff;">${reply.sender_name}</div>
                <div style="margin-top: 4px;">${this.escapeHtml(reply.content)}</div>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">${this.formatTime(reply.created_at)}</div>
            `;
            
            threadMessages.appendChild(replyElement);
        });
        
        threadMessages.scrollTop = threadMessages.scrollHeight;
    }
    
    // Pin Messages Functions
    pinMessage(messageId) {
        if (this.socket) {
            this.socket.emit('pin_message', {
                message_id: messageId,
                action: 'pin'
            });
        }
    }
    
    unpinMessage(messageId) {
        if (this.socket) {
            this.socket.emit('pin_message', {
                message_id: messageId,
                action: 'unpin'
            });
        }
    }
    
    updateMessagePinStatus(data) {
        const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
        if (!messageElement) return;
        
        const pinButton = messageElement.querySelector('.pin-button');
        if (pinButton) {
            if (data.is_pinned) {
                pinButton.innerHTML = '<i class="fas fa-thumbtack" style="color: #007bff;"></i>';
                pinButton.title = 'Unpin message';
                pinButton.onclick = () => this.unpinMessage(data.message_id);
            } else {
                pinButton.innerHTML = '<i class="fas fa-thumbtack"></i>';
                pinButton.title = 'Pin message';
                pinButton.onclick = () => this.pinMessage(data.message_id);
            }
        }
        
        // Show notification
        this.showToast(`${data.pinned_by} ${data.action} a message`);
    }
    
    displayPinnedMessages(data) {
        // This would be called when viewing pinned messages section
        console.log('Pinned messages loaded:', data);
    }
    
    showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10001;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    // Media Handling Methods
    initializeMediaHandling() {
        this.setupDragAndDrop();
        this.addMediaButtons();
    }
    
    setupDragAndDrop() {
        const messageInput = this.messageInput;
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            messageInput.addEventListener(eventName, this.preventDefaults.bind(this), false);
        });
        
        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            messageInput.addEventListener(eventName, this.highlightDropArea.bind(this), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            messageInput.addEventListener(eventName, this.unhighlightDropArea.bind(this), false);
        });
        
        // Handle dropped files
        messageInput.addEventListener('drop', this.handleDrop.bind(this), false);
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    highlightDropArea(e) {
        this.messageInput.style.borderColor = '#007bff';
        this.messageInput.style.backgroundColor = '#e3f2fd';
    }
    
    unhighlightDropArea(e) {
        this.messageInput.style.borderColor = '';
        this.messageInput.style.backgroundColor = '';
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            this.uploadFiles(files);
        }
    }
    
    addMediaButtons() {
        // Add media gallery button to the message box header
        const messageBoxHeader = document.querySelector('.message-box-header');
        if (messageBoxHeader) {
            const mediaButton = document.createElement('button');
            mediaButton.className = 'message-box-action-btn';
            mediaButton.innerHTML = '<i class="fas fa-images"></i>';
            mediaButton.title = 'Media Gallery';
            mediaButton.onclick = () => window.open('/production/media-gallery', '_blank');
            
            // Insert before the maximize button
            const maximizeBtn = messageBoxHeader.querySelector('.message-box-maximize');
            if (maximizeBtn) {
                maximizeBtn.parentNode.insertBefore(mediaButton, maximizeBtn);
            } else {
                messageBoxHeader.appendChild(mediaButton);
            }
        }
    }
    
    uploadFiles(files) {
        Array.from(files).forEach((file, index) => {
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/production/api/media/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Add media message to chat
                    const mediaMessage = {
                        id: data.message_id,
                        sender_id: this.getCurrentUserId(),
                        sender_name: this.getCurrentUserName(),
                        content: `Shared ${data.file_name}`,
                        message_type: 'file',
                        file_url: data.file_url,
                        file_name: data.file_name,
                        media_type: data.media_type,
                        file_size: data.file_size,
                        created_at: new Date().toISOString()
                    };
                    
                    this.addMessageToUI(mediaMessage);
                    this.showToast(`Uploaded ${data.file_name}`);
                } else {
                    this.showToast(`Error uploading ${file.name}: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Upload error:', error);
                this.showToast(`Error uploading ${file.name}`);
            });
        });
    }
    
    getCurrentUserId() {
        // This should be set from the server-side template
        return window.currentUserId || 1;
    }
    
    getCurrentUserName() {
        // This should be set from the server-side template
        return window.currentUserName || 'User';
    }
    
    getMediaIcon(mediaType) {
        const icons = {
            'image': 'fas fa-image',
            'video': 'fas fa-video',
            'audio': 'fas fa-music',
            'document': 'fas fa-file-alt',
            'link': 'fas fa-link'
        };
        return icons[mediaType] || 'fas fa-file';
    }
    
    getMediaColor(mediaType) {
        const colors = {
            'image': '#28a745',
            'video': '#dc3545',
            'audio': '#ffc107',
            'document': '#17a2b8',
            'link': '#6f42c1'
        };
        return colors[mediaType] || '#6c757d';
    }
    
    downloadMedia(fileUrl, fileName) {
        const link = document.createElement('a');
        link.href = fileUrl;
        link.download = fileName;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    createMediaAttachment(message) {
        const mediaType = message.media_type || 'document';
        const mediaIcon = this.getMediaIcon(mediaType);
        const mediaColor = this.getMediaColor(mediaType);
        
        return `
            <div class="media-attachment" style="
                margin-top: 8px;
                padding: 10px;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                border-left: 4px solid ${mediaColor};
            ">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="${mediaIcon}" style="color: ${mediaColor}; font-size: 20px;"></i>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: inherit;">${message.file_name}</div>
                        <div style="font-size: 12px; opacity: 0.8;">${message.file_size} MB</div>
                    </div>
                    <button class="btn btn-sm btn-outline-light" onclick="window.floatingMessageBox.downloadMedia('${message.file_url}', '${message.file_name}')" title="Download" style="
                        background: rgba(255,255,255,0.2);
                        border: 1px solid rgba(255,255,255,0.3);
                        color: inherit;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                    ">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Convert to Task functionality
    showConvertToTaskModal(messageId, messageContent) {
        // For floating message box, we'll redirect to the full messenger
        // since the modal is defined there
        window.open(`/production/messenger?convert_task=${messageId}&content=${encodeURIComponent(messageContent)}`, '_blank');
    }
    
    // Set Reminder functionality
    showSetReminderModal(messageId, messageContent) {
        // For floating message box, we'll redirect to the full messenger
        // since the modal is defined there
        window.open(`/production/messenger?set_reminder=${messageId}&content=${encodeURIComponent(messageContent)}`, '_blank');
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
}

// Initialize floating message box when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('floating-message-icon')) {
        window.floatingMessageBox = new FloatingMessageBox();
    }
});
