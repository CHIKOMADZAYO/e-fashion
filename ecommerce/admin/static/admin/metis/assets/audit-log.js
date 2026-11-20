import { n as Alpine } from "./vendor-ui-Bygqz38G.js";
import { r as swal } from "./vendor-bootstrap-Bfe3tQ1z.js";

function getCsrfToken() {
    const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
}
function jsonHeaders() {
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    };
}

document.addEventListener('alpine:init', () => {
    Alpine.data('auditLogTable', () => ({
        logs: [],
        filteredLogs: [],
        currentPage: 1,
        itemsPerPage: 25,
        searchQuery: '',
        actionFilter: '',
        modelFilter: '',
        dateFilter: '',
        sortField: 'createdAt',
        sortDirection: 'desc',
        expandedLog: null,
        isLoading: false,

        async init() {
            await this.fetchLogs();
        },

        async fetchLogs() {
            this.isLoading = true;
            const params = new URLSearchParams();
            params.set('page', this.currentPage);
            params.set('per_page', this.itemsPerPage);
            if (this.actionFilter) params.set('action', this.actionFilter);
            if (this.modelFilter) params.set('model', this.modelFilter);
            if (this.dateFilter) params.set('date_filter', this.dateFilter);
            params.set('sort', this.sortField);
            params.set('dir', this.sortDirection);

            try {
                const data = await (await fetch(`/admin/api/audit-logs/?${params}`, { headers: jsonHeaders() })).json();
                this.logs = (data.logs || []).map(log => ({
                    ...log,
                    user: log.user || 'System',
                    createdAt: log.createdAt
                }));
            } catch (e) {
                console.error('Failed to load audit logs', e);
                alert('Failed to load audit logs');
            } finally {
                this.isLoading = false;
            }
        },

        filterLogs() {
            this.currentPage = 1;
            this.fetchLogs();
        },

        sortBy(field) {
            if (this.sortField === field) this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            else { this.sortField = field; this.sortDirection = 'asc'; }
            this.fetchLogs();
        },

        goToPage(page) {
            this.currentPage = page;
            this.fetchLogs();
        },

        get paginatedLogs() {
            return this.logs;
        },
        get totalPages() { return 1; },
        get visiblePages() { return [1]; },
        get filteredLogs() { return this.logs; },

        formatDateTime(iso) {
            if (!iso) return '';
            return new Date(iso).toLocaleString();
        },

        timeAgo(iso) {
            if (!iso) return '';
            const d = new Date(iso);
            const now = new Date();
            const seconds = Math.floor((now - d) / 1000);
            if (seconds < 60) return 'just now';
            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
            const days = Math.floor(hours / 24);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        },

        formatAction(action) {
            return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        },

        actionBadgeClass(action) {
            const map = {
                login: 'bg-success', logout: 'bg-secondary',
                product_create: 'bg-info', product_update: 'bg-warning', product_delete: 'bg-danger',
                order_status_change: 'bg-primary',
                user_update: 'bg-info', settings_update: 'bg-warning'
            };
            return map[action] || 'bg-light text-dark';
        },

        showDetails(log) {
            this.expandedLog = this.expandedLog === log.id ? null : log.id;
        },

        exportLogs() {
            const rows = [['Date', 'User', 'Action', 'Model', 'Object', 'Details']];
            this.logs.forEach(log => rows.push([
                this.formatDateTime(log.createdAt),
                log.user,
                log.action,
                log.modelName,
                log.objectRepr || '',
                JSON.stringify(log.details || {})
            ]));
            const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'audit-logs.csv';
            a.style.visibility = 'hidden';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }));
});
