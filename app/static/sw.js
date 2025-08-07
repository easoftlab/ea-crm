// Service Worker for EA CRM PWA
const CACHE_NAME = 'ea-crm-v1.0.0';
const STATIC_CACHE = 'ea-crm-static-v1.0.0';
const DYNAMIC_CACHE = 'ea-crm-dynamic-v1.0.0';

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/css/custom.css',
    '/static/js/dashboard.js',
    '/static/js/chat.js',
    '/static/js/notifications.js',
    '/static/js/kanban-board.js',
    '/static/js/gantt-chart.js',
    '/static/js/ai-insights.js',
    '/static/js/floating-message-box.js',
    '/static/js/facebook-notifications.js',
    '/static/sounds/notification.wav',
    '/static/sounds/message.wav',
    '/static/sounds/mention.wav',
    '/static/images/logo.png',
    '/static/images/default-avatar.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js'
];

// API endpoints to cache for offline access
const API_CACHE_PATTERNS = [
    '/production/api/chat/messages',
    '/production/api/tasks',
    '/production/api/notifications',
    '/production/api/user/status'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('Static files cached successfully');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('Error caching static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - handle offline functionality
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Handle API requests with offline support
    if (isApiRequest(url.pathname)) {
        event.respondWith(handleApiRequest(request));
        return;
    }

    // Handle static file requests
    if (isStaticFile(url.pathname)) {
        event.respondWith(handleStaticRequest(request));
        return;
    }

    // Handle navigation requests
    if (request.mode === 'navigate') {
        event.respondWith(handleNavigationRequest(request));
        return;
    }

    // Default network-first strategy for other requests
    event.respondWith(
        fetch(request)
            .then((response) => {
                // Cache successful responses
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(DYNAMIC_CACHE)
                        .then((cache) => {
                            cache.put(request, responseClone);
                        });
                }
                return response;
            })
            .catch(() => {
                // Return cached version if available
                return caches.match(request);
            })
    );
});

// Handle API requests with offline queue
function handleApiRequest(request) {
    return fetch(request)
        .then((response) => {
            // Cache successful API responses
            if (response.status === 200) {
                const responseClone = response.clone();
                caches.open(DYNAMIC_CACHE)
                    .then((cache) => {
                        cache.put(request, responseClone);
                    });
            }
            return response;
        })
        .catch((error) => {
            console.log('API request failed, checking cache:', request.url);
            
            // For POST/PUT requests, queue for later sync
            if (request.method === 'POST' || request.method === 'PUT') {
                return queueForSync(request);
            }
            
            // For GET requests, return cached version
            return caches.match(request)
                .then((cachedResponse) => {
                    if (cachedResponse) {
                        console.log('Returning cached API response');
                        return cachedResponse;
                    }
                    
                    // Return offline response
                    return createOfflineResponse(request);
                });
        });
}

// Handle static file requests
function handleStaticRequest(request) {
    return caches.match(request)
        .then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            
            return fetch(request)
                .then((response) => {
                    if (response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(STATIC_CACHE)
                            .then((cache) => {
                                cache.put(request, responseClone);
                            });
                    }
                    return response;
                });
        });
}

