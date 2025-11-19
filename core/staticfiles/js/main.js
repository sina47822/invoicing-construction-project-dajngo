/**
 * Main JavaScript file for Project Management System
 * Handles global application functionality
 * Version: 1.0.0
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize main application components
    MainApp.init();
    
    // Initialize sidebar functionality
    Sidebar.init();
    
    // Initialize topbar functionality
    Topbar.init();
    
    // Initialize content loading
    ContentLoader.init();
    
    // Initialize keyboard shortcuts
    KeyboardShortcuts.init();
    
    // Initialize error handling
    ErrorHandler.init();
    
    console.log('Main application initialized');
});

// Main Application Namespace
const MainApp = {
    // Application configuration
    config: {
        debug: false, // Set to true in development
        apiBase: '/api/',
        maxRetries: 3,
        retryDelay: 1000,
        version: '1.0.0'
    },

    // State management
    state: {
        currentUser: null,
        activeProject: null,
        isLoading: false,
        lastActivity: null
    },

    // Initialize the application
    init() {
        this.loadUserData();
        this.setupEventListeners();
        this.startActivityTracking();
        this.initializePWA();
        
        // Check for updates
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }
        
        // Set up offline detection
        this.setupOfflineDetection();
        
        // Initialize analytics (if available)
        if (typeof gtag !== 'undefined') {
            this.initAnalytics();
        }
    },

    // Load user data from session or API
    loadUserData() {
        // Try to get user info from meta tags or data attributes
        const userMeta = document.querySelector('meta[name="current-user"]');
        if (userMeta) {
            try {
                this.state.currentUser = JSON.parse(userMeta.content);
            } catch (e) {
                console.warn('Failed to parse user data:', e);
            }
        }

        // Update UI with user data
        this.updateUserInterface();
    },

    // Setup global event listeners
    setupEventListeners() {
        // Global form submission handler
        document.addEventListener('submit', this.handleFormSubmission.bind(this));
        
        // Global AJAX error handler
        window.addEventListener('error', this.handleGlobalError.bind(this));
        window.addEventError('unhandledrejection', this.handleGlobalError.bind(this));
        
        // Window resize handler
        window.addEventListener('resize', this.handleWindowResize.bind(this));
        
        // Visibility change handler (for analytics)
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Before unload handler
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
        
        // Online/offline handlers
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
    },

    // Handle form submissions globally
    handleFormSubmission(event) {
        const form = event.target;
        const isAjaxForm = form.classList.contains('ajax-form') || 
                          form.hasAttribute('data-ajax');
        
        if (!isAjaxForm) return;
        
        event.preventDefault();
        
        // Mark form as submitting
        form.classList.add('submitting');
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>در حال ارسال...';
        }

        // Validate form
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            form.classList.remove('submitting');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
            return;
        }

        // Prepare form data
        const formData = new FormData(form);
        const url = form.action || form.getAttribute('data-action') || window.location.href;
        const method = (form.method || 'post').toUpperCase();
        
        // Add CSRF token if present
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken.value);
        }

        // Make AJAX request
        ProjectUtils.makeAjaxRequest(url, {
            method: method,
            body: formData,
            timeout: 30000,
            showLoading: false,
            loadingTarget: form.getAttribute('data-loading-target') || null
        })
        .then(response => {
            // Handle success
            const successCallback = form.getAttribute('data-on-success');
            if (successCallback && typeof window[successCallback] === 'function') {
                window[successCallback](response);
            } else {
                this.handleFormSuccess(form, response);
            }
        })
        .catch(error => {
            // Handle error
            console.error('Form submission error:', error);
            const errorCallback = form.getAttribute('data-on-error');
            if (errorCallback && typeof window[errorCallback] === 'function') {
                window[errorCallback](error);
            } else {
                this.handleFormError(form, error);
            }
        })
        .finally(() => {
            // Reset form state
            form.classList.remove('submitting');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    },

    handleFormSuccess(form, response) {
        // Default success handling
        const message = response.data.message || 'عملیات با موفقیت انجام شد';
        ProjectUtils.showToast(message, 'success', {
            title: 'موفقیت',
            timeout: 4000
        });

        // Reset form if needed
        if (form.classList.contains('reset-on-success')) {
            form.reset();
            form.classList.remove('was-validated');
        }

        // Close modal if form is in modal
        const modal = form.closest('.modal');
        if (modal && form.classList.contains('modal-form')) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        }

        // Reload page if specified
        if (form.hasAttribute('data-reload-on-success')) {
            const delay = parseInt(form.getAttribute('data-reload-delay')) || 1000;
            setTimeout(() => {
                if (form.getAttribute('data-reload-url')) {
                    window.location.href = form.getAttribute('data-reload-url');
                } else {
                    window.location.reload();
                }
            }, delay);
        }

        // Trigger custom event
        form.dispatchEvent(new CustomEvent('form:success', {
            detail: { response, form }
        }));
    },

    handleFormError(form, error) {
        let message = 'خطا در انجام عملیات';
        
        if (error.xhr && error.xhr.status === 0) {
            message = 'عدم اتصال به اینترنت';
        } else if (error.xhr && error.xhr.status >= 400 && error.xhr.status < 500) {
            message = error.error?.message || 'خطای ورودی';
        } else if (error.xhr && error.xhr.status >= 500) {
            message = error.error?.message || 'خطای سرور';
        } else if (error.message) {
            message = error.message;
        }

        ProjectUtils.showToast(message, 'danger', {
            title: 'خطا',
            timeout: 6000
        });

        // Add specific field errors if available
        if (error.xhr && error.xhr.responseText) {
            try {
                const errors = JSON.parse(error.xhr.responseText);
                if (errors.errors && typeof errors.errors === 'object') {
                    Object.keys(errors.errors).forEach(fieldName => {
                        const field = form.querySelector(`[name="${fieldName}"]`);
                        if (field) {
                            ProjectUtils.showFieldError(field, errors.errors[fieldName].join(', '));
                            field.classList.add('is-invalid');
                        }
                    });
                }
            } catch (e) {
                // Ignore JSON parsing errors
            }
        }

        form.dispatchEvent(new CustomEvent('form:error', {
            detail: { error, form }
        }));
    },

    // Update UI based on user state
    updateUserInterface() {
        if (!this.state.currentUser) return;

        // Update user name in topbar
        const userNameElements = document.querySelectorAll('[data-user-name]');
        userNameElements.forEach(el => {
            el.textContent = this.state.currentUser.get_full_name || 
                           this.state.currentUser.username || 
                           'کاربر';
        });

        // Update user role-based visibility
        const roleBasedElements = document.querySelectorAll('[data-show-for-role]');
        roleBasedElements.forEach(el => {
            const requiredRole = el.getAttribute('data-show-for-role');
            const hasRole = this.state.currentUser.roles?.includes(requiredRole) || 
                          this.state.currentUser.is_superuser;
            
            el.style.display = hasRole ? '' : 'none';
        });

        // Update permissions
        const permissionElements = document.querySelectorAll('[data-permission]');
        permissionElements.forEach(el => {
            const requiredPermission = el.getAttribute('data-permission');
            const hasPermission = this.state.currentUser.permissions?.includes(requiredPermission);
            
            if (!hasPermission) {
                el.style.display = 'none';
                el.disabled = true;
            }
        });

        // Update user avatar if available
        if (this.state.currentUser.avatar) {
            const avatarElements = document.querySelectorAll('[data-user-avatar]');
            avatarElements.forEach(el => {
                el.src = this.state.currentUser.avatar;
                el.alt = this.state.currentUser.get_full_name || this.state.currentUser.username;
            });
        }
    },

    // Track user activity
    startActivityTracking() {
        let activityTimeout;
        
        const resetActivityTimer = () => {
            clearTimeout(activityTimeout);
            activityTimeout = setTimeout(() => {
                this.state.isActive = false;
                // Optional: show idle warning
                if (this.config.debug) {
                    console.log('User is idle');
                }
            }, 15 * 60 * 1000); // 15 minutes
            
            this.state.isActive = true;
            this.state.lastActivity = new Date().toISOString();
        };

        // Reset timer on user interaction
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetActivityTimer, true);
        });

        // Initial reset
        resetActivityTimer();

        // Track for analytics
        if (typeof gtag !== 'undefined') {
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    gtag('event', 'page_view', {
                        event_category: 'Engagement',
                        event_label: window.location.pathname
                    });
                }
            });
        }
    },

    // Handle window resize
    handleWindowResize() {
        // Update sidebar state on mobile
        if (window.innerWidth < 768) {
            Sidebar.close();
        } else {
            Sidebar.open();
        }
        
        // Update layout calculations
        LayoutManager.update();
    },

    // Handle visibility changes
    handleVisibilityChange() {
        if (document.hidden) {
            // Page is hidden
            this.state.isVisible = false;
        } else {
            // Page is visible
            this.state.isVisible = true;
            
            // Refresh data if needed
            if (this.state.needsRefresh) {
                ContentLoader.refresh();
                this.state.needsRefresh = false;
            }
        }
    },

    // Handle before unload
    handleBeforeUnload(event) {
        // Warn user if they have unsaved changes
        const unsavedForms = document.querySelectorAll('form:has(.form-control.dirty)');
        if (unsavedForms.length > 0) {
            event.preventDefault();
            event.returnValue = 'شما تغییرات ذخیره نشده دارید. آیا مطمئن هستید؟';
            return 'شما تغییرات ذخیره نشده دارید. آیا مطمئن هستید؟';
        }

        // Save application state
        if (this.config.debug) {
            console.log('Saving application state before unload');
        }
    },

    // Handle online status
    handleOnline() {
        if (this.config.debug) {
            console.log('Connection restored');
        }
        
        ProjectUtils.showToast('اتصال به اینترنت برقرار شد', 'success', {
            timeout: 3000
        });

        // Retry failed requests
        if (window.failedRequests && window.failedRequests.length > 0) {
            window.failedRequests.forEach(request => {
                // Retry logic here
            });
            window.failedRequests = [];
        }

        this.state.isOffline = false;
    },

    // Handle offline status
    handleOffline() {
        if (this.config.debug) {
            console.log('Connection lost');
        }
        
        ProjectUtils.showToast('عدم اتصال به اینترنت', 'warning', {
            timeout: 5000
        });

        this.state.isOffline = true;
    },

    // Initialize Progressive Web App features
    initializePWA() {
        if ('serviceWorker' in navigator && 'PushManager' in window) {
            // PWA is supported
            this.state.supportsPWA = true;
            
            // Request notification permission
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        console.log('Notification permission granted');
                    }
                });
            }
        }
    },

    // Register service worker
    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    if (this.config.debug) {
                        console.log('SW registered: ', registration);
                    }
                    
                    // Update service worker if available
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed') {
                                if (navigator.serviceWorker.controller) {
                                    // New content available, show reload prompt
                                    this.showUpdateAvailable(registration);
                                }
                            }
                        });
                    });
                })
                .catch(registrationError => {
                    console.log('SW registration failed: ', registrationError);
                });
        }
    },

    // Show update available prompt
    showUpdateAvailable(registration) {
        const updateAvailable = confirm('نسخه جدیدی از برنامه در دسترس است. آیا می‌خواهید آن را بارگیری کنید؟');
        if (updateAvailable) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
            window.location.reload();
        }
    },

    // Setup offline detection and queueing
    setupOfflineDetection() {
        // Create offline queue
        if (!window.offlineQueue) {
            window.offlineQueue = [];
        }

        // Check offline status on load
        this.state.isOffline = !navigator.onLine;
    },

    // Initialize Google Analytics
    initAnalytics() {
        // Set user properties
        if (this.state.currentUser) {
            gtag('set', 'user_id', this.state.currentUser.id);
            gtag('set', 'user_name', this.state.currentUser.username);
        }

        // Track initial page view
        gtag('config', 'GA_MEASUREMENT_ID', {
            page_title: document.title,
            page_path: window.location.pathname
        });

        // Track form submissions
        document.addEventListener('form:success', (e) => {
            gtag('event', 'form_submit', {
                event_category: 'Forms',
                event_label: e.target.getAttribute('name') || 'unnamed',
                value: 1
            });
        });

        document.addEventListener('form:error', (e) => {
            gtag('event', 'form_error', {
                event_category: 'Forms',
                event_label: e.target.getAttribute('name') || 'unnamed',
                value: 1
            });
        });
    },

    // Global error handler
    handleGlobalError(error) {
        if (this.config.debug) {
            console.error('Global error:', error);
        }

        // Don't show error toast for expected errors
        if (error.message && (
            error.message.includes('Failed to load resource') ||
            error.message.includes('Script error') ||
            error.filename?.includes('extensions::')
        )) {
            return;
        }

        // Show user-friendly error
        let message = 'خطای غیرمنتظره‌ای رخ داد';
        if (error.message && error.message.includes('Network')) {
            message = 'مشکل در اتصال به شبکه';
        } else if (error.message && error.message.length < 100) {
            message = error.message;
        }

        ProjectUtils.showToast(message, 'danger', {
            title: 'خطای سیستم',
            timeout: 7000
        });

        // Send error to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'javascript_error', {
                event_category: 'Errors',
                event_label: error.message?.substring(0, 100) || 'Unknown error',
                value: 1
            });
        }

        return false; // Prevent default error handling
    },

    // Log application events
    logEvent(eventName, data = {}) {
        const eventData = {
            timestamp: new Date().toISOString(),
            userId: this.state.currentUser?.id || 'anonymous',
            page: window.location.pathname,
            ...data
        };

        if (this.config.debug) {
            console.log(`[App Event] ${eventName}:`, eventData);
        }

        // Send to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', eventName, eventData);
        }

        // Trigger custom event
        document.dispatchEvent(new CustomEvent(`app:${eventName}`, {
            detail: eventData
        }));
    },

    // Show global loading indicator
    showGlobalLoading(message = 'در حال بارگیری...') {
        this.state.isLoading = true;
        
        // Remove existing loading indicator
        const existing = document.getElementById('global-loading');
        if (existing) {
            existing.remove();
        }

        const loadingHTML = `
            <div id="global-loading" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" 
                 style="background: rgba(255, 255, 255, 0.9); z-index: 9999; backdrop-filter: blur(3px);">
                <div class="text-center p-4 bg-white rounded shadow">
                    <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;" role="status">
                        <span class="visually-hidden">${message}</span>
                    </div>
                    <div class="fw-semibold text-primary">${message}</div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // Focus management
        const loadingEl = document.getElementById('global-loading');
        loadingEl.setAttribute('role', 'status');
        loadingEl.setAttribute('aria-live', 'polite');
        loadingEl.setAttribute('aria-label', message);
    },

    hideGlobalLoading() {
        this.state.isLoading = false;
        const loadingEl = document.getElementById('global-loading');
        if (loadingEl) {
            loadingEl.remove();
        }
    },

    // Check if user has specific permission
    hasPermission(permission) {
        if (!this.state.currentUser) return false;
        return this.state.currentUser.is_superuser || 
               (this.state.currentUser.permissions && 
                this.state.currentUser.permissions.includes(permission));
    },

    // Check if user has specific role
    hasRole(role) {
        if (!this.state.currentUser) return false;
        return this.state.currentUser.is_superuser || 
               (this.state.currentUser.roles && 
                this.state.currentUser.roles.includes(role));
    }
};

// Sidebar Management
const Sidebar = {
    init() {
        this.mobileToggle = document.querySelector('[data-toggle-sidebar]');
        this.sidebar = document.querySelector('.sidebar');
        this.overlay = document.getElementById('sidebar-overlay');
        
        this.bindEvents();
        this.updateState();
    },

    bindEvents() {
        if (this.mobileToggle) {
            this.mobileToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggle();
            });
        }

        // Overlay click to close
        if (this.overlay) {
            this.overlay.addEventListener('click', () => {
                this.close();
            });
        }

        // Sidebar links
        const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Close sidebar on mobile after navigation
                if (window.innerWidth < 768) {
                    setTimeout(() => this.close(), 300);
                }
                
                // Update active state
                this.updateActiveLink(link);
            });
        });

        // Window resize handler
        window.addEventListener('resize', () => {
            this.updateState();
        });
    },

    toggle() {
        if (this.sidebar.classList.contains('active')) {
            this.close();
        } else {
            this.open();
        }
    },

    open() {
        this.sidebar.classList.add('active');
        document.body.classList.add('sidebar-open');
        
        if (this.overlay && window.innerWidth < 768) {
            this.overlay.classList.remove('d-none');
        }

        // Focus management
        const firstLink = this.sidebar.querySelector('.nav-link');
        if (firstLink) {
            firstLink.focus();
        }

        // Announce for screen readers
        this.announce('نوار کناری باز شد');
        
        MainApp.logEvent('sidebar_opened');
    },

    close() {
        this.sidebar.classList.remove('active');
        document.body.classList.remove('sidebar-open');
        
        if (this.overlay) {
            this.overlay.classList.add('d-none');
        }

        // Focus management
        const toggle = this.mobileToggle || document.querySelector('.navbar-brand');
        if (toggle) {
            toggle.focus();
        }

        this.announce('نوار کناری بسته شد');
        
        MainApp.logEvent('sidebar_closed');
    },

    updateState() {
        if (window.innerWidth >= 768) {
            this.sidebar.classList.add('active');
            document.body.classList.add('sidebar-open');
            if (this.overlay) {
                this.overlay.classList.add('d-none');
            }
        } else {
            this.sidebar.classList.remove('active');
            document.body.classList.remove('sidebar-open');
        }
    },

    updateActiveLink(activeLink) {
        // Remove active class from all links
        const allLinks = document.querySelectorAll('.sidebar .nav-link');
        allLinks.forEach(link => link.classList.remove('active'));

        // Add active class to clicked link
        activeLink.classList.add('active');

        // Update URL if it's a navigation link
        if (activeLink.href && activeLink.href !== '#') {
            history.replaceState(null, null, activeLink.href);
        }
    },

    announce(message) {
        // Create or update live region for screen readers
        let liveRegion = document.getElementById('sidebar-live-region');
        if (!liveRegion) {
            liveRegion = document.createElement('div');
            liveRegion.id = 'sidebar-live-region';
            liveRegion.className = 'visually-hidden';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            document.body.appendChild(liveRegion);
        }
        
        liveRegion.textContent = message;
    }
};

// Topbar Management
const Topbar = {
    init() {
        this.userMenu = document.querySelector('[data-user-menu]');
        this.searchInput = document.querySelector('.topbar-search');
        this.notifications = document.querySelector('[data-notifications]');
        
        this.bindEvents();
        this.updateNotifications();
    },

    bindEvents() {
        // User menu toggle
        if (this.userMenu) {
            this.userMenu.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const dropdown = this.userMenu.parentNode.querySelector('.dropdown-menu');
                if (dropdown) {
                    const isOpen = dropdown.classList.contains('show');
                    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                        menu.classList.remove('show');
                        menu.parentNode.classList.remove('show');
                    });
                    
                    if (!isOpen) {
                        dropdown.classList.add('show');
                        this.userMenu.parentNode.classList.add('show');
                    }
                }
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!this.userMenu.contains(e.target)) {
                    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                        menu.classList.remove('show');
                        menu.parentNode.classList.remove('show');
                    });
                }
            });
        }

        // Search functionality
        if (this.searchInput) {
            this.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.performSearch(this.searchInput.value);
                }
            });

            // Clear search
            const clearBtn = this.searchInput.parentNode.querySelector('.clear-search');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.searchInput.value = '';
                    this.searchInput.focus();
                    this.performSearch('');
                });
            }
        }

        // Notification handling
        if (this.notifications) {
            this.notifications.addEventListener('click', (e) => {
                e.preventDefault();
                this.markNotificationsAsRead();
                this.updateNotifications();
            });
        }
    },

    performSearch(query) {
        if (!query.trim()) {
            // Clear search results
            const resultsContainer = document.querySelector('.search-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = '';
                resultsContainer.classList.add('d-none');
            }
            return;
        }

        // Show loading
        const resultsContainer = document.querySelector('.search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';
            resultsContainer.classList.remove('d-none');
        }

        // Perform search (replace with actual search API)
        ProjectUtils.makeAjaxRequest('/api/search/', {
            method: 'POST',
            data: { query: query },
            timeout: 5000
        })
        .then(response => {
            this.displaySearchResults(response.data, query);
        })
        .catch(error => {
            console.error('Search error:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<div class="text-danger">خطا در جستجو</div>';
            }
        });
    },

    displaySearchResults(results, query) {
        const resultsContainer = document.querySelector('.search-results');
        if (!resultsContainer) return;

        if (results && results.length > 0) {
            const resultsHTML = results.map(result => `
                <div class="search-result p-2 border-bottom">
                    <a href="${result.url}" class="text-decoration-none">
                        <div class="fw-semibold">${result.title}</div>
                        <small class="text-muted">${result.description}</small>
                    </a>
                </div>
            `).join('');

            resultsContainer.innerHTML = `
                <div class="p-2 border-bottom">
                    <strong>${results.length} نتیجه برای "${query}"</strong>
                </div>
                ${resultsHTML}
            `;
        } else {
            resultsContainer.innerHTML = `
                <div class="p-3 text-center text-muted">
                    <div class="mb-2">هیچ نتیجه‌ای یافت نشد</div>
                    <small>"${query}"</small>
                </div>
            `;
        }
    },

    updateNotifications() {
        // Fetch notifications (replace with actual API call)
        if (!MainApp.state.currentUser) return;

        ProjectUtils.makeAjaxRequest('/api/notifications/', {
            method: 'GET'
        })
        .then(response => {
            this.renderNotifications(response.data.notifications || []);
        })
        .catch(error => {
            console.error('Failed to fetch notifications:', error);
        });
    },

    renderNotifications(notifications) {
        const notificationContainer = document.querySelector('.notifications-list');
        if (!notificationContainer) return;

        if (notifications.length === 0) {
            notificationContainer.innerHTML = `
                <div class="p-3 text-center text-muted">
                    <i class="bi bi-bell fs-1 mb-2"></i>
                    <div>هیچ اعلانی وجود ندارد</div>
                </div>
            `;
            return;
        }

        const unreadCount = notifications.filter(n => !n.read).length;
        const badge = document.querySelector('[data-notification-count]');
        if (badge) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = unreadCount > 0 ? '' : 'none';
        }

        const notificationsHTML = notifications.map(notification => {
            const isUnread = !notification.read;
            const iconClass = this.getNotificationIcon(notification.type);
            
            return `
                <a href="${notification.url || '#'}" class="notification-item p-3 border-bottom 
                    ${isUnread ? 'bg-light' : ''} text-decoration-none" 
                   data-notification-id="${notification.id}">
                    <div class="d-flex align-items-start">
                        <div class="notification-icon me-3 ${iconClass}">
                            <i class="bi ${iconClass.icon}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start mb-1">
                                <div class="fw-semibold">${notification.title}</div>
                                <small class="text-muted ms-2">${this.formatTime(notification.timestamp)}</small>
                            </div>
                            <div class="notification-message">${notification.message}</div>
                            ${isUnread ? '<div class="unread-indicator"></div>' : ''}
                        </div>
                    </div>
                </a>
            `;
        }).join('');

        notificationContainer.innerHTML = notificationsHTML;
    },

    getNotificationIcon(type) {
        const icons = {
            info: { class: 'text-info', icon: 'bi-info-circle' },
            success: { class: 'text-success', icon: 'bi-check-circle' },
            warning: { class: 'text-warning', icon: 'bi-exclamation-triangle' },
            error: { class: 'text-danger', icon: 'bi-x-circle' },
            project: { class: 'text-primary', icon: 'bi-building' },
            task: { class: 'text-primary', icon: 'bi-list-task' },
            default: { class: 'text-muted', icon: 'bi-bell' }
        };
        
        return icons[type] || icons.default;
    },

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);

        if (diffInHours < 1) {
            return 'همین الان';
        } else if (diffInHours < 24) {
            return `${Math.floor(diffInHours)} ساعت پیش`;
        } else if (diffInHours < 168) {
            return `${Math.floor(diffInHours / 24)} روز پیش`;
        } else {
            return date.toLocaleDateString('fa-IR');
        }
    },

    markNotificationsAsRead() {
        ProjectUtils.makeAjaxRequest('/api/notifications/read/', {
            method: 'POST'
        })
        .then(() => {
            // Update UI
            const unreadItems = document.querySelectorAll('.notification-item.bg-light');
            unreadItems.forEach(item => {
                item.classList.remove('bg-light');
                const indicator = item.querySelector('.unread-indicator');
                if (indicator) {
                    indicator.remove();
                }
            });

            const badge = document.querySelector('[data-notification-count]');
            if (badge) {
                badge.style.display = 'none';
            }

            MainApp.logEvent('notifications_read', {
                count: unreadItems.length
            });
        })
        .catch(error => {
            console.error('Failed to mark notifications as read:', error);
        });
    }
};

// Content Loader
const ContentLoader = {
    init() {
        this.cache = new Map();
        this.loadingStates = new Set();
        
        // Intercept navigation links for AJAX loading
        document.addEventListener('click', this.handleNavigationClick.bind(this));
        
        // Handle browser back/forward buttons
        window.addEventListener('popstate', this.handlePopState.bind(this));
        
        // Initialize infinite scroll if needed
        this.initInfiniteScroll();
    },

    handleNavigationClick(event) {
        const link = event.target.closest('a');
        if (!link || event.ctrlKey || event.metaKey || event.button !== 0) return;
        
        if (link.hasAttribute('data-no-ajax') || 
            link.href.indexOf('#') !== -1 || 
            link.target === '_blank' ||
            !link.href.startsWith(window.location.origin)) {
            return;
        }

        event.preventDefault();
        const url = new URL(link.href);
        
        if (url.pathname !== window.location.pathname) {
            this.loadContent(url.pathname + url.search, {
                method: 'GET',
                pushState: true,
                link: link
            });
        }
    },

    loadContent(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            data: null,
            pushState: false,
            replaceState: false,
            showLoading: true,
            cache: true,
            timeout: 10000,
            link: null
        };

        const config = { ...defaultOptions, ...options };
        
        // Don't load if already loading this URL
        const loadingKey = `${config.method}:${url}`;
        if (this.loadingStates.has(loadingKey)) {
            if (config.debug) console.log('Already loading:', url);
            return Promise.reject(new Error('Already loading this URL'));
        }

        this.loadingStates.add(loadingKey);

        if (config.showLoading) {
            MainApp.showGlobalLoading('در حال بارگیری محتوا...');
        }

        const requestPromise = ProjectUtils.makeAjaxRequest(url, {
            method: config.method,
            data: config.data,
            responseType: 'html',
            timeout: config.timeout,
            showLoading: false
        })
        .then(response => {
            if (config.cache) {
                this.cache.set(url, response.data);
            }

            // Update content
            this.updateContent(response.data, url, config);

            // Update browser history
            if (config.pushState) {
                history.pushState({ url: url }, '', url);
            } else if (config.replaceState) {
                history.replaceState({ url: url }, '', url);
            }

            // Update active navigation
            if (config.link) {
                Sidebar.updateActiveLink(config.link);
            }

            // Update page title
            const titleMatch = response.data.match(/<title>(.*?)<\/title>/i);
            if (titleMatch) {
                document.title = titleMatch[1];
            }

            return response;
        })
        .catch(error => {
            console.error('Content load error:', error);
            
            // Show error page or fallback
            this.showErrorPage(error, url);
            
            throw error;
        })
        .finally(() => {
            this.loadingStates.delete(loadingKey);
            if (config.showLoading) {
                MainApp.hideGlobalLoading();
            }
        });

        return requestPromise;
    },

    updateContent(html, url, config) {
        // Parse HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update main content
        const newMain = doc.querySelector('main');
        const currentMain = document.querySelector('main');
        if (newMain && currentMain) {
            currentMain.innerHTML = newMain.innerHTML;
            
            // Re-initialize components in new content
            this.reinitializeComponents(currentMain);
        }

        // Update title
        const newTitle = doc.querySelector('title');
        if (newTitle) {
            document.title = newTitle.textContent;
        }

        // Update meta tags if needed
        const newMeta = doc.querySelector('meta[name="description"]');
        if (newMeta) {
            let meta = document.querySelector('meta[name="description"]');
            if (!meta) {
                meta = document.createElement('meta');
                meta.name = 'description';
                document.head.appendChild(meta);
            }
            meta.content = newMeta.content;
        }

        // Scroll to top
        if (!config.preserveScroll) {
            window.scrollTo(0, 0);
        }

        // Trigger content loaded event
        document.dispatchEvent(new CustomEvent('content:loaded', {
            detail: { url, html, config }
        }));
    },

    reinitializeComponents(container) {
        // Reinitialize form validation
        ProjectUtils.initFormValidation();
        
        // Reinitialize tooltips and popovers
        ProjectUtils.initTooltips();
        ProjectUtils.initPopovers();
        
        // Reinitialize file uploads
        ProjectUtils.initFileUpload();
        
        // Reinitialize any custom components
        if (typeof reinitializeCharts === 'function') {
            reinitializeCharts(container);
        }
        
        if (typeof reinitializeMaps === 'function') {
            reinitializeMaps(container);
        }
    },

    handlePopState(event) {
        if (event.state && event.state.url) {
            this.loadContent(event.state.url, {
                pushState: false,
                showLoading: true,
                preserveScroll: false
            });
        }
    },

    showErrorPage(error, url) {
        const errorHTML = `
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6 text-center">
                        <div class="mb-4">
                            <i class="bi bi-exclamation-triangle display-1 text-warning"></i>
                        </div>
                        <h2 class="mb-3">خطا در بارگیری محتوا</h2>
                        <p class="text-muted mb-4">
                            ${error.xhr?.status === 404 ? 
                                'صفحه مورد نظر یافت نشد.' : 
                                'خطایی در بارگیری محتوا رخ داد. لطفاً دوباره تلاش کنید.'
                            }
                        </p>
                        <div class="d-flex gap-2 justify-content-center flex-wrap">
                            <button class="btn btn-primary" onclick="window.location.reload()">
                                <i class="bi bi-arrow-clockwise"></i> تلاش مجدد
                            </button>
                            <a href="${url}" class="btn btn-outline-secondary">
                                <i class="bi bi-house"></i> بازگشت به صفحه
                            </a>
                            ${error.xhr?.status === 404 ? 
                                '<a href="/" class="btn btn-outline-secondary"><i class="bi bi-house-door"></i> صفحه اصلی</a>' : 
                                ''
                            }
                        </div>
                        ${MainApp.config.debug ? 
                            `<div class="mt-4 p-3 bg-light rounded">
                                <small class="text-muted">
                                    <strong>جزئیات خطا:</strong><br>
                                    Status: ${error.xhr?.status || 'Unknown'}<br>
                                    URL: ${url}<br>
                                    Message: ${error.message || 'No additional info'}
                                </small>
                            </div>` : 
                            ''
                        }
                    </div>
                </div>
            </div>
        `;
        
        const mainContent = document.querySelector('main');
        if (mainContent) {
            mainContent.innerHTML = errorHTML;
        }
        
        MainApp.logEvent('content_error', {
            url: url,
            status: error.xhr?.status,
            error: error.message
        });
    },

    initInfiniteScroll() {
        const infiniteScrollContainers = document.querySelectorAll('[data-infinite-scroll]');
        
        infiniteScrollContainers.forEach(container => {
            const url = container.getAttribute('data-infinite-scroll');
            const threshold = parseInt(container.getAttribute('data-threshold')) || 100;
            let isLoading = false;
            let page = 1;
            
            const loadMore = () => {
                if (isLoading) return;
                
                const rect = container.getBoundingClientRect();
                if (rect.bottom - window.innerHeight < threshold) {
                    isLoading = true;
                    this.loadMoreContent(container, url, page)
                        .then(() => {
                            page++;
                            isLoading = false;
                        })
                        .catch(error => {
                            console.error('Infinite scroll error:', error);
                            isLoading = false;
                        });
                }
            };
            
            // Use IntersectionObserver for better performance
            if ('IntersectionObserver' in window) {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            loadMore();
                        }
                    });
                }, { threshold: 0.1 });
                
                observer.observe(container);
            } else {
                // Fallback to scroll event
                window.addEventListener('scroll', loadMore, { passive: true });
            }
        });
    },

    loadMoreContent(container, url, page) {
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'text-center p-3';
        loadingIndicator.innerHTML = `
            <div class="spinner-border spinner-border-sm text-primary"></div>
            <small class="text-muted">در حال بارگیری...</small>
        `;
        container.appendChild(loadingIndicator);

        return ProjectUtils.makeAjaxRequest(`${url}?page=${page}`, {
            method: 'GET'
        })
        .then(response => {
            loadingIndicator.remove();
            
            if (response.data && response.data.html) {
                container.insertAdjacentHTML('beforeend', response.data.html);
                
                // Reinitialize components in new content
                this.reinitializeComponents(container);
                
                // Check if there's more content
                if (!response.data.has_next) {
                    // Remove infinite scroll attribute to stop loading
                    container.removeAttribute('data-infinite-scroll');
                }
            }
        })
        .catch(error => {
            loadingIndicator.remove();
            console.error('Failed to load more content:', error);
            
            // Show error and stop infinite scroll
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-warning text-center';
            errorDiv.innerHTML = `
                <i class="bi bi-exclamation-triangle"></i>
                خطا در بارگیری محتوا
            `;
            container.appendChild(errorDiv);
            container.removeAttribute('data-infinite-scroll');
        });
    },

    // Get content from cache
    getCachedContent(url) {
        if (this.cache.has(url)) {
            return Promise.resolve({ data: this.cache.get(url) });
        }
        return null;
    },

    // Clear cache
    clearCache() {
        this.cache.clear();
        console.log('Content cache cleared');
    },

    refresh() {
        MainApp.state.needsRefresh = true;
        this.clearCache();
        
        // Reload current page
        if (history.state && history.state.url) {
            this.loadContent(history.state.url, { replaceState: true });
        }
    }
};

// Keyboard Shortcuts
const KeyboardShortcuts = {
    init() {
        this.shortcuts = new Map([
            ['Escape', this.handleEscape],
            ['Control+Shift+R', this.handleHardRefresh],
            ['Alt+1', () => window.location.href = '/'],
            ['Alt+2', () => Sidebar.toggle()],
            ['Control+F', this.handleSearchFocus],
            ['Control+P', this.handlePrint],
            ['F5', this.handleRefresh],
            ['Control+S', this.handleSave]
        ]);

        // Global keydown listener
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Add visual indicator
        this.addShortcutsIndicator();
    },

    handleKeyDown(event) {
        // Don't interfere with input fields
        if (event.target.tagName === 'INPUT' || 
            event.target.tagName === 'TEXTAREA' || 
            event.target.isContentEditable ||
            event.target.closest('.modal')) {
            return;
        }

        // Build key combination
        let keyCombo = '';
        if (event.ctrlKey) keyCombo += 'Control+';
        if (event.altKey) keyCombo += 'Alt+';
        if (event.shiftKey) keyCombo += 'Shift+';
        if (event.metaKey) keyCombo += 'Meta+';
        keyCombo += event.key;

        // Check if shortcut exists
        if (this.shortcuts.has(keyCombo)) {
            event.preventDefault();
            event.stopPropagation();
            
            const handler = this.shortcuts.get(keyCombo);
            if (typeof handler === 'function') {
                handler.call(this, event);
            }
            
            MainApp.logEvent('keyboard_shortcut', {
                shortcut: keyCombo,
                target: document.activeElement.tagName
            });
        }
    },

    handleEscape(event) {
        // Close modals
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
            return;
        }

        // Close dropdowns
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
            menu.parentNode.classList.remove('show');
        });

        // Close sidebar on mobile
        if (window.innerWidth < 768 && Sidebar.sidebar.classList.contains('active')) {
            Sidebar.close();
        }

        // Clear search
        const searchInput = document.querySelector('.search-input:focus');
        if (searchInput) {
            searchInput.blur();
        }
    },

    handleHardRefresh(event) {
        // Hard refresh (bypass cache)
        window.location.reload(true);
    },

    handleSearchFocus(event) {
        const searchInput = document.querySelector('.topbar-search, .search-input');
        if (searchInput) {
            event.preventDefault();
            searchInput.focus();
        }
    },

    handlePrint(event) {
        event.preventDefault();
        window.print();
    },

    handleRefresh(event) {
        event.preventDefault();
        ContentLoader.refresh();
    },

    handleSave(event) {
        event.preventDefault();
        
        // Save active form or show save dialog
        const activeForm = document.querySelector('form:not([hidden]):not(.d-none)');
        if (activeForm && activeForm.checkValidity()) {
            activeForm.dispatchEvent(new Event('submit'));
        } else {
            ProjectUtils.showToast('هیچ فرم ذخیره‌سازی در دسترس نیست', 'info');
        }
    },

    addShortcutsIndicator() {
        // Add keyboard shortcuts help
        const indicator = document.createElement('div');
        indicator.id = 'shortcuts-indicator';
        indicator.className = 'position-fixed bottom-0 end-0 p-3';
        indicator.style.cssText = `
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border-radius: 0.5rem 0.5rem 0 0;
            font-size: 0.75rem;
            z-index: 1000;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        indicator.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-keyboard me-1"></i>
                <span>میانبرهای کیبورد</span>
                <button class="btn-close btn-close-white ms-2" style="opacity: 0.7;"></button>
            </div>
        `;
        
        document.body.appendChild(indicator);
        
        // Show on hover
        indicator.addEventListener('mouseenter', () => {
            indicator.style.opacity = '1';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (e.clientX < 100 && e.clientY > window.innerHeight - 100) {
                indicator.style.opacity = '1';
            } else {
                indicator.style.opacity = '0';
            }
        });
        
        // Toggle shortcuts help
        indicator.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleShortcutsHelp();
        });
        
        // Close button
        const closeBtn = indicator.querySelector('.btn-close');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleShortcutsHelp();
        });
    },

    toggleShortcutsHelp() {
        let helpModal = document.getElementById('shortcuts-help-modal');
        
        if (helpModal) {
            // Close modal
            const modalInstance = bootstrap.Modal.getInstance(helpModal);
            if (modalInstance) {
                modalInstance.hide();
            }
        } else {
            // Create modal
            helpModal = document.createElement('div');
            helpModal.id = 'shortcuts-help-modal';
            helpModal.className = 'modal fade';
            helpModal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">میانبرهای کیبورد</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>میانبر</th>
                                            <th>عمل</th>
                                            <th>توضیحات</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Esc</td>
                                            <td>بستن</td>
                                            <td>بستن مودال‌ها، دراپ‌داون‌ها و نوار کناری</td>
                                        </tr>
                                        <tr>
                                            <td>Alt + 1</td>
                                            <td>صفحه اصلی</td>
                                            <td>رفتن به داشبورد</td>
                                        </tr>
                                        <tr>
                                            <td>Alt + 2</td>
                                            <td>نوار کناری</td>
                                            <td>باز و بسته کردن نوار کناری</td>
                                        </tr>
                                        <tr>
                                            <td>Ctrl + F</td>
                                            <td>جستجو</td>
                                            <td>تمرکز روی فیلد جستجو</td>
                                        </tr>
                                        <tr>
                                            <td>Ctrl + P</td>
                                            <td>چاپ</td>
                                            <td>چاپ صفحه فعلی</td>
                                        </tr>
                                        <tr>
                                            <td>F5</td>
                                            <td>رفرش</td>
                                            <td>بارگیری مجدد محتوا</td>
                                        </tr>
                                        <tr>
                                            <td>Ctrl + S</td>
                                            <td>ذخیره</td>
                                            <td>ذخیره فرم فعال</td>
                                        </tr>
                                        <tr>
                                            <td>Ctrl + Shift + R</td>
                                            <td>رفرش سخت</td>
                                            <td>بارگیری مجدد بدون استفاده از کش</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="alert alert-info mt-3">
                                <i class="bi bi-info-circle"></i>
                                <strong>نکته:</strong> میانبرها فقط زمانی کار می‌کنند که فوکوس روی فیلدهای ورودی نباشد.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(helpModal);
            
            // Show modal
            const modal = new bootstrap.Modal(helpModal);
            modal.show();
            
            // Cleanup on hide
            helpModal.addEventListener('hidden.bs.modal', () => {
                if (helpModal.parentNode) {
                    helpModal.parentNode.removeChild(helpModal);
                }
            }, { once: true });
        }
    }
};

// Layout Manager
const LayoutManager = {
    init() {
        this.update();
        window.addEventListener('resize', () => this.update());
        window.addEventListener('orientationchange', () => this.update());
    },

    update() {
        this.updateSidebar();
        this.updateTopbar();
        this.updateMainContent();
        this.updateFooter();
        this.handleMobileLayout();
    },

    updateSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        const isMobile = window.innerWidth < 768;
        const isTablet = window.innerWidth < 992;

        if (isMobile) {
            sidebar.classList.remove('d-none');
            sidebar.style.width = '280px';
        } else if (isTablet) {
            sidebar.style.width = '250px';
        } else {
            sidebar.style.width = '280px';
        }

        // Update sidebar position
        const sidebarRect = sidebar.getBoundingClientRect();
        if (sidebarRect.right > window.innerWidth) {
            sidebar.style.right = '0';
            sidebar.style.left = 'auto';
        }
    },

    updateTopbar() {
        const topbar = document.querySelector('.topbar');
        if (!topbar) return;

        // Adjust topbar padding based on fixed positioning
        if (topbar.classList.contains('fixed-top')) {
            document.body.style.paddingTop = topbar.offsetHeight + 'px';
        }
    },

    updateMainContent() {
        const main = document.querySelector('main');
        if (!main) return;

        // Adjust main content padding
        const topbarHeight = document.querySelector('.topbar')?.offsetHeight || 0;
        const sidebarWidth = document.querySelector('.sidebar')?.offsetWidth || 0;
        
        main.style.paddingTop = topbarHeight + 'px';
        main.style.marginRight = window.innerWidth >= 768 ? sidebarWidth + 'px' : '0';
        
        // Ensure minimum height
        main.style.minHeight = `calc(100vh - ${topbarHeight + 56}px)`;
    },

    updateFooter() {
        const footer = document.querySelector('.footer');
        if (!footer || !document.body) return;

        // Sticky footer logic
        const bodyHeight = document.body.scrollHeight;
        const windowHeight = window.innerHeight;
        
        if (bodyHeight < windowHeight) {
            footer.style.position = 'fixed';
            footer.style.bottom = '0';
            footer.style.width = '100%';
            document.body.style.paddingBottom = footer.offsetHeight + 'px';
        } else {
            footer.style.position = 'static';
            document.body.style.paddingBottom = '0';
        }
    },

    handleMobileLayout() {
        const isMobile = window.innerWidth < 768;
        
        // Mobile menu adjustments
        const navItems = document.querySelectorAll('.navbar-nav .nav-link');
        navItems.forEach(item => {
            if (isMobile) {
                item.style.fontSize = '0.9rem';
                item.style.padding = '0.5rem 0.75rem';
            } else {
                item.style.fontSize = '';
                item.style.padding = '';
            }
        });

        // Adjust dropdowns on mobile
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu && isMobile) {
                menu.style.fontSize = '0.875rem';
                menu.style.maxHeight = '300px';
                menu.style.overflowY = 'auto';
            } else {
                menu.style.fontSize = '';
                menu.style.maxHeight = '';
                menu.style.overflowY = '';
            }
        });

        // Touch-friendly buttons on mobile
        const buttons = document.querySelectorAll('button, a[role="button"]');
        buttons.forEach(button => {
            if (isMobile && !button.style.minHeight) {
                button.style.minHeight = '44px';
                button.style.minWidth = '44px';
            }
        });
    }
};

// Error Handler
const ErrorHandler = {
    init() {
        // Global error logging
        window.addEventListener('error', this.logError.bind(this));
        window.addEventListener('unhandledrejection', this.logPromiseError.bind(this));
        
        // AJAX error handling
        window.addEventListener('error', (e) => {
            if (e.filename && e.filename.includes('/static/')) {
                // Don't log static file errors
                e.preventDefault();
                return false;
            }
        });

        // Add error boundary classes
        document.documentElement.classList.add('error-boundary');
    },

    logError(event) {
        const errorData = {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            language: navigator.language
        };

        this.sendErrorReport(errorData);
        
        // Don't show error to user for expected errors
        if (this.isExpectedError(event)) {
            event.preventDefault();
            return false;
        }

        return true;
    },

    logPromiseError(event) {
        const errorData = {
            message: event.reason?.message || 'Unhandled promise rejection',
            filename: event.reason?.stack?.split('\n')[1]?.trim() || 'Unknown',
            error: event.reason,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            type: 'promise_rejection'
        };

        this.sendErrorReport(errorData);
    },

    isExpectedError(event) {
        const expectedPatterns = [
            /ResizeObserver loop limit exceeded/,
            /Failed to execute 'postMessage' on 'Window'/,
            /Script error/,
            /The play\(\) request was interrupted/
        ];

        return expectedPatterns.some(pattern => 
            pattern.test(event.message || '')
        );
    },

    sendErrorReport(errorData) {
        if (MainApp.config.debug) {
            console.error('Error Report:', errorData);
        }

        // Send to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'exception', {
                description: `${errorData.message} - ${errorData.filename}:${errorData.lineno}`,
                fatal: true
            });
        }

        // Send to error reporting service (Sentry, etc.)
        if (typeof Raven !== 'undefined') {
            Raven.captureException(errorData.error, {
                extra: {
                    url: errorData.url,
                    lineno: errorData.lineno,
                    colno: errorData.colno
                }
            });
        }

        // Store for later sending if offline
        if (!navigator.onLine) {
            if (!window.errorQueue) window.errorQueue = [];
            window.errorQueue.push(errorData);
        } else {
            // Send immediately
            this.sendToServer(errorData);
        }
    },

    sendToServer(errorData) {
        // Send error data to your backend
        ProjectUtils.makeAjaxRequest('/api/errors/', {
            method: 'POST',
            data: errorData,
            timeout: 5000,
            showLoading: false
        })
        .then(() => {
            if (MainApp.config.debug) {
                console.log('Error reported successfully');
            }
        })
        .catch(error => {
            console.warn('Failed to send error report:', error);
            // Store for retry
            if (!window.errorQueue) window.errorQueue = [];
            window.errorQueue.push(errorData);
        });
    },

    retryErrorReports() {
        if (!window.errorQueue || window.errorQueue.length === 0) return;

        const errorsToSend = [...window.errorQueue];
        window.errorQueue = [];

        errorsToSend.forEach(errorData => {
            this.sendToServer(errorData);
        });
    }
};

// Initialize layout manager
LayoutManager.init();

// Expose main components to global scope
window.MainApp = MainApp;
window.Sidebar = Sidebar;
window.Topbar = Topbar;
window.ContentLoader = ContentLoader;
window.KeyboardShortcuts = KeyboardShortcuts;
window.ErrorHandler = ErrorHandler;

// Handle offline error queue when back online
window.addEventListener('online', () => {
    if (window.errorQueue && window.errorQueue.length > 0) {
        ErrorHandler.retryErrorReports();
    }
});
// Search functionality enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Mobile search toggle
    const mobileSearchToggle = document.getElementById('mobileSearchToggle');
    const mobileSearchModal = new bootstrap.Modal(document.getElementById('mobileSearchModal'));
    
    if (mobileSearchToggle) {
        mobileSearchToggle.addEventListener('click', function() {
            mobileSearchModal.show();
        });
    }
    
    // Clear search functionality
    const clearSearchButtons = document.querySelectorAll('#clearSearch, .clear-search-btn');
    clearSearchButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const form = this.closest('form');
            const input = form.querySelector('input[type="search"]');
            const suggestions = form.querySelector('.search-suggestions');
            
            input.value = '';
            if (suggestions) suggestions.style.display = 'none';
            this.style.display = 'none';
            
            // Focus back to input
            input.focus();
            
            // Submit if needed
            if (form.id === 'topbarSearchForm') {
                window.location.href = "{% url 'sooratvaziat:dashboard' %}";
            }
        });
    });
    
    // Show/hide clear button
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        const clearBtn = input.closest('form').querySelector('#clearSearch, .clear-search-btn');
        if (clearBtn) {
            const observer = new MutationObserver(function() {
                if (input.value.trim()) {
                    clearBtn.style.display = 'block';
                } else {
                    clearBtn.style.display = 'none';
                }
            });
            
            observer.observe(input, { attributes: true, childList: true, subtree: true });
            
            // Initial check
            if (input.value.trim()) {
                clearBtn.style.display = 'block';
            }
        }
        
        // Search on input (for non-topbar forms)
        if (!input.closest('#topbarSearchForm')) {
            let debounceTimer;
            input.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                const query = this.value.trim();
                
                if (query.length >= 2) {
                    debounceTimer = setTimeout(() => {
                        // Update URL with query
                        const url = new URL(window.location);
                        url.searchParams.set('q', query);
                        window.history.replaceState({}, '', url);
                    }, 500);
                }
            });
        }
    });
    
    // Search submit enhancement
    const searchForms = document.querySelectorAll('.search-form');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const query = this.querySelector('input[type="search"]').value.trim();
            
            if (!query) {
                e.preventDefault();
                showToast('لطفاً عبارت جستجو را وارد کنید', 'warning');
                return false;
            }
            
            // Show loading state
            const submitBtn = this.querySelector('.search-submit');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>در حال جستجو...';
                submitBtn.disabled = true;
                
                // Restore after submit
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 2000);
            }
        });
    });
    
    // Keyboard shortcuts for search
    document.addEventListener('keydown', function(e) {
        // Ctrl+K or Cmd+K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.focus();
                showToast('جستجو فعال شد (ESC برای خروج)', 'info');
            }
        }
        
        // Ctrl+Enter for search submit
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const searchForm = document.querySelector('.search-form');
            if (searchForm && searchForm.querySelector('input[type="search"]').value.trim()) {
                e.preventDefault();
                searchForm.submit();
            }
        }
    });
});
