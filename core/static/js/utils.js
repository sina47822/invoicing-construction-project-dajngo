/**
 * Utility functions for the project management system
 * Version: 1.0.0
 * Author: Project Team
 */

// Namespace for utilities
const ProjectUtils = {
    // Initialize all utilities
    init() {
        this.initTooltips();
        this.initPopovers();
        this.initModals();
        this.initFormValidation();
        this.initClipboard();
        this.initLazyLoading();
        this.initPrint();
        this.initDarkModeToggle();
        this.initSearch();
        console.log('ProjectUtils initialized successfully');
    },

    // Initialize Bootstrap tooltips
    initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    // Initialize Bootstrap popovers
    initPopovers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    // Initialize modals with enhanced functionality
    initModals() {
        // Auto-focus first input in modals
        document.addEventListener('shown.bs.modal', function (event) {
            const modal = event.target;
            const firstInput = modal.querySelector('input, select, textarea');
            if (firstInput && !firstInput.disabled) {
                firstInput.focus();
            }
            
            // Add escape key to close modal
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    bootstrap.Modal.getInstance(modal).hide();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
        });

        // Close modals on outside click (excluding form submission)
        document.addEventListener('hide.bs.modal', function (event) {
            const modal = event.target;
            const isFormSubmitting = modal.querySelector('form.submitting');
            if (isFormSubmitting) {
                event.preventDefault();
            }
        });
    },

    // Initialize validation on all forms
    initFormValidation() {
        // Custom validation messages in Persian
        const validationMessages = {
            required: 'این فیلد الزامی است',
            email: 'لطفاً ایمیل معتبر وارد کنید',
            minlength: 'حداقل {0} کاراکتر وارد کنید',
            maxlength: 'حداکثر {0} کاراکتر مجاز است',
            pattern: 'فرمت وارد شده صحیح نمی‌باشد',
            custom: 'مقدار وارد شده معتبر نیست'
        };

        // Add custom validation rules FIRST
        ProjectUtils.addCustomValidators();

        // Initialize validation on all forms
        const forms = document.querySelectorAll('form.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', function (e) {
                if (!this.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                this.classList.add('was-validated');

                // Custom validation
                ProjectUtils.validateCustomFields(this);
            });

            // Real-time validation
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', function () {
                    this.classList.add('was-validated');
                    ProjectUtils.validateField(this);
                });

                input.addEventListener('input', function () {
                    if (this.classList.contains('is-invalid')) {
                        this.classList.remove('is-invalid');
                        ProjectUtils.removeFieldError(this);
                    }
                });
            });
        });
    },

    // Add custom validation rules
    addCustomValidators() {
        // Persian mobile number validation
        if (!window.HTMLInputElement.prototype.validityState.hasOwnProperty('persianMobile')) {
            Object.defineProperty(HTMLInputElement.prototype.validityState, 'persianMobile', {
                get: function() {
                    const value = this.value.trim();
                    const persianMobileRegex = /^09[0-9]{9}$/;
        return value === '' || persianMobileRegex.test(value);
                }
            });
        }

        // National ID validation
        if (!window.HTMLInputElement.prototype.validityState.hasOwnProperty('nationalId')) {
            Object.defineProperty(HTMLInputElement.prototype.validityState, 'nationalId', {
                get: function() {
                    const value = this.value.trim();
                    const nationalIdRegex = /^[0-9]{10}$/;
        if (!nationalIdRegex.test(value)) return false;

        // Checksum validation
        const check = parseInt(value[9]);
        let sum = 0;
        for (let i = 0; i < 9; ++i) {
            sum += parseInt(value[i]) * (10 - i);
        }
        sum %= 11;
        return (sum < 2 && check === sum) || (sum >= 2 && check === 11 - sum);
                }
            });
        }

        // Persian date validation (Jalali)
        if (!window.HTMLInputElement.prototype.validityState.hasOwnProperty('jalaliDate')) {
            Object.defineProperty(HTMLInputElement.prototype.validityState, 'jalaliDate', {
                get: function() {
                    const value = this.value.trim();
                    if (!value) return true;
                    const jalaliRegex = /^(13[0-9]{2}|14[0-2][0-9]|140[0-4])\/(0[1-9]|1[0-2])\/([0-2][0-9]|3[0-1])$/;
        return jalaliRegex.test(value);
                }
            });
        }
    },

    // Validate individual field
    validateField(input) {
        const value = input.value.trim();
        const fieldName = input.getAttribute('data-field-name') || input.name || 'فیلد';
        
        // Remove previous validation states
        input.classList.remove('is-valid', 'is-invalid');
        ProjectUtils.removeFieldError(input);

        // Check required
        if (input.hasAttribute('required') && !value) {
            ProjectUtils.showFieldError(input, `${fieldName} الزامی است`);
            input.classList.add('is-invalid');
            return false;
        }

        // Check pattern
        if (input.pattern && value && !new RegExp(input.pattern).test(value)) {
            const message = input.getAttribute('data-pattern-message') || 
                           `${fieldName} فرمت صحیح ندارد`;
            ProjectUtils.showFieldError(input, message);
            input.classList.add('is-invalid');
            return false;
        }

        // Check min/max length
        if (input.minLength && value.length < input.minLength) {
            ProjectUtils.showFieldError(input, 
                `حداقل ${input.minLength} کاراکتر وارد کنید`);
            input.classList.add('is-invalid');
            return false;
        }

        if (input.maxLength && value.length > input.maxLength) {
            ProjectUtils.showFieldError(input, 
                `حداکثر ${input.maxLength} کاراکتر مجاز است`);
            input.classList.add('is-invalid');
            return false;
        }

        // Email validation
        if (input.type === 'email' && value && !ProjectUtils.isValidEmail(value)) {
            ProjectUtils.showFieldError(input, 'لطفاً ایمیل معتبر وارد کنید');
            input.classList.add('is-invalid');
            return false;
        }

        // Custom validations
        if (!ProjectUtils.validateCustomField(input)) {
            input.classList.add('is-invalid');
            return false;
        }

        // All validations passed
        if (value) {
            input.classList.add('is-valid');
        }
        return true;
    },

    // Validate custom fields
    validateCustomFields(form) {
        const customFields = form.querySelectorAll('[data-custom-validation]');
        let isValid = true;

        customFields.forEach(field => {
            const validator = field.getAttribute('data-custom-validation');
            const value = field.value.trim();
            const fieldName = field.getAttribute('data-field-name') || field.name;

            if (validator === 'persianMobile' && value && !ProjectUtils.isValidPersianMobile(value)) {
                ProjectUtils.showFieldError(field, 'شماره موبایل معتبر نیست');
                field.classList.add('is-invalid');
                isValid = false;
            } else if (validator === 'nationalId' && value && !ProjectUtils.isValidNationalId(value)) {
                ProjectUtils.showFieldError(field, 'کد ملی معتبر نیست');
                field.classList.add('is-invalid');
                isValid = false;
            } else if (validator === 'jalaliDate' && value && !ProjectUtils.isValidJalaliDate(value)) {
                ProjectUtils.showFieldError(field, 'تاریخ شمسی معتبر نیست');
                field.classList.add('is-invalid');
                isValid = false;
            }
        });

        return isValid;
    },

    validateCustomField(field) {
        const validator = field.getAttribute('data-custom-validation');
        if (!validator) return true;

        const value = field.value.trim();
        if (!value) return true;

        switch (validator) {
            case 'persianMobile':
                return ProjectUtils.isValidPersianMobile(value);
            case 'nationalId':
                return ProjectUtils.isValidNationalId(value);
            case 'jalaliDate':
                return ProjectUtils.isValidJalaliDate(value);
            case 'positiveNumber':
                return ProjectUtils.isPositiveNumber(value);
            case 'persianText':
                return ProjectUtils.isValidPersianText(value);
            default:
                return true;
        }
    },

    // Validation helper functions
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    isValidPersianMobile(mobile) {
        const persianMobileRegex = /^09[0-9]{9}$/;
        return persianMobileRegex.test(mobile.replace(/\D/g, ''));
    },

    isValidNationalId(nationalId) {
        const value = nationalId.replace(/\D/g, '');
        if (value.length !== 10) return false;

        const check = parseInt(value[9]);
        let sum = 0;
        for (let i = 0; i < 9; ++i) {
            sum += parseInt(value[i]) * (10 - i);
        }
        sum %= 11;
        return (sum < 2 && check === sum) || (sum >= 2 && check === 11 - sum);
    },

    isValidJalaliDate(dateStr) {
        const parts = dateStr.split('/');
        if (parts.length !== 3) return false;

        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);

        if (year < 1300 || year > 1500 || month < 1 || month > 12 || day < 1) return false;

        // Days in each month (simplified)
        const daysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
        if (month === 12 && ProjectUtils.isJalaliLeapYear(year)) {
            daysInMonth[11] = 30;
        }

        return day <= daysInMonth[month - 1];
    },

    isJalaliLeapYear(year) {
        return (((((year * 682) % 2816) * 0.9017) % 2816) < 1860);
    },

    isPositiveNumber(value) {
        const num = parseFloat(value);
        return !isNaN(num) && num > 0;
    },

    isValidPersianText(text) {
        const persianRegex = /^[\u0600-\u06FF\s]+$/;
        return persianRegex.test(text);
    },

    // Show field error message
    showFieldError(input, message) {
        // Remove existing error
        ProjectUtils.removeFieldError(input);

        // Create error element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback d-block';
        errorDiv.style.cssText = 'color: #dc3545; font-size: 0.875rem; margin-top: 0.25rem;';
        errorDiv.textContent = message;

        // Insert after input
        const parent = input.parentNode;
        parent.insertBefore(errorDiv, input.nextSibling);

        // Add ARIA attributes
        input.setAttribute('aria-describedby', `error-${input.id || input.name}`);
        if (!input.id) {
            input.id = `input-${Date.now()}`;
        }
        errorDiv.id = `error-${input.id}`;
    },

    // Remove field error message
    removeFieldError(input) {
        const errorId = input.getAttribute('aria-describedby');
        if (errorId) {
            const errorEl = document.getElementById(errorId);
            if (errorEl) {
                errorEl.parentNode.removeChild(errorEl);
            }
            input.removeAttribute('aria-describedby');
        }
    },

    // Initialize clipboard functionality
    initClipboard() {
        const clipboardElements = document.querySelectorAll('[data-copy-text]');
        
        clipboardElements.forEach(element => {
            element.addEventListener('click', function(e) {
                e.preventDefault();
                const text = this.getAttribute('data-copy-text');
                const originalText = this.textContent;
                
                // Copy to clipboard
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(text).then(() => {
                        ProjectUtils.showCopyFeedback(this, 'کپی شد');
                    }).catch(err => {
                        console.error('Failed to copy: ', err);
                        ProjectUtils.fallbackCopyTextToClipboard(text, this);
                    });
                } else {
                    ProjectUtils.fallbackCopyTextToClipboard(text, this);
                }
            });
        });
    },

    showCopyFeedback(element, message) {
        const originalText = element.textContent;
        const originalTitle = element.getAttribute('title') || '';
        
        element.textContent = message;
        element.style.color = '#198754';
        element.setAttribute('title', 'کپی شد');
        
        setTimeout(() => {
            element.textContent = originalText;
            element.style.color = '';
            element.setAttribute('title', originalTitle);
        }, 2000);
    },

    fallbackCopyTextToClipboard(text, element) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                ProjectUtils.showCopyFeedback(element, 'کپی شد');
            } else {
                ProjectUtils.showCopyFeedback(element, 'خطا در کپی');
            }
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
            ProjectUtils.showCopyFeedback(element, 'خطا در کپی');
        }
        
        document.body.removeChild(textArea);
    },

    // Lazy loading for images
    initLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        img.alt = img.dataset.alt || '';
                        observer.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for browsers without IntersectionObserver
            images.forEach(img => {
                img.src = img.dataset.src;
                img.classList.remove('lazy');
            });
        }
    },

    // Print functionality with custom options
    initPrint() {
        const printButtons = document.querySelectorAll('[data-print]');
        
        printButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const printTarget = this.getAttribute('data-print');
                const printOptions = this.getAttribute('data-print-options') || '{}';
                const options = JSON.parse(printOptions);
                
                ProjectUtils.printElement(printTarget, options);
            });
        });

        // Global print styles
        if (!document.getElementById('print-styles')) {
            const style = document.createElement('style');
            style.id = 'print-styles';
            style.textContent = `
                @media print {
                    body * { visibility: hidden; }
                    .print-target, .print-target * { visibility: visible; }
                    .print-target { 
                        position: absolute !important;
                        left: 0 !important;
                        top: 0 !important;
                        width: 100% !important;
                        height: auto !important;
                    }
                    .no-print { display: none !important; }
                    .page-break { page-break-before: always; }
                }
            `;
            document.head.appendChild(style);
        }
    },

    printElement(target, options = {}) {
        const defaultOptions = {
            showDialog: true,
            title: document.title,
            styles: [],
            exclude: []
        };

        const config = { ...defaultOptions, ...options };
        
        // Add custom styles
        if (config.styles.length > 0) {
            const tempStyle = document.createElement('style');
            tempStyle.textContent = config.styles.join('\n');
            document.head.appendChild(tempStyle);
        }

        // Hide excluded elements
        config.exclude.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => el.classList.add('no-print'));
        });

        // Add print target class
        if (typeof target === 'string') {
            const element = document.querySelector(target);
            if (element) {
                element.classList.add('print-target');
            }
        } else {
            target.classList.add('print-target');
        }

        // Print
        if (config.showDialog) {
            window.print();
        } else {
            // Programmatic printing
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>${config.title}</title>
                        ${document.querySelector('head').innerHTML}
                    </head>
                    <body>${document.querySelector(target).innerHTML}</body>
                </html>
            `);
            printWindow.document.close();
            printWindow.print();
        }

        // Cleanup
        setTimeout(() => {
            if (typeof target === 'string') {
                const element = document.querySelector(target);
                if (element) {
                    element.classList.remove('print-target');
                }
            } else {
                target.classList.remove('print-target');
            }

            config.exclude.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => el.classList.remove('no-print'));
            });

            const tempStyle = document.querySelector('style[data-print-temp]');
            if (tempStyle) {
                tempStyle.parentNode.removeChild(tempStyle);
            }
        }, 1000);
    },

    // Dark mode toggle
    initDarkModeToggle() {
        const toggle = document.querySelector('[data-dark-mode-toggle]');
        if (!toggle) return;

        const isDark = localStorage.getItem('darkMode') === 'enabled';
        const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

        // Set initial state
        if (isDark || (!localStorage.getItem('darkMode') && systemPrefersDark)) {
            document.documentElement.classList.add('dark-mode');
            toggle.checked = true;
        }

        toggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'enabled');
                document.body.style.colorScheme = 'dark';
            } else {
                document.documentElement.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'disabled');
                document.body.style.colorScheme = 'light';
            }
        });

        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                if (localStorage.getItem('darkMode') !== 'enabled' && 
                    localStorage.getItem('darkMode') !== 'disabled') {
                    if (e.matches) {
                        document.documentElement.classList.add('dark-mode');
                        toggle.checked = true;
                    } else {
                        document.documentElement.classList.remove('dark-mode');
                        toggle.checked = false;
                    }
                }
            });
        }
    },

    // Search functionality
    initSearch() {
        const searchInputs = document.querySelectorAll('[data-search]');
        
        searchInputs.forEach(input => {
            const target = document.querySelector(input.getAttribute('data-search'));
            if (!target) return;

            let searchTimeout;
            input.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    ProjectUtils.performSearch(this.value, target, input.getAttribute('data-search-options'));
                }, 300);
            });

            // Clear search
            const clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'btn-close position-absolute top-50 end-0 translate-middle-y me-2';
            clearBtn.style.cssText = 'display: none; z-index: 5;';
            clearBtn.setAttribute('aria-label', 'پاک کردن جستجو');
            clearBtn.innerHTML = '&times;';
            
            clearBtn.addEventListener('click', function() {
                input.value = '';
                input.focus();
                ProjectUtils.performSearch('', target, input.getAttribute('data-search-options'));
                this.style.display = 'none';
            });
            
            input.parentNode.appendChild(clearBtn);
            
            input.addEventListener('input', function() {
                clearBtn.style.display = this.value ? 'block' : 'none';
            });
        });
    },

    performSearch(query, target, options = '{}') {
        const config = {
            selector: 'tr, .search-item',
            textFields: 'td, .search-text',
            highlight: true,
            caseSensitive: false,
            minLength: 2,
            ...JSON.parse(options)
        };

        const items = target.querySelectorAll(config.selector);
        let visibleCount = 0;

        items.forEach(item => {
            let textContent = '';
            
            // Get text from specified fields
            const fields = item.querySelectorAll(config.textFields);
            fields.forEach(field => {
                textContent += field.textContent || field.innerText || '';
            });

            // Clean and compare text
            const cleanQuery = config.caseSensitive ? query : query.toLowerCase();
            const cleanText = config.caseSensitive ? textContent : textContent.toLowerCase();
            
            if (query.length < config.minLength) {
                item.style.display = '';
                ProjectUtils.removeHighlight(item);
                visibleCount++;
                return;
            }

            if (cleanText.includes(cleanQuery)) {
                item.style.display = '';
                visibleCount++;
                
                // Highlight search terms
                if (config.highlight) {
                    ProjectUtils.highlightText(item, query, config.caseSensitive);
                }
            } else {
                item.style.display = 'none';
                ProjectUtils.removeHighlight(item);
            }
        });

        // Update search results count
        const countElement = target.parentNode.querySelector('.search-results-count');
        if (countElement) {
            countElement.textContent = `${visibleCount} نتیجه یافت شد`;
        }
    },

    highlightText(element, term, caseSensitive = false) {
        ProjectUtils.removeHighlight(element);
        
        const regex = new RegExp(
            `(${caseSensitive ? term : term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 
            'g'
        );
        
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const nodes = [];
        let node;
        while (node = walker.nextNode()) {
            nodes.push(node);
        }
        
        nodes.forEach(node => {
            const parent = node.parentNode;
            const content = caseSensitive ? node.textContent : node.textContent.toLowerCase();
            const index = content.indexOf(caseSensitive ? term : term.toLowerCase());
            
            if (index !== -1) {
                const highlighted = node.textContent.replace(regex, '<mark class="search-highlight">$1</mark>');
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = highlighted;
                
                while (tempDiv.firstChild) {
                    parent.insertBefore(tempDiv.firstChild, node);
                }
                
                parent.removeChild(node);
            }
        });
    },

    removeHighlight(element) {
        const highlights = element.querySelectorAll('.search-highlight');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            const textNode = document.createTextNode(highlight.textContent);
            parent.replaceChild(textNode, highlight);
        });
    },

    // Persian number utilities
    toPersianDigits(str) {
        if (!str) return '';
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return str.toString().replace(/\d/g, digit => persianDigits[digit]);
    },

    toEnglishDigits(str) {
        if (!str) return '';
        const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        return str.toString().replace(/[۰-۹]/g, digit => englishDigits[digit.charCodeAt(0) - '۰'.charCodeAt(0)]);
    },

    formatPersianNumber(number, decimals = 0) {
        const num = parseFloat(number).toFixed(decimals);
        return ProjectUtils.toPersianDigits(num).replace(/\B(?=(\d{3})+(?!\d))/g, '٬');
    },

    // Date utilities
    getCurrentJalaliDate() {
        const now = new Date();
        const jalali = ProjectUtils.gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());
        return `${jalali.year}/${jalali.month.toString().padStart(2, '0')}/${jalali.day.toString().padStart(2, '0')}`;
    },

    gregorianToJalali(gy, gm, gd) {
        let g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
        let jy = (gy <= 1600) ? 0 : 979;
        gy -= (gy <= 1600) ? 621 : 1600;
        let gy2 = (gm > 2) ? (gy + 1) : gy;
        let days = (365 * gy) + ((Math.floor((gy2 + 3) / 4)) - (Math.floor((gy2 + 99) / 100)) + (Math.floor((gy2 + 399) / 400))) - 80 + gd + g_d_m[gm - 1];
        jy += 33 * Math.floor(days / 12053);
        days %= 12053;
        jy += 4 * Math.floor(days / 1461);
        days %= 1461;
        if (days > 365) {
            jy += Math.floor((days - 1) / 365);
            days = (days - 1) % 365;
        }
        let jm = (days < 186) ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
        let jd = 1 + ((days < 186) ? (days % 31) : ((days - 186) % 30));
        return { year: jy, month: jm, day: jd };
    },

    // AJAX wrapper
    makeAjaxRequest(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            timeout: 10000,
            showLoading: true,
            loadingTarget: null,
            ...options
        };

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Setup timeout
            const timeoutId = setTimeout(() => {
                xhr.abort();
                reject(new Error('Request timeout'));
            }, defaultOptions.timeout);

            xhr.open(defaultOptions.method, url, true);
            
            // Set headers
            Object.keys(defaultOptions.headers).forEach(key => {
                xhr.setRequestHeader(key, defaultOptions.headers[key]);
            });

            // CSRF token for POST requests
            if (defaultOptions.method !== 'GET' && document.querySelector('[name=csrfmiddlewaretoken]')) {
                xhr.setRequestHeader('X-CSRFToken', 
                    document.querySelector('[name=csrfmiddlewaretoken]').value);
            }

            // Show loading
            if (defaultOptions.showLoading && defaultOptions.loadingTarget) {
                const target = document.querySelector(defaultOptions.loadingTarget);
                if (target) {
                    ProjectUtils.showLoading(target);
                }
            }

            xhr.onload = function() {
                clearTimeout(timeoutId);
                
                // Hide loading
                if (defaultOptions.showLoading && defaultOptions.loadingTarget) {
                    const target = document.querySelector(defaultOptions.loadingTarget);
                    if (target) {
                        ProjectUtils.hideLoading(target);
                    }
                }

                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const responseData = defaultOptions.responseType === 'json' 
                            ? JSON.parse(xhr.responseText) 
                            : xhr.responseText;
                        resolve({
                            status: xhr.status,
                            data: responseData,
                            headers: xhr.getAllResponseHeaders(),
                            xhr: xhr
                        });
                    } catch (e) {
                        resolve({
                            status: xhr.status,
                            data: xhr.responseText,
                            headers: xhr.getAllResponseHeaders(),
                            xhr: xhr
                        });
                    }
                } else {
                    let error;
                    try {
                        error = JSON.parse(xhr.responseText);
                    } catch (e) {
                        error = {
                            message: xhr.statusText,
                            status: xhr.status
                        };
                    }
                    reject({
                        status: xhr.status,
                        error: error,
                        xhr: xhr
                    });
                }
            };

            xhr.onerror = function() {
                clearTimeout(timeoutId);
                if (defaultOptions.showLoading && defaultOptions.loadingTarget) {
                    const target = document.querySelector(defaultOptions.loadingTarget);
                    if (target) {
                        ProjectUtils.hideLoading(target);
                    }
                }
                reject(new Error('Network error occurred'));
            };

            xhr.ontimeout = function() {
                if (defaultOptions.showLoading && defaultOptions.loadingTarget) {
                    const target = document.querySelector(defaultOptions.loadingTarget);
                    if (target) {
                        ProjectUtils.hideLoading(target);
                    }
                }
                reject(new Error('Request timeout'));
            };

            // Send request
            if (defaultOptions.method === 'GET') {
                xhr.send();
            } else {
                xhr.send(defaultOptions.body || JSON.stringify(defaultOptions.data));
            }
        });
    },

    // Loading states
    showLoading(target) {
        let loadingEl = target.querySelector('.loading-overlay');
        
        if (!loadingEl) {
            loadingEl = document.createElement('div');
            loadingEl.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
            loadingEl.style.cssText = `
                background: rgba(255, 255, 255, 0.8);
                z-index: 10;
                backdrop-filter: blur(2px);
            `;
            loadingEl.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">در حال بارگذاری...</span>
                </div>
                <div class="loading-text ms-2">در حال بارگذاری...</div>
            `;
            target.style.position = 'relative';
            target.appendChild(loadingEl);
        }
        
        loadingEl.classList.remove('d-none');
    },

    hideLoading(target) {
        const loadingEl = target.querySelector('.loading-overlay');
        if (loadingEl) {
            loadingEl.classList.add('d-none');
            setTimeout(() => {
                if (loadingEl.parentNode) {
                    loadingEl.parentNode.removeChild(loadingEl);
                }
            }, 300);
        }
    },

    // Toast notifications
    showToast(message, type = 'info', options = {}) {
        const defaultOptions = {
            title: '',
            timeout: 5000,
            position: 'top-right',
            closeButton: true,
            progressBar: true
        };

        const config = { ...defaultOptions, ...options };
        
        // Remove existing toast container if needed
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = `toast-container position-fixed ${config.position}`;
            toastContainer.style.cssText = `
                z-index: 9999;
                padding: 1rem;
                ${config.position.includes('top') ? 'top: 0;' : 'bottom: 0;'}
                ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'}
            `;
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = toastId;
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.style.cssText = `
            min-height: 60px;
            border-radius: 0.75rem;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.2);
            margin-bottom: 0.5rem;
            overflow: hidden;
        `;

        let toastContent = `
            <div class="d-flex">
                <div class="toast-body">
                    ${config.title ? `<strong class="me-2">${config.title}</strong>` : ''}
                    ${message}
                </div>
        `;

        if (config.closeButton) {
            toastContent += `
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="بستن"></button>
            `;
        }

        toastContent += '</div>';

        if (config.progressBar) {
            toastContent += `
                <div class="toast-progress" style="
                    height: 3px;
                    background: rgba(255, 255, 255, 0.3);
                    transition: width ${config.timeout}ms linear;
                "></div>
            `;
        }

        toastEl.innerHTML = toastContent;
        toastContainer.appendChild(toastEl);

        // Show toast
        const toast = new bootstrap.Toast(toastEl, { autohide: config.timeout > 0 });
        toast.show();

        // Progress bar animation
        if (config.progressBar) {
            const progressBar = toastEl.querySelector('.toast-progress');
            if (progressBar) {
                setTimeout(() => {
                    progressBar.style.width = '100%';
                }, 100);
            }
        }

        // Auto-hide
        if (config.timeout > 0) {
            setTimeout(() => {
                if (toastEl.parentNode) {
                    bootstrap.Toast.getInstance(toastEl).hide();
                }
            }, config.timeout);
        }

        // Cleanup on hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            if (this.parentNode) {
                this.parentNode.removeChild(this);
            }
            
            // Remove container if empty
            if (toastContainer.children.length === 0) {
                if (toastContainer.parentNode) {
                    toastContainer.parentNode.removeChild(toastContainer);
                }
            }
        });

        return toastEl;
    },

    // Confirmation dialogs
    confirmAction(message, options = {}) {
        return new Promise((resolve, reject) => {
            const defaultOptions = {
                title: 'تأیید عملیات',
                confirmText: 'تأیید',
                cancelText: 'انصراف',
                confirmClass: 'btn-danger',
                cancelClass: 'btn-secondary',
                showCancel: true,
                size: 'md'
            };

            const config = { ...defaultOptions, ...options };
            
            // Check if Bootstrap modal is available
            if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
                // Fallback to window.confirm
                const result = window.confirm(message);
                if (result) {
                    resolve(true);
                } else {
                    reject(new Error('User cancelled'));
                }
                return;
            }

            // Create unique modal ID
            const modalId = 'confirmModal-' + Date.now();
            
            // Create modal HTML
            const modalHTML = `
                <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                    <div class="modal-dialog modal-${config.size}">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="${modalId}Label">${config.title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="بستن"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                            </div>
                            <div class="modal-footer">
                                ${config.showCancel ? `
                                    <button type="button" class="btn ${config.cancelClass}" data-bs-dismiss="modal">
                                        ${config.cancelText}
                                    </button>
                                ` : ''}
                                <button type="button" class="btn ${config.confirmClass}" id="confirmBtn-${modalId}">
                                    ${config.confirmText}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Add to body
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Show modal
            const modalElement = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalElement);
            modal.show();

            // Handle confirm button
            const confirmBtn = document.getElementById(`confirmBtn-${modalId}`);
            confirmBtn.addEventListener('click', function() {
                modal.hide();
                resolve(true);
            });

            // Handle modal hidden
            modalElement.addEventListener('hidden.bs.modal', function() {
                // Cleanup
                if (this.parentNode) {
                    this.parentNode.removeChild(this);
                }
                reject(new Error('Modal closed'));
            }, { once: true });

            // Prevent escape key from closing if needed
            if (!config.showCancel) {
                modalElement.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        e.preventDefault();
                    }
                });
            }
        });
    },

    // File upload utilities
    initFileUpload() {
        const fileInputs = document.querySelectorAll('input[type="file"][data-file-upload]');
        
        fileInputs.forEach(input => {
            const previewContainer = document.querySelector(input.getAttribute('data-file-upload'));
            if (!previewContainer) return;

            input.addEventListener('change', function(e) {
                ProjectUtils.handleFileUpload(e.target.files, previewContainer, input);
            });

            // Drag and drop support
            previewContainer.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.classList.add('drag-over');
            });

            previewContainer.addEventListener('dragleave', function(e) {
                e.preventDefault();
                this.classList.remove('drag-over');
            });

            previewContainer.addEventListener('drop', function(e) {
                e.preventDefault();
                this.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const dataTransfer = new DataTransfer();
                    Array.from(files).forEach(file => dataTransfer.items.add(file));
                    input.files = dataTransfer.files;
                    ProjectUtils.handleFileUpload(files, this, input);
                }
            });
        });
    },

    handleFileUpload(files, previewContainer, input) {
        previewContainer.innerHTML = '';
        
        Array.from(files).forEach((file, index) => {
            // Check file type
            const allowedTypes = input.getAttribute('accept')?.split(',') || ['*/*'];
            const isValidType = allowedTypes.some(type => 
                file.type === '' || file.type.startsWith(type.trim()) || type.trim() === '*/*'
            );
            
            if (!isValidType) {
                ProjectUtils.showToast(`نوع فایل ${file.name} مجاز نیست`, 'danger');
                return;
            }

            // Check file size
            const maxSize = parseInt(input.getAttribute('data-max-size')) || 10; // MB
            const fileSizeMB = file.size / (1024 * 1024);
            if (fileSizeMB > maxSize) {
                ProjectUtils.showToast(
                    `حجم فایل ${file.name} (${fileSizeMB.toFixed(1)}MB) بیش از حد مجاز است`, 
                    'danger'
                );
                return;
            }

            // Create preview
            const filePreview = ProjectUtils.createFilePreview(file, index);
            previewContainer.appendChild(filePreview);

            // Add remove button functionality
            const removeBtn = filePreview.querySelector('.file-remove');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => {
                    filePreview.remove();
                    
                    // Update input files
                    const dt = new DataTransfer();
                    Array.from(input.files).forEach(f => {
                        if (f !== file) {
                            dt.items.add(f);
                        }
                    });
                    input.files = dt.files;
                });
            }
        });

        // Update input label
        const label = input.parentNode.querySelector('label') || input.parentNode;
        if (files.length > 0) {
            label.textContent = `${files.length} فایل انتخاب شد`;
            label.classList.add('text-success');
        } else {
            label.textContent = 'فایل را انتخاب کنید';
            label.classList.remove('text-success');
        }
    },

    createFilePreview(file, index) {
        const div = document.createElement('div');
        div.className = 'file-preview d-flex align-items-center p-3 border rounded mb-2';
        div.style.cssText = 'background: #ffffff; border: 1px solid #dee2e6;';

        let previewContent = '';
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                div.innerHTML = `
                    <img src="${e.target.result}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 0.375rem; margin-left: 1rem;" alt="${file.name}">
                    <div class="flex-grow-1 ms-3">
                        <div class="fw-semibold">${file.name}</div>
                        <small class="text-muted">${(file.size / 1024).toFixed(1)} KB</small>
                    </div>
                    <button type="button" class="btn-close file-remove" aria-label="حذف"></button>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            previewContent = `
                <div class="file-icon text-muted" style="font-size: 2rem; margin-left: 1rem;">
                    ${ProjectUtils.getFileIcon(file.type)}
                </div>
                <div class="flex-grow-1 ms-3">
                    <div class="fw-semibold">${file.name}</div>
                    <small class="text-muted">${(file.size / 1024).toFixed(1)} KB • ${file.type}</small>
                </div>
                <button type="button" class="btn-close file-remove" aria-label="حذف"></button>
            `;
            div.innerHTML = previewContent;
        }

        return div;
    },

    getFileIcon(fileType) {
        const iconMap = {
            'application/pdf': '📄',
            'application/msword': '📝',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝',
            'application/vnd.ms-excel': '📊',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊',
            'text/plain': '📄',
            'text/csv': '📊',
            'application/zip': '📦',
            'application/x-rar': '📦',
            default: '📎'
        };

        return iconMap[fileType] || iconMap.default;
    },

    // Table utilities
    initDataTable(selector, options = {}) {
        const defaultOptions = {
            searchable: true,
            sortable: true,
            paginated: true,
            perPage: 10,
            responsive: true,
            persistState: true
        };

        const config = { ...defaultOptions, ...options };
        const table = document.querySelector(selector);
        
        if (!table) return null;

        return new ProjectDataTable(table, config);
    }
};

// DataTable class
class ProjectDataTable {
    constructor(table, options) {
        this.table = table;
        this.options = options;
        this.currentPage = 1;
        this.rowsPerPage = options.perPage;
        this.sortColumn = 0;
        this.sortDirection = 'asc';
        this.filteredRows = [];
        this.stateKey = `datatable-${table.id || table.className}`;
        
        this.init();
    }

    init() {
        this.rows = Array.from(this.table.querySelectorAll('tbody tr'));
        this.headers = Array.from(this.table.querySelectorAll('thead th'));
        
        if (this.options.persistState) {
            this.loadState();
        }
        
        this.render();
        this.bindEvents();
        
        if (this.options.responsive) {
            this.makeResponsive();
        }
    }

    render() {
        // Filter rows if search is active
        if (this.searchQuery) {
            this.filteredRows = this.rows.filter(row => 
                Array.from(row.querySelectorAll('td')).some(cell => 
                    cell.textContent.toLowerCase().includes(this.searchQuery.toLowerCase())
                )
            );
        } else {
            this.filteredRows = [...this.rows];
        }

        // Sort rows
        this.sortRows();

        // Paginate
        const start = (this.currentPage - 1) * this.rowsPerPage;
        const end = start + this.rowsPerPage;
        const paginatedRows = this.filteredRows.slice(start, end);

        // Update table body
        const tbody = this.table.querySelector('tbody');
        tbody.innerHTML = '';

        paginatedRows.forEach(row => {
            tbody.appendChild(row.cloneNode(true));
        });

        // Update pagination
        this.updatePagination();
        
        // Save state
        if (this.options.persistState) {
            this.saveState();
        }
    }

    sortRows() {
        if (!this.options.sortable || this.sortColumn === -1) return;

        this.filteredRows.sort((a, b) => {
            const aCells = Array.from(a.querySelectorAll('td'));
            const bCells = Array.from(b.querySelectorAll('td'));
            
            let aText = aCells[this.sortColumn]?.textContent?.trim() || '';
            let bText = bCells[this.sortColumn]?.textContent?.trim() || '';
            
            // Handle numeric sorting
            const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // String sorting
            return this.sortDirection === 'asc' 
                ? aText.localeCompare(bText)
                : bText.localeCompare(aText);
        });
    }

    bindEvents() {
        // Header click for sorting
        if (this.options.sortable) {
            this.headers.forEach((header, index) => {
                if (!header.classList.contains('no-sort')) {
                    header.style.cursor = 'pointer';
                    header.addEventListener('click', () => this.handleSort(index));
                }
            });
        }

        // Search functionality
        const searchInput = this.table.parentNode.querySelector('.table-search');
        if (searchInput && this.options.searchable) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value;
                this.currentPage = 1;
                this.render();
            });
        }

        // Pagination events
        this.table.parentNode.addEventListener('click', (e) => {
            if (e.target.matches('[data-page]')) {
                this.currentPage = parseInt(e.target.getAttribute('data-page'));
                this.render();
            } else if (e.target.matches('.page-prev')) {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.render();
                }
            } else if (e.target.matches('.page-next')) {
                if (this.currentPage < this.totalPages) {
                    this.currentPage++;
                    this.render();
                }
            }
        });

        // Rows per page change
        const rowsPerPageSelect = this.table.parentNode.querySelector('.rows-per-page');
        if (rowsPerPageSelect) {
            rowsPerPageSelect.addEventListener('change', (e) => {
                this.rowsPerPage = parseInt(e.target.value);
                this.currentPage = 1;
                this.render();
            });
        }
    }

    handleSort(columnIndex) {
        if (this.sortColumn === columnIndex) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = columnIndex;
            this.sortDirection = 'asc';
        }

        // Update header indicators
        this.headers.forEach((header, index) => {
            header.innerHTML = header.innerHTML.replace(/<span class="sort-indicator">.*?<\/span>/, '');
            if (index === this.sortColumn) {
                const indicator = this.sortDirection === 'asc' ? '↑' : '↓';
                header.innerHTML += `<span class="sort-indicator ms-1">${indicator}</span>`;
            }
        });

        this.render();
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredRows.length / this.rowsPerPage);
        this.totalPages = totalPages;

        let paginationHTML = `
            <div class="d-flex justify-content-between align-items-center mt-3">
                <div class="d-flex align-items-center">
                    <span class="me-2">نمایش</span>
                    <select class="form-select form-select-sm rows-per-page" style="width: auto;">
                        <option value="5" ${this.rowsPerPage === 5 ? 'selected' : ''}>5</option>
                        <option value="10" ${this.rowsPerPage === 10 ? 'selected' : ''}>10</option>
                        <option value="25" ${this.rowsPerPage === 25 ? 'selected' : ''}>25</option>
                        <option value="50" ${this.rowsPerPage === 50 ? 'selected' : ''}>50</option>
                        <option value="100" ${this.rowsPerPage === 100 ? 'selected' : ''}>100</option>
                    </select>
                    <span class="ms-2">ردیف</span>
                </div>
        `;

        if (totalPages > 1) {
            const startItem = Math.max(1, this.currentPage - 2);
            const endItem = Math.min(totalPages, startItem + 4);

            paginationHTML += `
                <div class="d-flex align-items-center">
                    <span class="me-3">
                        ${this.currentPage} از ${totalPages} (کل: ${this.filteredRows.length})
                    </span>
                    <nav>
                        <ul class="pagination pagination-sm mb-0">
            `;

            // Previous button
            paginationHTML += `
                <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                    <button class="page-link page-prev" ${this.currentPage === 1 ? 'disabled' : ''}>
                        قبلی
                    </button>
                </li>
            `;

            // Page numbers
            for (let i = startItem; i <= endItem; i++) {
                paginationHTML += `
                    <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <button class="page-link" data-page="${i}">${i}</button>
                    </li>
                `;
            }

            // Next button
            paginationHTML += `
                <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                    <button class="page-link page-next" ${this.currentPage === totalPages ? 'disabled' : ''}>
                        بعدی
                    </button>
                </li>
            `;

            paginationHTML += `
                        </ul>
                    </nav>
                </div>
            `;
        }

        paginationHTML += '</div>';

        // Insert pagination
        let paginationContainer = this.table.parentNode.querySelector('.table-pagination');
        if (!paginationContainer) {
            paginationContainer = document.createElement('div');
            paginationContainer.className = 'table-pagination';
            this.table.parentNode.appendChild(paginationContainer);
        }
        
        paginationContainer.innerHTML = paginationHTML;
    }

    makeResponsive() {
        // Add horizontal scroll wrapper
        if (!this.table.parentNode.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            this.table.parentNode.insertBefore(wrapper, this.table);
            wrapper.appendChild(this.table);
        }

        // Add mobile-friendly attributes
        this.table.setAttribute('data-table-id', this.stateKey);
        
        // Add touch/swipe support for mobile
        let startX = 0;
        let startScrollLeft = 0;

        this.table.parentNode.addEventListener('touchstart', (e) => {
            startX = e.touches[0].pageX - this.table.parentNode.offsetLeft;
            startScrollLeft = this.table.scrollLeft;
        }, { passive: true });

        this.table.parentNode.addEventListener('touchmove', (e) => {
            const x = e.touches[0].pageX - this.table.parentNode.offsetLeft;
            const walk = (x - startX) * 2; // Scroll speed
            this.table.scrollLeft = startScrollLeft - walk;
        }, { passive: true });
    }

    saveState() {
        const state = {
            currentPage: this.currentPage,
            rowsPerPage: this.rowsPerPage,
            sortColumn: this.sortColumn,
            sortDirection: this.sortDirection,
            searchQuery: this.searchQuery || ''
        };
        
        localStorage.setItem(this.stateKey, JSON.stringify(state));
    }

    loadState() {
        try {
            const saved = localStorage.getItem(this.stateKey);
            if (saved) {
                const state = JSON.parse(saved);
                this.currentPage = state.currentPage || 1;
                this.rowsPerPage = state.rowsPerPage || this.options.perPage;
                this.sortColumn = state.sortColumn || 0;
                this.sortDirection = state.sortDirection || 'asc';
                this.searchQuery = state.searchQuery || '';
            }
        } catch (e) {
            console.warn('Failed to load datatable state:', e);
        }
    }

    destroy() {
        // Cleanup event listeners
        this.headers.forEach(header => {
            header.replaceWith(header.cloneNode(true));
        });

        // Remove pagination
        const pagination = this.table.parentNode.querySelector('.table-pagination');
        if (pagination) {
            pagination.remove();
        }

        // Clear saved state
        if (this.options.persistState) {
            localStorage.removeItem(this.stateKey);
        }

        // Remove responsive wrapper if empty
        const wrapper = this.table.parentNode;
        if (wrapper.classList.contains('table-responsive') && wrapper.children.length === 1) {
            wrapper.parentNode.insertBefore(this.table, wrapper);
            wrapper.remove();
        }
    }
}

// Auto-initialize utilities when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        ProjectUtils.init();
        ProjectUtils.initFileUpload();
    });
} else {
    ProjectUtils.init();
    ProjectUtils.initFileUpload();
}

// Expose to global scope for external access
window.ProjectUtils = ProjectUtils;
window.ProjectDataTable = ProjectDataTable;
