/**
 * Team-Based Messenger JavaScript
 * Handles team-based filtering and UI for the messenger system
 */

class TeamMessenger {
    constructor() {
        this.currentTeam = null;
        this.userTeams = [];
        this.currentUser = null;
        this.messages = [];
        this.groups = [];
        this.isInitialized = false;
        
        this.initialize();
    }
    
    async initialize() {
        console.log('Initializing Team Messenger...');
        
        // Get current user info
        await this.getCurrentUser();
        
        // Get user's teams
        await this.loadUserTeams();
        
        // Initialize UI
        this.initializeUI();
        
        // Load initial data
        await this.loadTeamData();
        
        this.isInitialized = true;
        console.log('Team Messenger initialized successfully');
    }
    
    async getCurrentUser() {
        try {
            const response = await fetch('/production/api/messenger/current-user');
            const data = await response.json();
            if (data.success) {
                this.currentUser = data.user;
                console.log('Current user:', this.currentUser);
            }
        } catch (error) {
            console.error('Error getting current user:', error);
        }
    }
    
    async loadUserTeams() {
        try {
            console.log('Loading user teams...');
            const response = await fetch('/production/api/messenger/teams');
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                console.error('Response not ok:', response.status, response.statusText);
                return;
            }
            
            const data = await response.json();
            console.log('Teams API response:', data);
            
            if (data.success) {
                this.userTeams = data.teams;
                console.log('User teams:', this.userTeams);
                
                // Set current team to first team if available
                if (this.userTeams.length > 0) {
                    this.currentTeam = this.userTeams[0];
                    console.log('Current team set to:', this.currentTeam.name);
                }
            } else {
                console.error('Teams API error:', data.error);
            }
        } catch (error) {
            console.error('Error loading user teams:', error);
        }
    }
    
    initializeUI() {
        // Create team selector
        this.createTeamSelector();
        
        // Create team filter controls
        this.createTeamFilterControls();
        
        // Update sidebar to show team-specific content
        this.updateTeamSidebar();
        
        // Add event listeners
        this.addEventListeners();
    }
    
    createTeamSelector() {
        const messengerHeader = document.querySelector('.messenger-header-left');
        if (!messengerHeader) return;
        
        // Create team selector container
        const teamSelectorContainer = document.createElement('div');
        teamSelectorContainer.className = 'team-selector-container';
        teamSelectorContainer.innerHTML = `
            <div class="team-selector">
                <label for="team-select">Team:</label>
                <select id="team-select" class="form-control form-control-sm">
                    <option value="">All Teams</option>
                </select>
            </div>
        `;
        
        // Insert after the title
        const title = messengerHeader.querySelector('h2');
        title.parentNode.insertBefore(teamSelectorContainer, title.nextSibling);
        
        // Populate team options
        this.populateTeamOptions();
    }
    
    populateTeamOptions() {
        const teamSelect = document.getElementById('team-select');
        if (!teamSelect) return;
        
        // Clear existing options except "All Teams"
        while (teamSelect.children.length > 1) {
            teamSelect.removeChild(teamSelect.lastChild);
        }
        
        // Add team options
        this.userTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.id;
            option.textContent = team.name;
            option.dataset.teamId = team.id;
            teamSelect.appendChild(option);
        });
        
        // Set current team if available
        if (this.currentTeam) {
            teamSelect.value = this.currentTeam.id;
        }
    }
    
    createTeamFilterControls() {
        const sidebar = document.querySelector('.messenger-sidebar');
        if (!sidebar) return;
        
        // Create team filter section
        const teamFilterSection = document.createElement('div');
        teamFilterSection.className = 'sidebar-section team-filter-section';
        teamFilterSection.innerHTML = `
            <h5><i class="fas fa-filter"></i> Team Filter</h5>
            <div class="team-filter-controls">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="show-team-only" checked>
                    <label class="form-check-label" for="show-team-only">
                        Show team content only
                    </label>
                </div>
                <div class="team-info" id="team-info">
                    <!-- Team info will be displayed here -->
                </div>
            </div>
        `;
        
        // Insert at the top of sidebar
        sidebar.insertBefore(teamFilterSection, sidebar.firstChild);
        
        // Update team info
        this.updateTeamInfo();
    }
    
    updateTeamInfo() {
        const teamInfo = document.getElementById('team-info');
        if (!teamInfo) return;
        
        if (this.currentTeam) {
            teamInfo.innerHTML = `
                <div class="current-team-info">
                    <strong>${this.currentTeam.name}</strong>
                    <small class="text-muted">${this.currentTeam.description}</small>
                    <span class="badge badge-${this.currentTeam.is_manager ? 'primary' : 'secondary'}">
                        ${this.currentTeam.is_manager ? 'Manager' : 'Member'}
                    </span>
                </div>
            `;
        } else {
            teamInfo.innerHTML = `
                <div class="no-team-info">
                    <small class="text-muted">No team assigned</small>
                </div>
            `;
        }
    }
    
    updateTeamSidebar() {
        // Update conversations list to show team-specific groups
        this.loadTeamGroups();
        
        // Update online users to show team members
        this.loadTeamUsers();
    }
    
    async loadTeamGroups() {
        try {
            const response = await fetch('/production/api/groups');
            const data = await response.json();
            if (data.groups) {
                this.groups = data.groups;
                this.displayTeamGroups();
            }
        } catch (error) {
            console.error('Error loading team groups:', error);
        }
    }
    
    displayTeamGroups() {
        const conversationsList = document.getElementById('conversations-list');
        if (!conversationsList) return;
        
        // Clear existing conversations
        conversationsList.innerHTML = '';
        
        // Filter groups by current team
        const teamGroups = this.currentTeam ? 
            this.groups.filter(group => group.team_id === this.currentTeam.id) :
            this.groups;
        
        if (teamGroups.length === 0) {
            conversationsList.innerHTML = `
                <div class="no-conversations">
                    <small class="text-muted">No team conversations available</small>
                </div>
            `;
            return;
        }
        
        // Display team groups
        teamGroups.forEach(group => {
            const groupElement = this.createGroupElement(group);
            conversationsList.appendChild(groupElement);
        });
    }
    
    createGroupElement(group) {
        const groupElement = document.createElement('div');
        groupElement.className = 'conversation-item team-group';
        groupElement.dataset.groupId = group.id;
        groupElement.dataset.teamId = group.team_id;
        
        // Check if user is manager (can delete groups)
        const isManager = this.currentUser && this.currentUser.role && 
            ['productions_manager', 'marketing_manager', 'admin'].includes(this.currentUser.role.name);
        
        groupElement.innerHTML = `
            <div class="conversation-info">
                <div class="conversation-name">
                    <i class="fas fa-users"></i>
                    ${group.name}
                </div>
                <div class="conversation-meta">
                    <small class="text-muted">${group.member_count} members</small>
                    ${group.team_name ? `<span class="badge badge-info badge-sm">${group.team_name}</span>` : ''}
                    ${isManager ? `<button class="btn btn-sm btn-outline-danger delete-group-btn" data-group-id="${group.id}" title="Delete Group">
                        <i class="fas fa-trash"></i>
                    </button>` : ''}
                </div>
            </div>
        `;
        
        // Add click event (but not on delete button)
        groupElement.addEventListener('click', (e) => {
            if (!e.target.classList.contains('delete-group-btn')) {
                this.selectGroup(group);
            }
        });
        
        return groupElement;
    }
    
    async loadTeamUsers() {
        try {
            const response = await fetch('/production/api/messenger/users/online');
            const data = await response.json();
            if (data.success && data.users) {
                this.displayTeamUsers(data.users);
            }
        } catch (error) {
            console.error('Error loading team users:', error);
        }
    }
    
    displayTeamUsers(users) {
        const usersList = document.getElementById('users-list');
        if (!usersList) return;
        
        // Clear existing users
        usersList.innerHTML = '';
        
        // Filter users by current team
        const teamUsers = this.currentTeam ? 
            users.filter(user => user.team_id === this.currentTeam.id) :
            users;
        
        if (teamUsers.length === 0) {
            usersList.innerHTML = `
                <div class="no-users">
                    <small class="text-muted">No team members online</small>
                </div>
            `;
            return;
        }
        
        // Display team users
        teamUsers.forEach(user => {
            const userElement = this.createUserElement(user);
            usersList.appendChild(userElement);
        });
    }
    
    createUserElement(user) {
        const userElement = document.createElement('div');
        userElement.className = 'user-item';
        userElement.dataset.userId = user.id;
        
        userElement.innerHTML = `
            <div class="user-info">
                <div class="user-avatar">
                    <img src="${user.avatar_url || '/static/images/default-avatar.png'}" alt="${user.full_name}">
                    <span class="online-indicator ${user.is_online ? 'online' : 'offline'}"></span>
                </div>
                <div class="user-details">
                    <div class="user-name">${user.full_name}</div>
                    <small class="text-muted">${user.username}</small>
                </div>
            </div>
        `;
        
        return userElement;
    }
    
    async loadTeamData() {
        // Load team messages
        await this.loadTeamMessages();
        
        // Load team groups
        await this.loadTeamGroups();
        
        // Load team users
        await this.loadTeamUsers();
    }
    
    async loadTeamMessages() {
        try {
            const response = await fetch('/production/api/messenger/messages');
            const data = await response.json();
            if (data.success) {
                this.messages = data.messages;
                this.displayTeamMessages();
            }
        } catch (error) {
            console.error('Error loading team messages:', error);
        }
    }
    
    displayTeamMessages() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        // Clear existing messages
        messagesList.innerHTML = '';
        
        // Filter messages by current team
        const teamMessages = this.currentTeam ? 
            this.messages.filter(message => message.team_id === this.currentTeam.id) :
            this.messages;
        
        if (teamMessages.length === 0) {
            messagesList.innerHTML = `
                <div class="no-messages">
                    <small class="text-muted">No team messages available</small>
                </div>
            `;
            return;
        }
        
        // Display team messages
        teamMessages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            messagesList.appendChild(messageElement);
        });
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    createMessageElement(message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.is_own ? 'own-message' : 'other-message'}`;
        messageElement.dataset.messageId = message.id;
        
        messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">${message.sender_name}</span>
                    <span class="message-time">${this.formatTime(message.created_at)}</span>
                </div>
                <div class="message-text">${this.formatMessageContent(message.content)}</div>
                ${message.is_edited ? '<small class="text-muted">(edited)</small>' : ''}
            </div>
        `;
        
        return messageElement;
    }
    
    formatMessageContent(content) {
        // Basic formatting - you can enhance this
        return content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('messages-container');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    selectGroup(group) {
        console.log('Selected group:', group);
        // Update UI to show selected group
        this.updateChatTitle(group.name);
        
        // Load group messages
        this.loadGroupMessages(group.id);
    }
    
    updateChatTitle(title) {
        const chatTitle = document.getElementById('current-chat-title');
        if (chatTitle) {
            chatTitle.textContent = title;
        }
    }
    
    async loadGroupMessages(groupId) {
        try {
            const response = await fetch(`/production/api/groups/${groupId}/messages`);
            const data = await response.json();
            if (data.success) {
                this.messages = data.messages;
                this.currentGroupId = groupId;
                this.displayTeamMessages();
            } else {
                console.error('Error loading group messages:', data.error);
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading group messages:', error);
            this.showToast('Error loading group messages', 'error');
        }
    }
    
    addEventListeners() {
        // Team selector change
        const teamSelect = document.getElementById('team-select');
        if (teamSelect) {
            teamSelect.addEventListener('change', (e) => {
                const teamId = e.target.value;
                if (teamId) {
                    this.currentTeam = this.userTeams.find(team => team.id == teamId);
                } else {
                    this.currentTeam = null;
                }
                this.updateTeamInfo();
                this.loadTeamData();
            });
        }
        
        // Team filter checkbox
        const showTeamOnly = document.getElementById('show-team-only');
        if (showTeamOnly) {
            showTeamOnly.addEventListener('change', (e) => {
                this.loadTeamData();
            });
        }
        
        // Message input
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // Send button
        const sendButton = document.getElementById('send-message-btn');
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });
        }
        
        // Create group button
        const createGroupBtn = document.getElementById('create-group-btn');
        if (createGroupBtn) {
            createGroupBtn.addEventListener('click', () => {
                this.showCreateGroupModal();
            });
        }
        
        // Group delete buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-group-btn')) {
                const groupId = e.target.dataset.groupId;
                this.deleteGroup(groupId);
            }
        });
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        if (!messageInput || !messageInput.value.trim()) return;
        
        const content = messageInput.value.trim();
        const teamId = this.currentTeam ? this.currentTeam.id : null;
        const groupId = this.currentGroupId || null;
        
        try {
            const response = await fetch('/production/api/messenger/messages/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    content: content,
                    team_id: teamId,
                    group_id: groupId
                })
            });
            
            const data = await response.json();
            if (data.success) {
                messageInput.value = '';
                // Reload messages to show the new message
                if (groupId) {
                    await this.loadGroupMessages(groupId);
                } else {
                    await this.loadTeamMessages();
                }
            } else {
                console.error('Error sending message:', data.error);
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showToast('Error sending message', 'error');
        }
    }
    
    async showCreateGroupModal() {
        console.log('Showing create group modal...');
        console.log('Current team:', this.currentTeam);
        
        if (!this.currentTeam) {
            this.showToast('Please select a team first', 'error');
            return;
        }
        
        // Load team members
        try {
            console.log('Loading team members for team ID:', this.currentTeam.id);
            const response = await fetch(`/production/api/teams/${this.currentTeam.id}/members`);
            console.log('Team members response status:', response.status);
            
            if (!response.ok) {
                console.error('Team members response not ok:', response.status, response.statusText);
                this.showToast('Failed to load team members', 'error');
                return;
            }
            
            const data = await response.json();
            console.log('Team members API response:', data);
            
            if (!data.success) {
                console.error('Team members API error:', data.error);
                this.showToast('Failed to load team members', 'error');
                return;
            }
            
            console.log('Team members loaded:', data.members);
            this.showCreateGroupForm(data.members);
        } catch (error) {
            console.error('Error loading team members:', error);
            this.showToast('Error loading team members', 'error');
        }
    }
    
    showCreateGroupForm(teamMembers) {
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'createGroupModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Create New Group</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="createGroupForm">
                            <div class="mb-3">
                                <label for="groupName" class="form-label">Group Name</label>
                                <input type="text" class="form-control" id="groupName" required>
                            </div>
                            <div class="mb-3">
                                <label for="groupDescription" class="form-label">Description</label>
                                <textarea class="form-control" id="groupDescription" rows="3"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Add Members</label>
                                <div class="member-selection">
                                    ${teamMembers.map(member => `
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" value="${member.id}" id="member_${member.id}">
                                            <label class="form-check-label" for="member_${member.id}">
                                                ${member.name} (${member.role})
                                            </label>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="teamMessenger.createGroup()">Create Group</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Store modal reference
        this.createGroupModal = modal;
    }
    
    async createGroup() {
        const groupName = document.getElementById('groupName').value.trim();
        const groupDescription = document.getElementById('groupDescription').value.trim();
        
        if (!groupName) {
            this.showToast('Group name is required', 'error');
            return;
        }
        
        // Get selected members
        const selectedMembers = [];
        document.querySelectorAll('#createGroupForm input[type="checkbox"]:checked').forEach(checkbox => {
            selectedMembers.push(parseInt(checkbox.value));
        });
        
        try {
            const response = await fetch('/production/api/groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    name: groupName,
                    description: groupDescription,
                    team_id: this.currentTeam.id,
                    member_ids: selectedMembers
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Group created successfully!', 'success');
                
                // Close modal
                const bootstrapModal = bootstrap.Modal.getInstance(this.createGroupModal);
                bootstrapModal.hide();
                this.createGroupModal.remove();
                
                // Reload groups
                await this.loadTeamGroups();
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            console.error('Error creating group:', error);
            this.showToast('Error creating group', 'error');
        }
    }
    
    async deleteGroup(groupId) {
        if (!confirm('Are you sure you want to delete this group? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/production/api/groups/${groupId}/delete`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Group deleted successfully!', 'success');
                
                // Reload groups
                await this.loadTeamGroups();
            } else {
                this.showToast(data.error, 'error');
            }
        } catch (error) {
            console.error('Error deleting group:', error);
            this.showToast('Error deleting group', 'error');
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span>${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    }
}

// Initialize Team Messenger when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.teamMessenger = new TeamMessenger();
});

// Export for global access
window.TeamMessenger = TeamMessenger; 