// Handle navigation requests
function handleNavigationRequest(request) {
    return fetch(request)
        .then((response) => {
            // Cache successful navigation responses
            if (response.status === 200) {
                const responseClone = response.clone();
                caches.open(DYNAMIC_CACHE)
                    .then((cache) => {
                        cache.put(request, responseClone);
                    });
            }
            return response;
        })
        .catch(() => {
            // Return offline page
            return caches.match('/offline.html')
                .then((offlineResponse) => {
                    if (offlineResponse) {
                        return offlineResponse;
                    }
                    
                    // Create basic offline page
                    return new Response(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Offline - EA CRM</title>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                .offline-icon { font-size: 64px; color: #6c757d; margin-bottom: 20px; }
                                .retry-btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                            </style>
                        </head>
                        <body>
                            <div class="offline-icon">📱</div>
                            <h1>You're Offline</h1>
                            <p>Please check your internet connection and try again.</p>
                            <button class="retry-btn" onclick="window.location.reload()">Retry</button>
                        </body>
                        </html>
                    `, {
                        headers: { 'Content-Type': 'text/html' }
                    });
                });
        });
}

// Queue requests for background sync
function queueForSync(request) {
    return request.clone().json()
        .then((data) => {
            // Store in IndexedDB for later sync
            return storeOfflineData(request.url, request.method, data);
        })
        .then(() => {
            // Return immediate response indicating queued
            return new Response(JSON.stringify({
                success: true,
                message: 'Request queued for sync when online',
                queued: true
            }), {
                headers: { 'Content-Type': 'application/json' }
            });
        })
        .catch(() => {
            // Fallback response
            return new Response(JSON.stringify({
                success: false,
                message: 'Offline - request will be synced when online',
                queued: true
            }), {
                headers: { 'Content-Type': 'application/json' }
            });
        });
}

// Store offline data in IndexedDB
function storeOfflineData(url, method, data) {
    return new Promise((resolve) => {
        const request = indexedDB.open('EA_CRM_Offline', 1);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offline_requests')) {
                const store = db.createObjectStore('offline_requests', { keyPath: 'id', autoIncrement: true });
                store.createIndex('url', 'url', { unique: false });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
        
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['offline_requests'], 'readwrite');
            const store = transaction.objectStore('offline_requests');
            
            const offlineRequest = {
                url: url,
                method: method,
                data: data,
                timestamp: Date.now()
            };
            
            const addRequest = store.add(offlineRequest);
            addRequest.onsuccess = () => resolve();
        };
    });
}

// Create offline response for API requests
function createOfflineResponse(request) {
    const url = new URL(request.url);
    
    // Return appropriate offline data based on endpoint
    if (url.pathname.includes('/api/chat/messages')) {
        return new Response(JSON.stringify({
            messages: [],
            offline: true,
            message: 'Messages will be loaded when online'
        }), {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    if (url.pathname.includes('/api/tasks')) {
        return new Response(JSON.stringify({
            tasks: [],
            offline: true,
            message: 'Tasks will be loaded when online'
        }), {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    return new Response(JSON.stringify({
        offline: true,
        message: 'Data will be available when online'
    }), {
        headers: { 'Content-Type': 'application/json' }
    });
}

// Check if request is for API endpoint
function isApiRequest(pathname) {
    return pathname.startsWith('/production/api/') || 
           pathname.startsWith('/api/') ||
           API_CACHE_PATTERNS.some(pattern => pathname.includes(pattern));
}

// Check if request is for static file
function isStaticFile(pathname) {
    return pathname.startsWith('/static/') ||
           pathname.includes('.css') ||
           pathname.includes('.js') ||
           pathname.includes('.png') ||
           pathname.includes('.jpg') ||
           pathname.includes('.ico') ||
           pathname.includes('.woff') ||
           pathname.includes('.woff2');
}

// Background sync event
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'sync-offline-data') {
        event.waitUntil(syncOfflineData());
    }
});

// Sync offline data when connection is restored
function syncOfflineData() {
    return new Promise((resolve) => {
        const request = indexedDB.open('EA_CRM_Offline', 1);
        
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['offline_requests'], 'readwrite');
            const store = transaction.objectStore('offline_requests');
            const index = store.index('timestamp');
            
            const getAllRequest = index.getAll();
            
            getAllRequest.onsuccess = () => {
                const offlineRequests = getAllRequest.result;
                
                if (offlineRequests.length === 0) {
                    resolve();
                    return;
                }
                
                console.log(`Syncing ${offlineRequests.length} offline requests`);
                
                // Process requests in order
                const syncPromises = offlineRequests.map((offlineRequest) => {
                    return fetch(offlineRequest.url, {
                        method: offlineRequest.method,
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Offline-Sync': 'true'
                        },
                        body: JSON.stringify(offlineRequest.data)
                    })
                    .then((response) => {
                        if (response.ok) {
                            // Remove from offline storage
                            return store.delete(offlineRequest.id);
                        }
                        throw new Error('Sync failed');
                    })
                    .catch((error) => {
                        console.error('Failed to sync request:', error);
                        // Keep in storage for next sync attempt
                    });
                });
                
                Promise.all(syncPromises)
                    .then(() => {
                        console.log('Offline sync completed');
                        resolve();
                    })
                    .catch((error) => {
                        console.error('Offline sync failed:', error);
                        resolve();
                    });
            };
        };
    });
}

// Push notification event
self.addEventListener('push', (event) => {
    console.log('Push notification received');
    
    let notificationData = {
        title: 'EA CRM',
        body: 'You have a new notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        data: {
            url: '/production/notifications'
        }
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
        } catch (error) {
            console.error('Error parsing push data:', error);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            data: notificationData.data,
            actions: [
                {
                    action: 'view',
                    title: 'View',
                    icon: '/static/images/view-icon.png'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ],
            requireInteraction: true
        })
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view' || event.action === '') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/production/dashboard')
        );
    }
});

// Message event for communication with main thread
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'SYNC_OFFLINE_DATA') {
        event.waitUntil(syncOfflineData());
    }
}); 