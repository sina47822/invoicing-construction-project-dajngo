/**
 * JavaScript functionality for Riz Metre page
 * Simplified version to avoid dependency issues
 */

class RizMetreTable {
    constructor() {
        this.table = document.getElementById('measurement-table');
        this.init();
    }

    init() {
        if (!this.table) {
            console.warn('Measurement table not found');
            return;
        }

        this.bindEvents();
        this.addTableEnhancements();
        this.setupKeyboardShortcuts();
        
        console.log('RizMetreTable initialized');
    }

    bindEvents() {
        // Column toggle button
        const toggleColumnsBtn = document.getElementById('toggle-columns');
        if (toggleColumnsBtn) {
            toggleColumnsBtn.addEventListener('click', () => {
                const modal = document.getElementById('columnsModal');
                if (modal) {
                    const modalInstance = new bootstrap.Modal(modal);
                    modalInstance.show();
                }
            });
        }

        // Copy table button
        const copyTableBtn = document.getElementById('copy-table');
        if (copyTableBtn) {
            copyTableBtn.addEventListener('click', () => this.copyTableToClipboard());
        }

        // Reset columns button
        const resetColumnsBtn = document.getElementById('reset-columns');
        if (resetColumnsBtn) {
            resetColumnsBtn.addEventListener('click', () => this.resetColumnSettings());
        }

        // Bind column checkboxes
        this.bindColumnCheckboxes();

        // Table row click handlers
        this.table.addEventListener('click', (e) => {
            if (e.target.closest('.item-row')) {
                this.handleRowClick(e.target.closest('.item-row'));
            }
        });
    }

