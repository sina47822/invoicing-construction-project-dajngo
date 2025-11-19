/**
 * Dashboard specific JavaScript functionality
 * Handles charts, statistics, quick actions, and dashboard interactions
 * Version: 1.0.0
 */

document.addEventListener('DOMContentLoaded', function() {
    Dashboard.init();
    
    // Listen for content updates
    document.addEventListener('content:loaded', () => {
        Dashboard.refresh();
    });
    
    // Periodic data refresh
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            Dashboard.refreshData();
        }
    }, 5 * 60 * 1000); // Refresh every 5 minutes
});

const Dashboard = {
    // Configuration
    config: {
        refreshInterval: 300000, // 5 minutes
        chartAnimationDuration: 1000,
        maxStatsHistory: 30, // Days
        defaultCurrency: 'تومان'
    },

    // State
    state: {
        chartsInitialized: false,
        statsLoaded: false,
        lastRefresh: null,
        isRefreshing: false
    },

    // Initialize dashboard
    init() {
        this.initializeCharts();
        this.initializeStatsCards();
        this.initializeQuickActions();
        this.initializeRecentActivity();
        this.initializeProjectOverview();
        this.setupEventListeners();
        this.loadInitialData();
        
        // Mark as initialized
        this.state.chartsInitialized = true;
        console.log('Dashboard initialized successfully');
    },

    // Initialize all charts
    initializeCharts() {
        const chartContainers = document.querySelectorAll('.chart-container');
        
        if (chartContainers.length === 0) {
            console.warn('No chart containers found');
            return;
        }

        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            this.showChartError('کتابخانه نمودارها بارگیری نشده است');
            return;
        }

        chartContainers.forEach(container => {
            const chartType = container.getAttribute('data-chart-type') || 'line';
            const chartId = container.getAttribute('data-chart-id');
            const chartDataAttr = container.getAttribute('data-chart-data');
            
            if (!chartId) {
                console.warn('Chart container missing data-chart-id:', container);
                return;
            }

            try {
                let chartData;
                
                // Try to get data from data attribute
                if (chartDataAttr) {
                    try {
                        chartData = JSON.parse(chartDataAttr);
                    } catch (e) {
                        console.warn('Failed to parse chart data:', e);
                    }
                }

                // If no data, fetch from API
                if (!chartData || chartData.length === 0) {
                    chartData = this.generateDefaultChartData(chartType, chartId);
                }

                this.createChart(chartId, chartType, chartData, container);
            } catch (error) {
                console.error('Failed to initialize chart:', chartId, error);
                this.showChartError(`خطا در ایجاد نمودار: ${chartId}`, container);
            }
        });

        MainApp.logEvent('charts_initialized', {
            count: chartContainers.length
        });
    },

    createChart(chartId, chartType, data, container) {
        const canvas = container.querySelector('canvas');
        if (!canvas) {
            console.warn('No canvas found for chart:', chartId);
            return null;
        }

        // Prepare chart configuration
        const config = this.getChartConfig(chartType, data, chartId);
        
        // Destroy existing chart if present
        if (window.dashboardCharts && window.dashboardCharts[chartId]) {
            window.dashboardCharts[chartId].destroy();
        }

        // Create new chart
        const chart = new Chart(canvas, config);
        
        // Store reference
        if (!window.dashboardCharts) {
            window.dashboardCharts = {};
        }
        window.dashboardCharts[chartId] = chart;

        // Add chart interactions
        this.addChartInteractions(chart, container);

        // Animate chart appearance
        this.animateChart(container);

        return chart;
    },

    getChartConfig(type, data, chartId) {
        const baseConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: type !== 'pie' && type !== 'doughnut',
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12,
                            family: "'Vazir', sans-serif"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#0d6efd',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: (context) => {
                            return this.formatTooltipTitle(context[0].label);
                        },
                        label: (context) => {
                            return `${context.dataset.label || ''}: ${this.formatNumber(context.parsed.y)}`;
                        },
                        afterLabel: (context) => {
                            if (type === 'pie' || type === 'doughnut') {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${percentage}%`;
                            }
                            return '';
                        }
                    }
                },
                title: {
                    display: true,
                    text: this.getChartTitle(chartId),
                    font: {
                        size: 16,
                        weight: 'bold',
                        family: "'Vazir', sans-serif"
                    },
                    padding: {
                        top: 10,
                        bottom: 20
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: type !== 'pie' && type !== 'doughnut' ? {
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: "'Vazir', sans-serif"
                        },
                        maxTicksLimit: 10,
                        callback: (value, index, values) => {
                            return this.formatXAxisLabel(value, index);
                        }
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: "'Vazir', sans-serif"
                        },
                        callback: (value) => {
                            return this.formatNumber(value, true);
                        }
                    }
                }
            } : {},
            animation: {
                duration: this.config.chartAnimationDuration,
                easing: 'easeOutQuart'
            },
            elements: {
                point: {
                    radius: 4,
                    hoverRadius: 6
                },
                line: {
                    tension: 0.4,
                    borderWidth: 3
                },
                bar: {
                    borderRadius: 4,
                    borderSkipped: false
                }
            }
        };

        // Type-specific configuration
        switch (type) {
            case 'line':
                return {
                    ...baseConfig,
                    data: {
                        labels: data.labels || [],
                        datasets: this.prepareLineDatasets(data.datasets || [])
                    },
                    options: {
                        ...baseConfig,
                        scales: {
                            ...baseConfig.scales,
                            y: {
                                ...baseConfig.scales.y,
                                grace: '5%'
                            }
                        },
                        plugins: {
                            ...baseConfig.plugins,
                            legend: {
                                ...baseConfig.plugins.legend,
                                display: data.datasets && data.datasets.length > 1
                            }
                        }
                    },
                    type: 'line'
                };

            case 'bar':
                return {
                    ...baseConfig,
                    data: {
                        labels: data.labels || [],
                        datasets: this.prepareBarDatasets(data.datasets || [])
                    },
                    options: {
                        ...baseConfig,
                        scales: {
                            ...baseConfig.scales,
                            x: {
                                ...baseConfig.scales.x,
                                stacked: data.stacked
                            },
                            y: {
                                ...baseConfig.scales.y,
                                stacked: data.stacked,
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            ...baseConfig.plugins,
                            legend: {
                                ...baseConfig.plugins.legend,
                                display: data.datasets && data.datasets.length > 1
                            }
                        }
                    },
                    type: 'bar'
                };

            case 'pie':
            case 'doughnut':
                return {
                    ...baseConfig,
                    data: {
                        labels: data.labels || [],
                        datasets: [{
                            data: data.data || [],
                            backgroundColor: this.getChartColors(data.labels.length),
                            borderColor: '#fff',
                            borderWidth: 2,
                            hoverOffset: 10
                        }]
                    },
                    options: {
                        ...baseConfig,
                        cutout: type === 'doughnut' ? '50%' : '0%',
                        plugins: {
                            ...baseConfig.plugins,
                            legend: {
                                ...baseConfig.plugins.legend,
                                position: 'right'
                            },
                            tooltip: {
                                ...baseConfig.plugins.tooltip,
                                callbacks: {
                                    ...baseConfig.plugins.tooltip.callbacks,
                                    label: (context) => {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                                        return `${context.label}: ${this.formatNumber(context.parsed)} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    },
                    type: type
                };

            case 'radar':
                return {
                    ...baseConfig,
                    data: {
                        labels: data.labels || [],
                        datasets: this.prepareRadarDatasets(data.datasets || [])
                    },
                    options: {
                        ...baseConfig,
                        scales: {
                            r: {
                                beginAtZero: true,
                                max: Math.max(...data.data) * 1.1,
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.05)'
                                },
                                ticks: {
                                    font: {
                                        family: "'Vazir', sans-serif"
                                    },
                                    stepSize: 10
                                },
                                pointLabels: {
                                    font: {
                                        family: "'Vazir', sans-serif"
                                    }
                                }
                            }
                        }
                    },
                    type: 'radar'
                };

            default:
                console.warn('Unknown chart type:', type);
                return this.getChartConfig('line', data, chartId);
        }
    },

    prepareLineDatasets(datasets) {
        return datasets.map((dataset, index) => ({
            label: dataset.label || `داده ${index + 1}`,
            data: dataset.data || [],
            borderColor: this.getDatasetColor(index),
            backgroundColor: this.getDatasetColor(index, 0.1),
            fill: dataset.fill !== false,
            tension: 0.4,
            pointBackgroundColor: this.getDatasetColor(index),
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: this.getDatasetColor(index)
        }));
    },

    prepareBarDatasets(datasets) {
        return datasets.map((dataset, index) => ({
            label: dataset.label || `داده ${index + 1}`,
            data: dataset.data || [],
            backgroundColor: this.getDatasetColor(index, 0.8),
            borderColor: this.getDatasetColor(index),
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false
        }));
    },

    prepareRadarDatasets(datasets) {
        return datasets.map((dataset, index) => ({
            label: dataset.label || `داده ${index + 1}`,
            data: dataset.data || [],
            borderColor: this.getDatasetColor(index),
            backgroundColor: this.getDatasetColor(index, 0.2),
            pointBackgroundColor: this.getDatasetColor(index),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: this.getDatasetColor(index),
            tension: 0.4,
            fill: true
        }));
    },

    getChartColors(count) {
        const colors = [
            'rgba(13, 110, 253, 0.8)',   // Primary
            'rgba(25, 135, 84, 0.8)',    // Success
            'rgba(255, 193, 7, 0.8)',    // Warning
            'rgba(220, 53, 69, 0.8)',    // Danger
            'rgba(108, 117, 125, 0.8)',  // Secondary
            'rgba(0, 123, 255, 0.8)',    // Info
            'rgba(40, 167, 69, 0.8)',    // Success variant
            'rgba(255, 152, 0, 0.8)',    // Orange
            'rgba(153, 102, 255, 0.8)',  // Purple
            'rgba(52, 152, 219, 0.8)',   // Blue
            'rgba(231, 76, 60, 0.8)',    // Red
            'rgba(46, 204, 113, 0.8)'    // Green
        ];

        if (!count) count = 1;
        return colors.slice(0, count);
    },

    getDatasetColor(index, alpha = 1) {
        const colors = [
            `rgba(13, 110, 253, ${alpha})`,   // Primary
            `rgba(25, 135, 84, ${alpha})`,    // Success
            `rgba(255, 193, 7, ${alpha})`,    // Warning
            `rgba(220, 53, 69, ${alpha})`,    // Danger
            `rgba(108, 117, 125, ${alpha})`,  // Secondary
            `rgba(0, 123, 255, ${alpha})`,    // Info
            `rgba(40, 167, 69, ${alpha})`,    // Success variant
            `rgba(255, 152, 0, ${alpha})`,    // Orange
            `rgba(153, 102, 255, ${alpha})`,  // Purple
            `rgba(52, 152, 219, ${alpha})`    // Blue
        ];

        return colors[index % colors.length];
    },

    getChartTitle(chartId) {
        const titles = {
            'project-progress': 'پیشرفت پروژه‌ها',
            'financial-overview': 'بررسی مالی',
            'team-performance': 'عملکرد تیم',
            'task-completion': 'تکمیل وظایف',
            'revenue-trend': 'روند درآمد',
            'expense-analysis': 'تحلیل هزینه‌ها',
            'user-activity': 'فعالیت کاربران',
            default: 'نمودار'
        };

        return titles[chartId] || titles.default;
    },

    generateDefaultChartData(type, chartId) {
        const now = new Date();
        const labels = [];
        
        // Generate time-based labels
        if (type === 'line' || type === 'bar') {
            for (let i = 6; i >= 0; i--) {
                const date = new Date(now);
                date.setDate(date.getDate() - i);
                labels.push(date.toLocaleDateString('fa-IR', { 
                    month: 'short', 
                    day: 'numeric' 
                }));
            }
        } else {
            labels = ['دسته 1', 'دسته 2', 'دسته 3', 'دسته 4', 'دسته 5', 'دسته 6'];
        }

        const baseData = Array(labels.length).fill(0).map(() => 
            Math.floor(Math.random() * 100) + 20
        );

        switch (chartId) {
            case 'project-progress':
                return {
                    labels: labels,
                    datasets: [{
                        label: 'درصد پیشرفت',
                        data: baseData.map(val => val * 0.8 + 20), // 20-100%
                        fill: true
                    }]
                };

            case 'financial-overview':
                return {
                    labels: labels,
                    datasets: [
                        {
                            label: 'درآمد',
                            data: baseData.map(val => val * 1000 + 50000),
                            fill: false
                        },
                        {
                            label: 'هزینه',
                            data: baseData.map(val => val * 800 + 30000),
                            fill: false
                        }
                    ]
                };

            case 'team-performance':
                return {
                    labels: ['احمد', 'مریم', 'علی', 'فاطمه', 'حسن', 'زهرا'],
                    datasets: [{
                        label: 'امتیاز عملکرد',
                        data: [85, 92, 78, 95, 88, 91],
                        backgroundColor: this.getChartColors(6)
                    }],
                    type: 'bar'
                };

            case 'task-completion':
                return {
                    labels: labels,
                    datasets: [{
                        label: 'وظایف تکمیل شده',
                        data: baseData.map(val => Math.floor(val / 3)),
                        backgroundColor: this.getChartColors(1)
                    }],
                    type: 'line'
                };

            case 'revenue-trend':
                return {
                    labels: ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور'],
                    datasets: [{
                        data: [120, 190, 300, 500, 200, 300],
                        backgroundColor: this.getChartColors(1)
                    }],
                    type: 'doughnut'
                };

            default:
                return {
                    labels: labels,
                    datasets: [{
                        label: 'داده‌های نمونه',
                        data: baseData,
                        fill: true
                    }],
                    type: type
                };
        }
    },

    formatTooltipTitle(label) {
        // Persian date formatting for tooltips
        if (label.match(/^\d{1,2}\/\d{1,2}$/)) {
            // Already formatted as Persian date
            return label;
        }
        
        if (label.match(/^\d{4}\/\d{1,2}\/\d{1,2}$/)) {
            // Jalali date
            return label;
        }
        
        // Format English date to Persian
        try {
            const date = new Date(label);
            if (!isNaN(date.getTime())) {
                const jalali = ProjectUtils.gregorianToJalali(
                    date.getFullYear(), 
                    date.getMonth() + 1, 
                    date.getDate()
                );
                return `${jalali.day}/${jalali.month}`;
            }
        } catch (e) {
            // Fall back to original label
        }
        
        return label;
    },

    formatXAxisLabel(value, index) {
        // Limit labels to prevent overcrowding
        if (index % 2 === 1) return '';
        
        // Format numbers and dates
        if (typeof value === 'number') {
            return ProjectUtils.toPersianDigits(value.toFixed(0));
        }
        
        return value;
    },

    formatNumber(value, compact = false) {
        if (value === null || value === undefined) return '0';
        
        const num = parseFloat(value);
        if (isNaN(num)) return value;
        
        if (compact) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
        }
        
        return ProjectUtils.toPersianDigits(num.toLocaleString('fa-IR'));
    },

    addChartInteractions(chart, container) {
        const canvas = container.querySelector('canvas');
        
        // Hover effects
        canvas.addEventListener('mouseenter', () => {
            container.style.transform = 'translateY(-2px)';
            container.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
            container.style.transition = 'all 0.3s ease';
        });

        canvas.addEventListener('mouseleave', () => {
            container.style.transform = 'translateY(0)';
            container.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
        });

        // Click to drill down (if data-url is present)
        canvas.addEventListener('click', (e) => {
            const url = container.getAttribute('data-chart-url');
            if (url) {
                const activeElement = chart.getActiveElements()[0];
                if (activeElement) {
                    const index = activeElement.index;
                    const query = new URLSearchParams({
                        period: index,
                        chart: container.getAttribute('data-chart-id')
                    });
                    window.location.href = `${url}?${query.toString()}`;
                } else {
                    window.location.href = url;
                }
            }
        });

        // Export functionality
        const exportBtn = container.parentNode.querySelector('.chart-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportChart(chart, container.getAttribute('data-chart-id'));
            });
        }
    },

    animateChart(container) {
        // Animate chart appearance
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
            container.style.transition = 'all 0.6s ease-out';
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        });
    },

    showChartError(message, container) {
        const canvas = container.querySelector('canvas');
        if (canvas) {
            canvas.style.display = 'none';
        }

        const errorDiv = document.createElement('div');
        errorDiv.className = 'chart-error text-center p-4';
        errorDiv.style.cssText = `
            background: #ffffff;
            border: 2px dashed #dee2e6;
            border-radius: 0.75rem;
            color: #6c757d;
        `;
        errorDiv.innerHTML = `
            <i class="bi bi-graph-down display-4 mb-3 text-muted"></i>
            <div class="h6 mb-2">${message}</div>
            <small>لطفاً صفحه را رفرش کنید</small>
            <button class="btn btn-outline-primary btn-sm mt-2" onclick="Dashboard.refreshChart(this.parentNode.parentNode.getAttribute('data-chart-id'))">
                تلاش مجدد
            </button>
        `;
        
        container.appendChild(errorDiv);
    },

    // Initialize statistics cards
    initializeStatsCards() {
        const statCards = document.querySelectorAll('.stat-card');
        
        statCards.forEach(card => {
            // Add hover animation
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
                card.style.transition = 'transform 0.2s ease';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });

            // Add click handler for detail view
            const detailLink = card.getAttribute('data-detail-url');
            if (detailLink) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', (e) => {
                    if (!e.target.closest('.dropdown, .btn')) {
                        window.location.href = detailLink;
                    }
                });
            }

            // Initialize counter animation
            const counterEl = card.querySelector('.stat-number');
            if (counterEl) {
                this.animateCounter(counterEl);
            }
        });

        // Add sparkle effect to cards
        this.addSparkleEffect(statCards);
    },

    animateCounter(element) {
        const targetValue = parseInt(element.getAttribute('data-target-value')) || 
                           parseInt(element.textContent.replace(/[^\d]/g, '')) || 0;
        const duration = 2000; // 2 seconds
        const startTime = null;
        let currentValue = 0;

        const updateCounter = (currentTime) => {
            if (!startTime) startTime = currentTime;
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (easeOutQuad)
            const easeOut = 1 - (1 - progress) * (1 - progress);
            currentValue = easeOut * targetValue;
            
            const formattedValue = this.formatNumber(Math.floor(currentValue));
            element.textContent = formattedValue;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                // Ensure exact value
                element.textContent = this.formatNumber(targetValue);
                element.setAttribute('data-current-value', targetValue);
            }
        };

        // Start animation when element comes into view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    requestAnimationFrame(updateCounter);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        observer.observe(element);
    },

    addSparkleEffect(cards) {
        cards.forEach((card, index) => {
            // Create sparkle element
            const sparkle = document.createElement('div');
            sparkle.className = 'stat-sparkle';
            sparkle.style.cssText = `
                position: absolute;
                top: -10px;
                right: -10px;
                width: 20px;
                height: 20px;
                background: linear-gradient(45deg, #ffd700, #ffed4e);
                border-radius: 50% 0;
                opacity: 0;
                transform: rotate(45deg) scale(0);
                z-index: 10;
                pointer-events: none;
            `;
            
            card.appendChild(sparkle);
            
            // Animate on hover
            card.addEventListener('mouseenter', () => {
                sparkle.style.opacity = '1';
                sparkle.style.transform = 'rotate(45deg) scale(1)';
                sparkle.style.transition = 'all 0.3s ease';
                
                // Add glow effect
                card.style.boxShadow = '0 0 20px rgba(255, 215, 0, 0.3)';
            });

            card.addEventListener('mouseleave', () => {
                sparkle.style.opacity = '0';
                sparkle.style.transform = 'rotate(45deg) scale(0)';
                card.style.boxShadow = '';
            });
        });
    },

    // Initialize quick actions
    initializeQuickActions() {
        const actionItems = document.querySelectorAll('.action-item');
        
        actionItems.forEach(item => {
            // Add click ripple effect
            item.addEventListener('click', (e) => {
                this.createRippleEffect(e, item);
                
                // Delay for visual feedback
                setTimeout(() => {
                    const url = item.getAttribute('href') || item.getAttribute('data-action-url');
                    if (url && !item.classList.contains('disabled')) {
                        if (item.hasAttribute('data-confirm')) {
                            const message = item.getAttribute('data-confirm');
                            ProjectUtils.confirmAction(message).then(() => {
                                window.location.href = url;
                            });
                        } else {
                            window.location.href = url;
                        }
                    }
                }, 200);
            });

            // Add loading state
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'action-loading';
            loadingIndicator.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 20px;
                height: 20px;
                border: 2px solid transparent;
                border-top: 2px solid currentColor;
                border-radius: 50%;
                opacity: 0;
                transition: opacity 0.2s ease;
            `;
            item.appendChild(loadingIndicator);

            // Disabled state
            if (item.classList.contains('disabled')) {
                item.style.opacity = '0.6';
                item.style.cursor = 'not-allowed';
            }
        });

        // Add grid animation
        const actionsGrid = document.querySelector('.actions-grid');
        if (actionsGrid) {
            this.animateGridItems(actionsGrid);
        }
    },

    createRippleEffect(event, element) {
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: currentColor;
            border-radius: 50%;
            transform: scale(0);
            opacity: 0.6;
            pointer-events: none;
            animation: ripple 0.6s linear;
            z-index: 1;
        `;

        // Add ripple animation
        if (!document.getElementById('ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'ripple-styles';
            style.textContent = `
                @keyframes ripple {
                    to {
                        transform: scale(4);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(ripple);

        // Clean up
        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 600);
    },

    animateGridItems(container) {
        const items = container.querySelectorAll('.action-item');
        items.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px)';
            
            requestAnimationFrame(() => {
                item.style.transition = `all 0.6s ease ${index * 0.1}s`;
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            });
        });
    },

    // Initialize recent activity
    initializeRecentActivity() {
        const activityContainer = document.querySelector('.recent-activity');
        if (!activityContainer) return;

        // Add smooth scrolling for activity list
        const activityList = activityContainer.querySelector('.activity-list');
        if (activityList) {
            activityList.style.overflowY = 'auto';
            activityList.style.maxHeight = '400px';
            
            // Custom scrollbar
            activityList.style.scrollbarWidth = 'thin';
            activityList.style.scrollbarColor = '#dee2e6 #ffffff';
        }

        // Add activity animations
        const activityItems = activityContainer.querySelectorAll('.activity-item');
        activityItems.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            
            requestAnimationFrame(() => {
                item.style.transition = `all 0.5s ease ${index * 0.1}s`;
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            });

            // Add click handlers
            const link = item.querySelector('a');
            if (link && link.href !== '#') {
                item.style.cursor = 'pointer';
                item.addEventListener('click', (e) => {
                    if (!e.target.closest('.dropdown')) {
                        window.location.href = link.href;
                    }
                });
            }
        });

        // Auto-scroll to recent activity every 30 seconds (optional)
        // this.startActivityAutoScroll(activityContainer);
    },

    startActivityAutoScroll(container) {
        let scrollInterval;
        let isHovered = false;

        container.addEventListener('mouseenter', () => {
            isHovered = true;
            clearInterval(scrollInterval);
        });

        container.addEventListener('mouseleave', () => {
            isHovered = false;
            scrollInterval = setInterval(() => {
                if (!isHovered) {
                    const list = container.querySelector('.activity-list');
                    if (list) {
                        list.scrollTop += 1;
                        if (list.scrollTop >= list.scrollHeight - list.clientHeight) {
                            list.scrollTop = 0;
                        }
                    }
                }
            }, 50);
        });

        // Stop auto-scroll when user manually scrolls
        const list = container.querySelector('.activity-list');
        if (list) {
            list.addEventListener('scroll', () => {
                clearInterval(scrollInterval);
                setTimeout(() => {
                    if (!isHovered) {
                        scrollInterval = setInterval(() => {
                            if (!isHovered) {
                                list.scrollTop += 1;
                                if (list.scrollTop >= list.scrollHeight - list.clientHeight) {
                                    list.scrollTop = 0;
                                }
                            }
                        }, 50);
                    }
                }, 3000);
            });
        }
    },

    // Initialize project overview
    initializeProjectOverview() {
        const overviewContainer = document.querySelector('.project-overview');
        if (!overviewContainer) return;

        // Initialize progress bars
        const progressBars = overviewContainer.querySelectorAll('.progress');
        progressBars.forEach(bar => {
            const progress = bar.querySelector('.progress-bar');
            if (progress) {
                const targetWidth = parseInt(progress.getAttribute('data-progress')) || 0;
                progress.style.width = '0%';
                
                // Animate progress
                setTimeout(() => {
                    progress.style.transition = 'width 1.5s ease-out';
                    progress.style.width = `${targetWidth}%`;
                    
                    // Add percentage text
                    const percentage = progress.getAttribute('data-progress-text') || 
                                     progress.getAttribute('aria-valuetext') || 
                                     `${targetWidth}%`;
                    progress.setAttribute('aria-valuetext', percentage);
                }, 500);
            }
        });

        // Add project status interactions
        const statusItems = overviewContainer.querySelectorAll('.status-item');
        statusItems.forEach(item => {
            item.addEventListener('click', () => {
                const detailUrl = item.getAttribute('data-detail-url');
                if (detailUrl) {
                    window.location.href = detailUrl;
                }
            });
        });

        // Update project status colors
        this.updateStatusColors(overviewContainer);
    },

    updateStatusColors(container) {
        const statusItems = container.querySelectorAll('.status-item');
        statusItems.forEach(item => {
            const value = parseInt(item.querySelector('.status-number')?.textContent) || 0;
            const maxValue = parseInt(item.getAttribute('data-max-value')) || 100;
            const percentage = (value / maxValue) * 100;

            let colorClass = '';
            if (percentage >= 80) {
                colorClass = 'text-success';
            } else if (percentage >= 60) {
                colorClass = 'text-warning';
            } else {
                colorClass = 'text-danger';
            }

            // Update status number color
            const statusNumber = item.querySelector('.status-number');
            if (statusNumber) {
                statusNumber.className = `status-number ${colorClass} fw-bold`;
            }

            // Update status label color
            const statusLabel = item.querySelector('.status-label');
            if (statusLabel) {
                statusLabel.className = `status-label ${colorClass}`;
            }
        });
    },

    // Setup event listeners
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.querySelector('#dashboard-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refresh();
            });
        }

        // Stats period selector
        const periodSelector = document.querySelector('#stats-period');
        if (periodSelector) {
            periodSelector.addEventListener('change', (e) => {
                this.updateStatsPeriod(e.target.value);
            });
        }

        // Export dashboard
        const exportBtn = document.querySelector('#dashboard-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportDashboard();
            });
        }

        // Theme switcher
        const themeToggle = document.querySelector('#theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('change', (e) => {
                this.toggleTheme(e.target.checked);
            });
        }

        // Dashboard resize observer
        if ('ResizeObserver' in window) {
            const resizeObserver = new ResizeObserver((entries) => {
                entries.forEach(entry => {
                    const width = entry.contentRect.width;
                    this.adjustDashboardLayout(width);
                });
            });

            const dashboardContainer = document.querySelector('.dashboard-container');
            if (dashboardContainer) {
                resizeObserver.observe(dashboardContainer);
            }
        }
    },

    // Load initial data
    loadInitialData() {
        this.refreshData()
            .then(() => {
                this.state.statsLoaded = true;
                this.state.lastRefresh = new Date().toISOString();
                
                // Update last refresh time
                const lastRefreshEl = document.querySelector('#last-refresh');
                if (lastRefreshEl) {
                    lastRefreshEl.textContent = `آخرین به‌روزرسانی: ${new Date().toLocaleTimeString('fa-IR')}`;
                }
                
                console.log('Dashboard data loaded successfully');
            })
            .catch(error => {
                console.error('Failed to load initial dashboard data:', error);
                this.showDataError('خطا در بارگیری داده‌های داشبورد');
            });
    },

    // Refresh dashboard data
    refreshData() {
        if (this.state.isRefreshing) {
            return Promise.reject(new Error('Already refreshing'));
        }

        this.state.isRefreshing = true;
        
        // Show loading state
        const loadingElements = document.querySelectorAll('.dashboard-loading');
        loadingElements.forEach(el => {
            el.style.display = 'block';
        });

        // Update stats cards
        const statsPromises = Array.from(document.querySelectorAll('.stat-card[data-api-url]'))
            .map(card => this.refreshStatCard(card));

        // Refresh charts
        const chartPromises = Array.from(document.querySelectorAll('.chart-container[data-api-url]'))
            .map(container => this.refreshChartData(container));

        // Refresh recent activity
        const activityPromise = this.refreshRecentActivity();

        // Wait for all promises to complete
        return Promise.all([
            ...statsPromises,
            ...chartPromises,
            activityPromise
        ])
        .then(results => {
            // Hide loading states
            loadingElements.forEach(el => {
                el.style.display = 'none';
            });

            // Animate refreshed content
            this.animateRefreshedContent();

            this.state.isRefreshing = false;
            
            MainApp.logEvent('dashboard_refreshed', {
                statsUpdated: results.filter(r => r.type === 'stat').length,
                chartsUpdated: results.filter(r => r.type === 'chart').length,
                timestamp: new Date().toISOString()
            });

            return results;
        })
        .catch(error => {
            console.error('Dashboard refresh error:', error);
            this.state.isRefreshing = false;
            
            loadingElements.forEach(el => {
                el.style.display = 'none';
            });

            throw error;
        });
    },

    refreshStatCard(card) {
        const apiUrl = card.getAttribute('data-api-url');
        const statNumber = card.querySelector('.stat-number');
        const statLabel = card.querySelector('.stat-label');

        if (!apiUrl || !statNumber) {
            return Promise.resolve({ type: 'stat', success: false });
        }

        return ProjectUtils.makeAjaxRequest(apiUrl, {
            method: 'GET',
            timeout: 5000
        })
        .then(response => {
            if (response.data.value !== undefined) {
                const newValue = response.data.value;
                statNumber.setAttribute('data-target-value', newValue);
                
                // Re-animate counter
                this.animateCounter(statNumber);
                
                // Update label if provided
                if (response.data.label && statLabel) {
                    statLabel.textContent = response.data.label;
                }
                
                // Update trend indicator
                if (response.data.trend) {
                    this.updateTrendIndicator(card, response.data.trend);
                }
            }
            
            return { type: 'stat', success: true, card };
        })
        .catch(error => {
            console.error('Failed to refresh stat card:', error);
            return { type: 'stat', success: false, card, error };
        });
    },

    refreshChartData(container) {
        const apiUrl = container.getAttribute('data-api-url');
        const chartId = container.getAttribute('data-chart-id');

        if (!apiUrl || !chartId) {
            return Promise.resolve({ type: 'chart', success: false });
        }

        return ProjectUtils.makeAjaxRequest(apiUrl, {
            method: 'GET',
            timeout: 8000
        })
        .then(response => {
            if (response.data && response.data.labels && response.data.datasets) {
                // Update chart
                const chart = window.dashboardCharts && window.dashboardCharts[chartId];
                if (chart) {
                    chart.data.labels = response.data.labels;
                    chart.data.datasets = this.prepareChartDatasets(response.data.datasets, chart.config.type);
                    chart.update('none'); // Update without animation
                }
                
                return { type: 'chart', success: true, container, data: response.data };
            }
            
            return { type: 'chart', success: false };
        })
        .catch(error => {
            console.error('Failed to refresh chart data:', error);
            return { type: 'chart', success: false, container, error };
        });
    },

    refreshRecentActivity() {
        const container = document.querySelector('.recent-activity');
        if (!container || !container.hasAttribute('data-api-url')) {
            return Promise.resolve({ type: 'activity', success: false });
        }

        const apiUrl = container.getAttribute('data-api-url');
        const activityList = container.querySelector('.activity-list');

        return ProjectUtils.makeAjaxRequest(apiUrl, {
            method: 'GET',
            timeout: 5000
        })
        .then(response => {
            if (response.data && response.data.activities) {
                activityList.innerHTML = '';
                
                response.data.activities.forEach((activity, index) => {
                    const activityItem = this.createActivityItem(activity, index);
                    activityList.appendChild(activityItem);
                });

                // Animate new items
                this.animateActivityItems(activityList);
                
                return { type: 'activity', success: true, count: response.data.activities.length };
            }
            
            return { type: 'activity', success: false };
        })
        .catch(error => {
            console.error('Failed to refresh recent activity:', error);
            return { type: 'activity', success: false, error };
        });
    },

    createActivityItem(activity, index) {
        const div = document.createElement('div');
        div.className = `activity-item p-3 ${index % 2 === 0 ? 'bg-light' : ''}`;
        div.style.cssText = `
            border-bottom: 1px solid #f1f3f4;
            transition: all 0.2s ease;
            opacity: 0;
            transform: translateX(${index * 10}px);
        `;

        const iconClass = this.getActivityIcon(activity.type);
        const timeAgo = this.formatTimeAgo(activity.timestamp);

        div.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="activity-icon flex-shrink-0 me-3 ${iconClass.color}">
                    <i class="bi ${iconClass.icon} fs-4"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <div class="fw-semibold text-dark">${activity.title}</div>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                    <div class="activity-description text-muted small">${activity.description}</div>
                    ${activity.user ? `<div class="mt-1"><small class="text-muted">توسط ${activity.user}</small></div>` : ''}
                </div>
            </div>
        `;

        // Add click handler if URL present
        if (activity.url) {
            div.style.cursor = 'pointer';
            div.addEventListener('click', () => {
                window.location.href = activity.url;
            });

            // Add hover effect
            div.addEventListener('mouseenter', () => {
                div.style.backgroundColor = '#ffffff';
                div.style.borderRadius = '0.5rem';
                div.style.margin = '0 -0.75rem';
                div.style.transform = 'translateX(5px)';
            });

            div.addEventListener('mouseleave', () => {
                div.style.backgroundColor = index % 2 === 0 ? '#ffffff' : 'transparent';
                div.style.borderRadius = '';
                div.style.margin = '';
                div.style.transform = 'translateX(0)';
            });
        }

        return div;
    },

    getActivityIcon(type) {
        const icons = {
            project: { color: 'text-primary', icon: 'bi-building' },
            task: { color: 'text-success', icon: 'bi-check-circle' },
            meeting: { color: 'text-info', icon: 'bi-calendar-event' },
            financial: { color: 'text-warning', icon: 'bi-currency-dollar' },
            user: { color: 'text-primary', icon: 'bi-person' },
            system: { color: 'text-muted', icon: 'bi-gear' },
            error: { color: 'text-danger', icon: 'bi-exclamation-triangle' },
            default: { color: 'text-muted', icon: 'bi-circle' }
        };

        return icons[type] || icons.default;
    },

    formatTimeAgo(timestamp) {
        const now = new Date();
        const activityTime = new Date(timestamp);
        const diffInMinutes = (now - activityTime) / (1000 * 60);

        if (diffInMinutes < 1) {
            return 'همین الان';
        } else if (diffInMinutes < 60) {
            return `${Math.floor(diffInMinutes)} دقیقه پیش`;
        } else if (diffInMinutes < 1440) {
            return `${Math.floor(diffInMinutes / 60)} ساعت پیش`;
        } else {
            return `${Math.floor(diffInMinutes / 1440)} روز پیش`;
        }
    },

    animateActivityItems(container) {
        const items = container.querySelectorAll('.activity-item');
        items.forEach((item, index) => {
            requestAnimationFrame(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
                item.style.transition = `all 0.5s ease ${index * 0.1}s`;
            });
        });
    },

    // Update stats period
    updateStatsPeriod(period) {
        const statsCards = document.querySelectorAll('.stat-card[data-period]');
        const loadingIndicator = document.querySelector('.stats-loading');
        
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }

        // Update each stat card for new period
        const updatePromises = Array.from(statsCards).map(card => {
            const currentPeriod = card.getAttribute('data-period');
            card.setAttribute('data-period', period);
            
            const apiUrl = card.getAttribute('data-api-url');
            if (apiUrl) {
                // Add period parameter to URL
                const url = new URL(apiUrl, window.location.origin);
                url.searchParams.set('period', period);
                
                return ProjectUtils.makeAjaxRequest(url.toString(), {
                    method: 'GET'
                })
                .then(response => {
                    const statNumber = card.querySelector('.stat-number');
                    if (statNumber && response.data.value !== undefined) {
                        statNumber.setAttribute('data-target-value', response.data.value);
                        this.animateCounter(statNumber);
                    }
                });
            }
            
            return Promise.resolve();
        });

        Promise.all(updatePromises)
            .then(() => {
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                
                ProjectUtils.showToast(`داده‌های آماری برای ${period} به‌روزرسانی شد`, 'success');
            })
            .catch(error => {
                console.error('Failed to update stats period:', error);
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            });
    },

    // Export functionality
    exportDashboard(format = 'pdf') {
        const exportBtn = document.querySelector('#dashboard-export');
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>در حال تهیه...';
        }

        // Create export data
        const exportData = {
            title: document.title,
            timestamp: new Date().toISOString(),
            format: format,
            stats: this.collectStatsData(),
            charts: this.collectChartsData(),
            user: MainApp.state.currentUser ? {
                id: MainApp.state.currentUser.id,
                name: MainApp.state.currentUser.get_full_name || MainApp.state.currentUser.username
            } : null
        };

        // Send to export API
        ProjectUtils.makeAjaxRequest('/api/dashboard/export/', {
            method: 'POST',
            data: exportData,
            timeout: 30000,
            responseType: 'blob' // For file download
        })
        .then(response => {
            this.downloadExportFile(response, format);
            ProjectUtils.showToast('فایل صادر شد', 'success');
        })
        .catch(error => {
            console.error('Export failed:', error);
            ProjectUtils.showToast('خطا در صدور فایل', 'danger');
        })
        .finally(() => {
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.innerHTML = '<i class="bi bi-download"></i> صدور داشبورد';
            }
        });
    },

    exportChart(chart, chartId) {
        const container = document.querySelector(`[data-chart-id="${chartId}"]`);
        if (!container) return;

        // Create temporary canvas for export
        const exportCanvas = document.createElement('canvas');
        const exportCtx = exportCanvas.getContext('2d');
        
        exportCanvas.width = chart.canvas.width;
        exportCanvas.height = chart.canvas.height;
        
        // Draw chart to export canvas
        exportCtx.drawImage(chart.canvas, 0, 0);
        
        // Add title and metadata
        exportCtx.fillStyle = '#fff';
        exportCtx.fillRect(0, 0, exportCanvas.width, 40);
        exportCtx.fillStyle = '#333';
        exportCtx.font = "bold 16px 'Vazir', sans-serif";
        exportCtx.textAlign = 'center';
        exportCtx.fillText(this.getChartTitle(chartId), exportCanvas.width / 2, 25);
        
        exportCtx.fillStyle = '#666';
        exportCtx.font = "12px 'Vazir', sans-serif";
        exportCtx.fillText(`صادر شده در: ${new Date().toLocaleString('fa-IR')}`, 
                          exportCanvas.width / 2, exportCanvas.height - 10);

        // Download as PNG
        const link = document.createElement('a');
        link.download = `chart-${chartId}-${Date.now()}.png`;
        link.href = exportCanvas.toDataURL();
        link.click();
    },

    collectStatsData() {
        const stats = [];
        document.querySelectorAll('.stat-card').forEach(card => {
            stats.push({
                title: card.querySelector('.stat-label')?.textContent || '',
                value: parseInt(card.querySelector('.stat-number')?.getAttribute('data-target-value')) || 0,
                type: card.getAttribute('data-stat-type') || 'number',
                period: card.getAttribute('data-period') || 'today'
            });
        });
        
        return stats;
    },

    collectChartsData() {
        const charts = [];
        document.querySelectorAll('.chart-container').forEach(container => {
            const chartId = container.getAttribute('data-chart-id');
            const chart = window.dashboardCharts && window.dashboardCharts[chartId];
            
            if (chart) {
                charts.push({
                    id: chartId,
                    type: container.getAttribute('data-chart-type'),
                    title: this.getChartTitle(chartId),
                    data: {
                        labels: chart.data.labels,
                        datasets: chart.data.datasets.map(dataset => ({
                            label: dataset.label,
                            data: dataset.data
                        }))
                    }
                });
            }
        });
        
        return charts;
    },

    downloadExportFile(response, format) {
        const blob = new Blob([response.data], { 
            type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `dashboard-${format}-${new Date().toISOString().split('T')[0]}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    },

    // Refresh single chart
    refreshChart(chartId) {
        const container = document.querySelector(`[data-chart-id="${chartId}"]`);
        if (!container) {
            console.warn('Chart container not found:', chartId);
            return;
        }

        const errorEl = container.querySelector('.chart-error');
        if (errorEl) {
            errorEl.remove();
        }

        const canvas = container.querySelector('canvas');
        if (canvas) {
            canvas.style.display = 'block';
        }

        // Reinitialize chart
        this.initializeCharts();
        
        ProjectUtils.showToast(`نمودار ${this.getChartTitle(chartId)} به‌روزرسانی شد`, 'success');
    },

    // Theme toggle
    toggleTheme(isDark) {
        if (isDark) {
            document.documentElement.classList.add('dark-mode');
            localStorage.setItem('dashboard-theme', 'dark');
            ProjectUtils.showToast('حالت تاریک فعال شد', 'info');
        } else {
            document.documentElement.classList.remove('dark-mode');
            localStorage.setItem('dashboard-theme', 'light');
            ProjectUtils.showToast('حالت روشن فعال شد', 'info');
        }

        // Update charts for dark mode
        setTimeout(() => {
            this.updateChartsForTheme(isDark);
        }, 300);
    },

    updateChartsForTheme(isDark) {
        Object.values(window.dashboardCharts || {}).forEach(chart => {
            const canvas = chart.canvas;
            const container = canvas.closest('.chart-container');
            
            if (isDark) {
                container.classList.add('dark-mode');
                canvas.style.backgroundColor = '#2d3748';
            } else {
                container.classList.remove('dark-mode');
                canvas.style.backgroundColor = '#fff';
            }
        });
    },

    // Adjust layout based on container width
    adjustDashboardLayout(width) {
        const isMobile = width < 576;
        const isTablet = width < 768;
        const isDesktop = width >= 1200;

        // Adjust chart sizes
        document.querySelectorAll('.chart-card').forEach(card => {
            if (isMobile) {
                card.style.height = '250px';
            } else if (isTablet) {
                card.style.height = '300px';
            } else if (isDesktop) {
                card.style.height = '400px';
            } else {
                card.style.height = '350px';
            }
        });

        // Adjust stats grid
        const statsGrid = document.querySelector('.stats-grid');
        if (statsGrid) {
            if (isMobile) {
                statsGrid.style.gridTemplateColumns = '1fr';
                statsGrid.style.gap = '1rem';
            } else if (isTablet) {
                statsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
                statsGrid.style.gap = '1rem';
            } else {
                statsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(280px, 1fr))';
                statsGrid.style.gap = '1.5rem';
            }
        }

        // Adjust actions grid
        const actionsGrid = document.querySelector('.actions-grid');
        if (actionsGrid) {
            if (isMobile) {
                actionsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
                actionsGrid.style.gap = '0.75rem';
            } else if (isTablet) {
                actionsGrid.style.gridTemplateColumns = 'repeat(3, 1fr)';
                actionsGrid.style.gap = '1rem';
            } else {
                actionsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
                actionsGrid.style.gap = '1rem';
            }
        }
    },

    // Show data error
    showDataError(message) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-warning alert-dismissible fade show dashboard-error';
        errorContainer.role = 'alert';
        errorContainer.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            <button type="button" class="btn btn-sm btn-outline-primary ms-2" onclick="Dashboard.refresh()">
                <i class="bi bi-arrow-clockwise"></i> تلاش مجدد
            </button>
        `;
        
        const dashboardContainer = document.querySelector('.dashboard-container');
        if (dashboardContainer) {
            dashboardContainer.insertBefore(errorContainer, dashboardContainer.firstChild);
        }

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            const alertInstance = new bootstrap.Alert(errorContainer);
            alertInstance.close();
        }, 10000);
    },

    // Refresh entire dashboard
    refresh() {
        if (this.state.isRefreshing) {
            ProjectUtils.showToast('در حال به‌روزرسانی...', 'info');
            return;
        }

        ProjectUtils.showToast('در حال به‌روزرسانی داشبورد...', 'info');
        this.refreshData()
            .then(() => {
                ProjectUtils.showToast('داشبورد به‌روزرسانی شد', 'success');
            })
            .catch(error => {
                this.showDataError('خطا در به‌روزرسانی داشبورد');
            });
    },

    // Animate refreshed content
    animateRefreshedContent() {
        // Add refresh animation to stats cards
        document.querySelectorAll('.stat-card').forEach((card, index) => {
            card.style.transform = 'scale(0.95)';
            card.style.opacity = '0.7';
            
            requestAnimationFrame(() => {
                card.style.transition = `all 0.3s ease ${index * 0.05}s`;
                card.style.transform = 'scale(1)';
                card.style.opacity = '1';
            });
        });

        // Pulse animation for charts
        document.querySelectorAll('.chart-container').forEach((container, index) => {
            container.style.transform = 'scale(0.98)';
            
            requestAnimationFrame(() => {
                container.style.transition = `all 0.4s ease ${index * 0.1}s`;
                container.style.transform = 'scale(1)';
                
                // Brief glow effect
                container.style.boxShadow = '0 0 20px rgba(13, 110, 253, 0.3)';
                setTimeout(() => {
                    container.style.boxShadow = '';
                }, 400);
            });
        });

        // Fade in activity items
        document.querySelectorAll('.activity-item').forEach((item, index) => {
            item.style.opacity = '0.5';
            item.style.transform = 'translateX(-10px)';
            
            requestAnimationFrame(() => {
                item.style.transition = `all 0.3s ease ${index * 0.05}s`;
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            });
        });
    },

    // Update trend indicators
    updateTrendIndicator(card, trend) {
        // Remove existing indicators
        const existingIndicators = card.querySelectorAll('.trend-indicator');
        existingIndicators.forEach(indicator => indicator.remove());

        if (!trend || trend.change === 0) return;

        const indicator = document.createElement('div');
        indicator.className = `trend-indicator small mt-1 ${trend.direction}`;
        indicator.style.cssText = `
            display: inline-flex;
            align-items: center;
            font-size: 0.75rem;
            font-weight: 500;
        `;

        const icon = trend.direction === 'positive' ? 
            '<i class="bi bi-arrow-up me-1"></i>' : 
            '<i class="bi bi-arrow-down me-1"></i>';
        
        const change = Math.abs(trend.change).toFixed(trend.decimals || 1);
        const suffix = trend.suffix || '%';
        
        indicator.innerHTML = `
            ${icon}
            ${change}${suffix}
            ${trend.period ? `<span class="text-muted ms-1">(${trend.period})</span>` : ''}
        `;

        const statNumber = card.querySelector('.stat-number');
        if (statNumber && statNumber.parentNode) {
            statNumber.parentNode.appendChild(indicator);
        }
    },

    // Get Persian month names for charts
    getPersianMonths() {
        return [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ];
    },

    // Convert Gregorian to Jalali for chart labels
    formatDateForChart(dateString) {
        try {
            const date = new Date(dateString);
            const jalali = ProjectUtils.gregorianToJalali(
                date.getFullYear(),
                date.getMonth() + 1,
                date.getDate()
            );
            
            return `${jalali.day}/${jalali.month}`;
        } catch (error) {
            console.warn('Failed to format date for chart:', error);
            return dateString;
        }
    }
};

