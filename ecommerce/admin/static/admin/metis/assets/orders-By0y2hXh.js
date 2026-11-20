import { n as Alpine } from "./vendor-ui-Bygqz38G.js";
import { l as Chart, r as scaleCfg, o as colorRgba, i as colorAlpha, a as colorAt, s as neutralColor, d as getColor, l as chartCtor, y as plugin } from "./main-db-DdQNj.js";
import { t as searchComponent } from "./search-component-B5zGr_FE.js";

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
function showModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = 'block';
    el.classList.add('show');
    el.setAttribute('aria-modal', 'true');
    el.removeAttribute('aria-hidden');
    const bd = document.createElement('div');
    bd.className = 'modal-backdrop fade show';
    document.body.appendChild(bd);
    document.body.style.overflow = 'hidden';
    el._bsBd = bd;
}
function hideModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = 'none';
    el.classList.remove('show');
    el.setAttribute('aria-hidden', 'true');
    el.removeAttribute('aria-modal');
    if (el._bsBd) { el._bsBd.remove(); delete el._bsBd; }
    if (!document.querySelector('.modal-backdrop')) document.body.style.overflow = '';
}

document.addEventListener('alpine:init', () => {
    Alpine.data('orderTable', () => ({
        orders: [],
        filteredOrders: [],
        selectedOrders: [],
        currentPage: 1,
        itemsPerPage: 10,
        searchQuery: '',
        statusFilter: '',
        dateFilter: '',
        sortField: 'orderNumber',
        sortDirection: 'desc',
        isLoading: false,
        chartsInitialized: false,
        stats: { total: 0, pending: 0, shipped: 0, revenue: 0 },
        statusStats: [],
        selectedViewOrder: null,
        bulkStatus: 'processing',

        async init() {
            await this.fetchOrders();
            this.filterOrders();
            this.calculateStats();
            setTimeout(() => this.initCharts(), 500);
        },

        async fetchOrders() {
            this.isLoading = true;
            try {
                const data = await (await fetch('/admin/api/orders/', { headers: jsonHeaders() })).json();
                this.orders = (data.orders || []).map(o => ({
                    id: o.id,
                    orderNumber: o.orderNumber,
                    customer: { name: o.customer?.name || '', email: o.customer?.email || '', avatar: o.customer?.avatar || './assets/images/avatar-placeholder.svg' },
                    items: o.items || [],
                    itemCount: o.itemCount || 0,
                    total: parseFloat(o.total) || 0,
                    status: o.status,
                    orderDate: o.orderDate || o.createdAt?.slice(0, 10) || ''
                }));
            } catch (e) {
                console.error('Failed to load orders', e);
                this.showNotification('Failed to load orders', 'error');
            } finally {
                this.isLoading = false;
            }
        },

        calculateStats() {
            this.stats.total = this.orders.length;
            this.stats.pending = this.orders.filter(o => o.status === 'pending').length;
            this.stats.shipped = this.orders.filter(o => o.status === 'shipped').length;
            this.stats.revenue = this.orders.filter(o => o.status !== 'cancelled').reduce((sum, o) => sum + o.total, 0);
            const counts = {};
            this.orders.forEach(o => { counts[o.status] = (counts[o.status] || 0) + 1; });
            this.statusStats = Object.entries(counts).map(([name, count]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                count,
                percentage: this.orders.length ? Math.round(count / this.orders.length * 100) : 0
            }));
        },

        filterOrders() {
            const q = this.searchQuery.toLowerCase();
            this.filteredOrders = this.orders.filter(o => {
                const matchQuery = !q || o.orderNumber.toLowerCase().includes(q) || o.customer.name.toLowerCase().includes(q) || o.customer.email.toLowerCase().includes(q);
                const matchStatus = !this.statusFilter || o.status === this.statusFilter;
                let matchDate = true;
                if (this.dateFilter) {
                    const d = new Date(o.orderDate || o.createdAt);
                    const now = new Date();
                    if (this.dateFilter === 'today') matchDate = d.toDateString() === now.toDateString();
                    else if (this.dateFilter === 'week') matchDate = d >= new Date(now.getTime() - 6048e5);
                    else if (this.dateFilter === 'month') matchDate = d >= new Date(now.getTime() - 2592e6);
                }
                return matchQuery && matchStatus && matchDate;
            });
            this.sortOrders();
            this.currentPage = 1;
        },

        sortOrders() {
            this.filteredOrders.sort((a, b) => {
                let x = a[this.sortField], y = b[this.sortField];
                if (this.sortField === 'total') { x = Number(x); y = Number(y); }
                else if (this.sortField === 'orderDate') { x = new Date(x); y = new Date(y); }
                else { x = String(x).toLowerCase(); y = String(y).toLowerCase(); }
                return this.sortDirection === 'asc' ? (x < y ? -1 : x > y ? 1 : 0) : (x > y ? -1 : x < y ? 1 : 0);
            });
        },

        sortBy(field) {
            if (this.sortField === field) this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            else { this.sortField = field; this.sortDirection = 'asc'; }
            this.filterOrders();
        },

        toggleAll(checked) {
            this.selectedOrders = checked ? this.paginatedOrders.map(o => o.id) : [];
        },

        async bulkAction(status) {
            if (this.selectedOrders.length === 0) return;
            try {
                await fetch('/admin/api/orders/bulk/', {
                    method: 'POST', headers: jsonHeaders(),
                    body: JSON.stringify({ order_ids: this.selectedOrders, status })
                });
            } catch (e) {
                console.error('Bulk update failed', e);
                this.showNotification('Bulk update failed', 'error');
                this.selectedOrders = [];
                return;
            }
            this.selectedOrders = [];
            await this.fetchOrders();
            this.filterOrders();
            this.calculateStats();
            this.showNotification(`Orders marked as ${status}`, 'success');
        },

        async cancelOrder(order) {
            const target = order || this.selectedViewOrder;
            if (!target) return;
            if (!confirm(`Cancel order ${target.orderNumber}?`)) return;
            try {
                await fetch(`/admin/api/orders/${encodeURIComponent(target.id)}/status/`, {
                    method: 'PATCH', headers: jsonHeaders(), body: JSON.stringify({ status: 'cancelled' })
                });
                this.selectedViewOrder = null;
                await this.fetchOrders();
                this.filterOrders();
                this.calculateStats();
                this.showNotification('Order cancelled', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to cancel order', 'error');
            }
        },

        viewOrder(order) {
            this.selectedViewOrder = order;
            const fill = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
            fill('modalOrderNumber', order.orderNumber);
            fill('modalOrderStatus', order.status);
            fill('modalCustomer', order.customer.name);
            fill('modalEmail', order.customer.email);
            fill('modalTotal', '$' + order.total);
            fill('modalDate', order.orderDate);
            const itemsEl = document.getElementById('modalItems');
            if (itemsEl) {
                itemsEl.innerHTML = (order.items || []).map(i => `<li>${i.name} × ${i.quantity} @ $${i.price}</li>`).join('');
            }
            const el = document.getElementById('orderModal');
            if (el) showModal('orderModal');
        },

        trackOrder(order) {
            this.showNotification(`Track: ${order.orderNumber}`, 'info');
        },

        printInvoice(order) {
            this.showNotification(`Invoice: ${order.orderNumber}`, 'info');
        },

        get paginatedOrders() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            return this.filteredOrders.slice(start, start + this.itemsPerPage);
        },
        get totalPages() { return Math.ceil(this.filteredOrders.length / this.itemsPerPage); },
        get visiblePages() {
            if (this.totalPages <= 1) return [1];
            const pages = [];
            if (this.totalPages <= 7) {
                for (let i = 2; i <= this.totalPages; i++) pages.push(i);
            } else if (this.currentPage <= 4) {
                for (let i = 2; i <= 5; i++) pages.push(i);
                pages.push('...', this.totalPages);
            } else if (this.currentPage >= this.totalPages - 3) {
                pages.push('...');
                for (let i = this.totalPages - 4; i <= this.totalPages; i++) pages.push(i);
            } else {
                pages.push('...');
                for (let i = this.currentPage - 1; i <= this.currentPage + 1; i++) pages.push(i);
                pages.push('...', this.totalPages);
            }
            return pages;
        },
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) this.currentPage = page;
        },

        initCharts() {
            if (this.chartsInitialized) return;
            this.chartsInitialized = true;
            try {
                const Ctor = Chart || chartCtor;
                if (!Ctor) return;
                const trendsEl = document.getElementById('orderTrendsChart');
                if (trendsEl) {
                    new Ctor(trendsEl, {
                        type: 'line',
                        data: { labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], datasets: [
                            { label: 'Orders', data: [12,19,15,27,24,32,28], borderColor: '#2563eb', fill: false },
                            { label: 'Revenue', data: [1200,1900,1500,2700,2400,3200,2800], borderColor: '#dc2626', fill: false }
                        ] },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
                const statusEl = document.getElementById('statusChart');
                if (statusEl && this.statusStats.length) {
                    new Ctor(statusEl, {
                        type: 'doughnut',
                        data: { labels: this.statusStats.map(s => s.name), datasets: [{ label: 'Orders', data: this.statusStats.map(s => s.count) }] },
                        options: { cutout: '70%', plugins: { legend: { display: false } } }
                    });
                }
            } catch (e) { console.warn('Chart init skipped', e); }
        },

        showNotification(msg) { alert(msg); }
    }));

    Alpine.data('searchComponent', searchComponent({ getResults: () => [] }));
    Alpine.data('themeSwitch', () => ({
        currentTheme: 'light',
        init() { this.currentTheme = localStorage.getItem('theme') || 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); },
        toggle() { this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); localStorage.setItem('theme', this.currentTheme); }
    }));
});
