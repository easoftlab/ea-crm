// PWA Installation and Offline Support
class PWAInstallManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.offlineData = [];
        
        this.initializePWA();
        this.initializeOfflineSupport();
        this.checkInstallationStatus();
    }
    
    initializePWA() {
        // Listen for the beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('PWA install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt();
        });
        
        // Listen for app installed event
        window.addEventListener('appinstalled', (e) => {
            console.log('PWA was installed');
            this.isInstalled = true;
            this.hideInstallPrompt();
            this.showToast('🎉 EA CRM has been installed!', 'success');
        });
        
        // Check if app is running in standalone mode
        if (window.matchMedia('(display-mode: standalone)').matches || 
            window.navigator.standalone === true) {
            this.isInstalled = true;
            console.log('App is running in standalone mode');
        }
    }
    
    initializeOfflineSupport() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then((registration) => {
                    console.log('Service Worker registered:', registration);
                    this.serviceWorker = registration;
                    
                    // Listen for service worker updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                this.showUpdatePrompt();
                            }
                        });
                    });
                })
                .catch((error) => {
                    console.error('Service Worker registration failed:', error);
                });
        }
        
        // Initialize IndexedDB for offline storage
        this.initializeOfflineStorage();
        
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.handleOnline();
        });
        
        window.addEventListener('offline', () => {
            this.handleOffline();
        });
    }
    
    initializeOfflineStorage() {
        const request = indexedDB.open('EA_CRM_PWA', 1);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            // Offline data store
            if (!db.objectStoreNames.contains('offline_data')) {
                const store = db.createObjectStore('offline_data', { keyPath: 'id', autoIncrement: true });
                store.createIndex('type', 'type', { unique: false });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
            
            // User preferences store
            if (!db.objectStoreNames.contains('user_preferences')) {
                const store = db.createObjectStore('user_preferences', { keyPath: 'key' });
            }
            
            // Cached data store
            if (!db.objectStoreNames.contains('cached_data')) {
                const store = db.createObjectStore('cached_data', { keyPath: 'url' });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
        
        request.onsuccess = (event) => {
            this.db = event.target.result;
            console.log('PWA offline storage initialized');
        };
    }
    
    showInstallPrompt() {
        // Create install prompt if it doesn't exist
        if (!document.getElementById('pwa-install-prompt')) {
            const prompt = document.createElement('div');
            prompt.id = 'pwa-install-prompt';
            prompt.className = 'pwa-install-prompt';
            prompt.innerHTML = `
                <h6>📱 Install EA CRM</h6>
                <p>Install our app for a better experience with offline support!</p>
                <button class="btn btn-primary btn-sm install-btn">Install App</button>
                <button class="btn btn-secondary btn-sm dismiss-btn">Not Now</button>
            `;
            
            document.body.appendChild(prompt);
            
            // Add event listeners
            prompt.querySelector('.install-btn').addEventListener('click', () => {
                this.installPWA();
            });
            
            prompt.querySelector('.dismiss-btn').addEventListener('click', () => {
                this.hideInstallPrompt();
            });
        }
    }
    
    hideInstallPrompt() {
        const prompt = document.getElementById('pwa-install-prompt');
        if (prompt) {
            prompt.remove();
        }
    }
    
    showUpdatePrompt() {
        const updatePrompt = document.createElement('div');
        updatePrompt.className = 'pwa-install-prompt';
        updatePrompt.innerHTML = `
            <h6>🔄 Update Available</h6>
            <p>A new version of EA CRM is available!</p>
            <button class="btn btn-primary btn-sm update-btn">Update Now</button>
            <button class="btn btn-secondary btn-sm dismiss-btn">Later</button>
        `;
        
        document.body.appendChild(updatePrompt);
        
        updatePrompt.querySelector('.update-btn').addEventListener('click', () => {
            this.updatePWA();
        });
        
        updatePrompt.querySelector('.dismiss-btn').addEventListener('click', () => {
            updatePrompt.remove();
        });
    }
    
    async installPWA() {
        if (!this.deferredPrompt) {
            console.log('No install prompt available');
            return;
        }
        
        try {
            // Show the install prompt
            this.deferredPrompt.prompt();
            
            // Wait for the user to respond to the prompt
            const { outcome } = await this.deferredPrompt.userChoice;
            
            if (outcome === 'accepted') {
                console.log('User accepted the install prompt');
                this.hideInstallPrompt();
            } else {
                console.log('User dismissed the install prompt');
            }
            
            // Clear the deferredPrompt
            this.deferredPrompt = null;
        } catch (error) {
            console.error('Error installing PWA:', error);
        }
    }
    
    updatePWA() {
        if (this.serviceWorker && this.serviceWorker.waiting) {
            // Send message to service worker to skip waiting
            this.serviceWorker.waiting.postMessage({ type: 'SKIP_WAITING' });
            
            // Reload the page when the new service worker takes over
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                window.location.reload();
            });
        }
    }
    
    checkInstallationStatus() {
        // Check if app is installed
        if (window.matchMedia('(display-mode: standalone)').matches || 
            window.navigator.standalone === true) {
            this.isInstalled = true;
            console.log('App is installed and running in standalone mode');
        }
        
        // Check if service worker is active
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then((registration) => {
                if (registration.active) {
                    console.log('Service Worker is active');
                }
            });
        }
    }
    
    handleOnline() {
        console.log('Connection restored');
        this.showToast('🟢 Back online - syncing data...', 'success');
        
        // Sync offline data
        this.syncOfflineData();
        
        // Update connection status
        this.updateConnectionStatus(true);
    }
    
    handleOffline() {
        console.log('Connection lost');
        this.showToast('🔴 You are offline - some features may be limited', 'warning');
        
        // Update connection status
        this.updateConnectionStatus(false);
    }
    
    updateConnectionStatus(isOnline) {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            statusIndicator.className = `connection-status ${isOnline ? 'connected' : 'disconnected'}`;
            statusIndicator.textContent = isOnline ? '🟢 Online' : '🔴 Offline';
        }
    }
    
    async syncOfflineData() {
        if (!this.db) return;
        
        try {
            const transaction = this.db.transaction(['offline_data'], 'readwrite');
            const store = transaction.objectStore('offline_data');
            const request = store.getAll();
            
            request.onsuccess = () => {
                const offlineData = request.result;
                
                if (offlineData.length > 0) {
                    console.log(`Syncing ${offlineData.length} offline items`);
                    
                    // Process offline data
                    offlineData.forEach(item => {
                        this.processOfflineItem(item);
                    });
                    
                    // Clear offline data after successful sync
                    const clearTransaction = this.db.transaction(['offline_data'], 'readwrite');
                    const clearStore = clearTransaction.objectStore('offline_data');
                    clearStore.clear();
                    
                    this.showToast('🔄 Offline data synced successfully', 'success');
                }
            };
        } catch (error) {
            console.error('Error syncing offline data:', error);
        }
    }
    
    processOfflineItem(item) {
        switch (item.type) {
            case 'chat_message':
                this.syncChatMessage(item.data);
                break;
            case 'task_update':
                this.syncTaskUpdate(item.data);
                break;
            case 'notification':
                this.syncNotification(item.data);
                break;
            default:
                console.log('Unknown offline item type:', item.type);
        }
    }
    
    syncChatMessage(data) {
        // Send chat message to server
        fetch('/production/api/chat/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                console.log('Chat message synced');
            }
        })
        .catch(error => {
            console.error('Error syncing chat message:', error);
        });
    }
    
    syncTaskUpdate(data) {
        // Send task update to server
        fetch(`/production/api/tasks/${data.task_id}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                console.log('Task update synced');
            }
        })
        .catch(error => {
            console.error('Error syncing task update:', error);
        });
    }
    
    syncNotification(data) {
        // Send notification to server
        fetch('/production/api/notifications', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                console.log('Notification synced');
            }
        })
        .catch(error => {
            console.error('Error syncing notification:', error);
        });
    }
    
    storeOfflineData(type, data) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['offline_data'], 'readwrite');
        const store = transaction.objectStore('offline_data');
        
        const offlineItem = {
            type: type,
            data: data,
            timestamp: Date.now()
        };
        
        store.add(offlineItem);
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    showToast(message, type = 'info') {
        if (window.notificationManager) {
            window.notificationManager.showToast(message, type);
        } else {
            // Fallback toast implementation
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    // Request notification permission
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then((permission) => {
                if (permission === 'granted') {
                    console.log('Notification permission granted');
                    this.showToast('🔔 Notifications enabled', 'success');
                } else {
                    console.log('Notification permission denied');
                }
            });
        }
    }
    
    // Send push notification
    sendPushNotification(title, body, data = {}) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification(title, {
                body: body,
                icon: '/static/images/icon-192x192.png',
                badge: '/static/images/badge-72x72.png',
                data: data,
                requireInteraction: false
            });
            
            notification.onclick = () => {
                window.focus();
                notification.close();
                
                // Navigate to specific page if data contains URL
                if (data.url) {
                    window.location.href = data.url;
                }
            };
        }
    }
}

// Initialize PWA Install Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.pwaInstallManager = new PWAInstallManager();
    
    // Request notification permission on first visit
    if (!localStorage.getItem('notification_permission_requested')) {
        setTimeout(() => {
            window.pwaInstallManager.requestNotificationPermission();
            localStorage.setItem('notification_permission_requested', 'true');
        }, 3000);
    }
}); 