    bindColumnCheckboxes() {
        const columnCheckboxes = document.querySelectorAll('.column-settings input[type="checkbox"]');
        columnCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const columnName = e.target.id.replace('col-', '');
                const columnIndex = this.getColumnIndex(columnName);
                
                const header = this.table.querySelector(`th:nth-child(${columnIndex})`);
                const cells = this.table.querySelectorAll(`tbody td:nth-child(${columnIndex})`);
                
                if (e.target.checked) {
                    if (header) header.style.display = '';
                    cells.forEach(cell => cell.style.display = '');
                } else {
                    if (header) header.style.display = 'none';
                    cells.forEach(cell => cell.style.display = 'none');
                }
                
                // Save settings to localStorage
                this.saveColumnSettings();
            });
        });

        // Load saved settings
        this.loadColumnSettings();
    }

    getColumnIndex(columnName) {
        const columnMap = {
            'length': 4,
            'width': 5,
            'height': 6,
            'weight': 7,
            'count': 8,
            'session': 10
        };
        return columnMap[columnName] || 1;
    }

    saveColumnSettings() {
        const settings = {};
        document.querySelectorAll('.column-settings input[type="checkbox"]').forEach(checkbox => {
            settings[checkbox.id] = checkbox.checked;
        });
        
        localStorage.setItem('rizMetreColumns', JSON.stringify({
            settings: settings,
            timestamp: Date.now(),
            page: window.location.pathname
        }));
    }

    loadColumnSettings() {
        try {
            const saved = localStorage.getItem('rizMetreColumns');
            if (saved) {
                const data = JSON.parse(saved);
                if (data.page === window.location.pathname) {
                    Object.keys(data.settings).forEach(key => {
                        const checkbox = document.getElementById(key);
                        if (checkbox) {
                            checkbox.checked = data.settings[key];
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                }
            }
        } catch (error) {
            console.warn('Failed to load column settings:', error);
        }
    }

    resetColumnSettings() {
        document.querySelectorAll('.column-settings input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change'));
        });
        
        localStorage.removeItem('rizMetreColumns');
        
        // Show success message
        const toastEl = document.createElement('div');
        toastEl.className = 'toast align-items-center text-white bg-success border-0 position-fixed end-0 top-0 m-3';
        toastEl.setAttribute('role', 'alert');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    تنظیمات ستون‌ها بازنشانی شد
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toastEl);
        
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    }

    addTableEnhancements() {
        // Add row numbers
        const rows = this.table.querySelectorAll('.item-row');
        let globalCounter = 1;
        
        rows.forEach((row, index) => {
            const groupRow = row.previousElementSibling;
            if (groupRow && groupRow.classList.contains('group-header')) {
                globalCounter = 1;
            }
            
            const firstCell = row.cells[0];
            if (firstCell) {
                firstCell.setAttribute('data-row-number', globalCounter);
                firstCell.setAttribute('aria-label', `ردیف ${globalCounter}`);
            }
            
            globalCounter++;
        });

        // Add zebra striping
        rows.forEach((row, index) => {
            if (index % 2 === 0) {
                row.classList.add('table-light');
            }
        });

        // Add amount column highlighting
        const amountCells = this.table.querySelectorAll('.amount-value');
        amountCells.forEach(cell => {
            const value = parseFloat(cell.getAttribute('data-value') || 0);
            const parentCell = cell.parentElement;
            if (value > 1000) {
                parentCell.classList.add('high-value');
                cell.classList.add('text-warning');
            } else if (value > 100) {
                parentCell.classList.add('medium-value');
            }
        });
    }

    handleRowClick(row) {
        const itemId = row.getAttribute('data-item-id');
        const group = row.getAttribute('data-group');
        
        if (itemId) {
            // Highlight row
            document.querySelectorAll('.item-row').forEach(r => {
                r.classList.remove('table-active');
            });
            row.classList.add('table-active');
            
            // Log interaction (if analytics available)
            console.log(`Row clicked: Item ${itemId}, Group ${group}`);
        }
    }

    copyTableToClipboard() {
        if (!navigator.clipboard) {
            this.copyTableAsCSV();
            return;
        }

        // Create a copy of the table
        const tableClone = this.table.cloneNode(true);
        
        // Remove interactive elements
        const interactiveElements = tableClone.querySelectorAll('button, a, .dropdown, .badge, .btn, .modal');
        interactiveElements.forEach(el => {
            const textContent = el.textContent.trim();
            if (textContent) {
                el.outerHTML = `<span>${textContent}</span>`;
            } else {
                el.remove();
            }
        });
        
        // Clean up empty cells
        const emptyCells = tableClone.querySelectorAll('td:empty, th:empty');
        emptyCells.forEach(cell => {
            cell.textContent = '-';
        });
        
        // Create temporary container for copying
        const tempContainer = document.createElement('div');
        tempContainer.appendChild(tableClone);
        
        // Copy to clipboard
        navigator.clipboard.writeText(tempContainer.innerText).then(() => {
            this.showCopyFeedback('copy-table', 'کپی شد');
            console.log('Table copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy: ', err);
            this.copyTableAsCSV();
        });
    }

    copyTableAsCSV() {
        const rows = this.table.querySelectorAll('tr');
        let csvContent = '';
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('th, td');
            const rowData = Array.from(cells).map(cell => {
                let text = cell.textContent.trim();
                
                // Clean up text
                text = text.replace(/[\r\n\t]/g, ' ');
                text = text.replace(/"/g, '""');
                
                // Remove HTML entities
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = text;
                text = tempDiv.textContent || tempDiv.innerText || '';
                
                return `"${text}"`;
            });
            
            csvContent += rowData.join(',') + '\r\n';
        });
        
        // Create and download CSV
        const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], {
            type: 'text/csv;charset=utf-8;'
        });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `riz-metre-${new Date().toISOString().split('T')[0]}.csv`;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
        
        this.showCopyFeedback('copy-table', 'CSV دانلود شد');
    }

    showCopyFeedback(buttonId, message) {
        const button = document.getElementById(buttonId);
        if (!button) return;
        
        const originalText = button.innerHTML;
        button.innerHTML = `<i class="bi bi-check-circle text-success me-1"></i>${message}`;
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+K for column settings
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                document.getElementById('toggle-columns')?.click();
            }
            
            // Ctrl+/ for search
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                document.getElementById('search-table')?.click();
            }
            
            // Ctrl+Enter to copy table
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('copy-table')?.click();
            }
        });
    }
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.RizMetreTable = new RizMetreTable();
    });
} else {
    window.RizMetreTable = new RizMetreTable();
}

// Add CSS for table-active state
const style = document.createElement('style');
style.textContent = `
    .table-active {
        background-color: rgba(13, 110, 253, 0.1) !important;
        border-left-color: #0d6efd !important;
        box-shadow: 0 2px 8px rgba(13, 110, 253, 0.15);
    }
    
    .high-value {
        background-color: rgba(255, 193, 7, 0.1);
    }
    
    .medium-value {
        background-color: rgba(25, 135, 84, 0.1);
    }
    
    .table-light {
        background-color: rgba(0, 0, 0, 0.025);
    }
    
    .search-result:hover {
        background-color: #ffffff;
        transform: translateX(-5px);
        transition: all 0.2s ease;
    }
    
    .visually-hidden {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
`;
document.head.appendChild(style);

// Page unload cleanup
window.addEventListener('beforeunload', () => {
    // Save final column settings
    if (window.RizMetreTable && typeof window.RizMetreTable.saveColumnSettings === 'function') {
        window.RizMetreTable.saveColumnSettings();
    }
});