// Make Dashboard globally accessible
window.Dashboard = Dashboard;

// Auto-refresh functionality for visible dashboard
if ('IntersectionObserver' in window) {
    const dashboardObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && Dashboard.state && !Dashboard.state.isRefreshing) {
                // Refresh when dashboard becomes visible
                setTimeout(() => {
                    if (entry.isIntersecting) {
                        Dashboard.refreshData();
                    }
                }, 1000);
            }
        });
    }, { threshold: 0.1 });

    // Observe dashboard container
    const dashboardContainer = document.querySelector('.dashboard-container, main');
    if (dashboardContainer) {
        dashboardObserver.observe(dashboardContainer);
    }
}

// Handle dashboard print
window.addEventListener('beforeprint', () => {
    // Prepare dashboard for printing
    document.querySelectorAll('.chart-container canvas').forEach(canvas => {
        // Ensure charts are fully rendered before print
        if (window.dashboardCharts) {
            Object.values(window.dashboardCharts).forEach(chart => {
                chart.resize();
                chart.update('none');
            });
        }
    });

    // Hide interactive elements
    document.querySelectorAll('.action-item, .btn, .dropdown').forEach(el => {
        el.style.display = 'none';
    });

    // Show print-friendly versions if available
    document.querySelectorAll('.print-only').forEach(el => {
        el.style.display = 'block';
    });
});

window.addEventListener('afterprint', () => {
    // Restore interactive elements
    document.querySelectorAll('.action-item, .btn, .dropdown').forEach(el => {
        el.style.display = '';
    });

    // Hide print-only elements
    document.querySelectorAll('.print-only').forEach(el => {
        el.style.display = 'none';
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    // Destroy charts to prevent memory leaks
    if (window.dashboardCharts) {
        Object.values(window.dashboardCharts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        window.dashboardCharts = {};
    }
});
