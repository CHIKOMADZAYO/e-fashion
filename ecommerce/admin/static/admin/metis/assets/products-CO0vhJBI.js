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
function handleRes(res) {
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
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
    Alpine.data('productTable', () => ({
        products: [],
        filteredProducts: [],
        selectedProducts: [],
        currentPage: 1,
        itemsPerPage: 10,
        searchQuery: '',
        categoryFilter: '',
        stockFilter: '',
        sortField: 'name',
        sortDirection: 'asc',
        isLoading: false,
        chartsInitialized: false,
        stats: { total: 0, inStock: 0, lowStock: 0, totalValue: 0 },
        categoryStats: [],
        editingProduct: null,

        async init() {
            await this.fetchProducts();
            this.filterProducts();
            this.calculateStats();
            setTimeout(() => this.initCharts(), 500);
        },

        async fetchProducts() {
            this.isLoading = true;
            try {
                const data = await (await fetch('/admin/api/products/', { headers: jsonHeaders() })).json();
                this.products = (data.products || []).map(p => ({
                    id: p.id,
                    name: p.name,
                    sku: p.sku,
                    category: (p.category && p.category.name) || 'Uncategorized',
                    price: parseFloat(p.price) || 0,
                    stock: p.stock_quantity,
                    status: p.is_active ? 'published' : 'draft',
                    created: p.created_at ? String(p.created_at).slice(0, 10) : '',
                    image: p.image || './assets/images/product-placeholder.svg',
                    description: p.description || ''
                }));
            } catch (e) {
                console.error('Failed to load products', e);
                this.showNotification('Failed to load products', 'error');
            } finally {
                this.isLoading = false;
            }
        },

        calculateStats() {
            this.stats.total = this.products.length;
            this.stats.inStock = this.products.filter(p => p.stock > 20).length;
            this.stats.lowStock = this.products.filter(p => p.stock > 0 && p.stock <= 20).length;
            this.stats.totalValue = this.products.reduce((sum, p) => sum + p.price * p.stock, 0);
            const counts = {};
            this.products.forEach(p => { counts[p.category] = (counts[p.category] || 0) + 1; });
            this.categoryStats = Object.entries(counts).map(([name, count]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                count,
                percentage: this.products.length ? Math.round(count / this.products.length * 100) : 0
            }));
        },

        filterProducts() {
            const q = this.searchQuery.toLowerCase();
            this.filteredProducts = this.products.filter(p => {
                const matchQuery = !q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q);
                const matchCat = !this.categoryFilter || p.category === this.categoryFilter;
                let matchStock = true;
                if (this.stockFilter === 'in-stock') matchStock = p.stock > 20;
                else if (this.stockFilter === 'low-stock') matchStock = p.stock > 0 && p.stock <= 20;
                else if (this.stockFilter === 'out-of-stock') matchStock = p.stock === 0;
                return matchQuery && matchCat && matchStock;
            });
            this.sortProducts();
            this.currentPage = 1;
        },

        sortProducts() {
            this.filteredProducts.sort((a, b) => {
                let x = a[this.sortField], y = b[this.sortField];
                if (this.sortField === 'price' || this.sortField === 'stock') { x = Number(x); y = Number(y); }
                else if (this.sortField === 'created') { x = new Date(x); y = new Date(y); }
                else { x = String(x).toLowerCase(); y = String(y).toLowerCase(); }
                return this.sortDirection === 'asc' ? (x < y ? -1 : x > y ? 1 : 0) : (x > y ? -1 : x < y ? 1 : 0);
            });
        },

        sortBy(field) {
            if (this.sortField === field) this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            else { this.sortField = field; this.sortDirection = 'asc'; }
            this.filterProducts();
        },

        toggleAll(checked) {
            this.selectedProducts = checked ? this.paginatedProducts.map(p => p.id) : [];
        },

        async bulkAction(action) {
            if (this.selectedProducts.length === 0) return;
            if (action === 'delete') {
                if (!confirm(`Delete ${this.selectedProducts.length} product(s)?`)) return;
                for (const id of this.selectedProducts) {
                    try {
                        await fetch(`/admin/api/products/${id}/delete/`, { method: 'DELETE', headers: jsonHeaders() });
                    } catch (e) { console.error('Delete failed', id, e); }
                }
            } else {
                const isActive = action === 'publish';
                for (const id of this.selectedProducts) {
                    try {
                        await fetch(`/admin/api/products/${id}/update/`, {
                            method: 'PATCH', headers: jsonHeaders(),
                            body: JSON.stringify({ is_active })
                        });
                    } catch (e) { console.error('Update failed', id, e); }
                }
            }
            this.selectedProducts = [];
            await this.fetchProducts();
            this.filterProducts();
            this.calculateStats();
            this.showNotification('Bulk action completed', 'success');
        },

        async deleteProduct(product) {
            if (!confirm(`Delete "${product.name}"?`)) return;
            try {
                await fetch(`/admin/api/products/${product.id}/delete/`, { method: 'DELETE', headers: jsonHeaders() });
                await this.fetchProducts();
                this.filterProducts();
                this.calculateStats();
                this.showNotification('Product deleted', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to delete product', 'error');
            }
        },

        editProduct(product) {
            const formEl = document.querySelector('[x-data="productForm"]');
            if (formEl && formEl.__x) {
                formEl.__x.productForm.openEdit(product);
            } else {
                this.showNotification('Edit form not available', 'error');
            }
        },

        viewProduct(product) {
            this.showNotification(`View: ${product.name}`, 'info');
        },

        duplicateProduct(product) {
            this.showNotification(`Duplicate: ${product.name}`, 'info');
        },

        async saveProduct(form) {
            const required = ['name', 'sku', 'category', 'price', 'stock', 'status'];
            if (required.some(f => !form[f])) { alert('Please fill in all required fields'); return; }
            try {
                const formData = new FormData();
                formData.append('name', form.name);
                formData.append('sku', form.sku);
                formData.append('description', form.description || '');
                formData.append('category', form.category);
                formData.append('price', parseFloat(form.price) || 0);
                formData.append('stock_quantity', parseInt(form.stock) || 0);
                formData.append('is_active', form.status === 'published');
                if (form.image instanceof File) {
                    formData.append('image', form.image);
                } else if (form.image) {
                    formData.append('image', form.image);
                }
                const url = this.editingProduct ? `/admin/api/products/${this.editingProduct.id}/update/` : '/admin/api/products/create/';
                const method = this.editingProduct ? 'PATCH' : 'POST';
                const headers = { 'X-CSRFToken': getCsrfToken() };
                if (!(form.image instanceof File)) {
                    headers['Accept'] = 'application/json';
                }
                await fetch(url, { method, headers, body: formData });
                this.editingProduct = null;
                await this.fetchProducts();
                this.filterProducts();
                this.calculateStats();
                const modalEl = document.getElementById('productModal');
                if (modalEl) (window.bootstrap || {}).Modal?.getInstance(modalEl)?.hide?.();
                this.showNotification('Product saved', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to save product', 'error');
            }
        },

        get paginatedProducts() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            return this.filteredProducts.slice(start, start + this.itemsPerPage);
        },
        get totalPages() { return Math.ceil(this.filteredProducts.length / this.itemsPerPage); },
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
                const salesEl = document.getElementById('salesChart');
                if (salesEl) {
                    new Ctor(salesEl, {
                        type: 'line',
                        data: { labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], datasets: [{ label: 'Sales', data: [65,78,85,92,88,95,102], borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.1)', fill: true }] },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
                    });
                }
                const catEl = document.getElementById('categoryChart');
                if (catEl && this.categoryStats.length) {
                    new Ctor(catEl, {
                        type: 'doughnut',
                        data: { labels: this.categoryStats.map(c => c.name), datasets: [{ label: 'Products', data: this.categoryStats.map(c => c.count) }] },
                        options: { cutout: '70%', plugins: { legend: { display: false } } }
                    });
                }
            } catch (e) { console.warn('Chart init skipped', e); }
        },

        showNotification(msg) { alert(msg); }
    }));

    Alpine.data('productForm', () => ({
        form: { name: '', sku: '', category: '', price: '', stock: '', description: '', status: 'draft', image: '' },
        editingId: null,
        openEdit(product) {
            this.editingId = product.id;
            this.form = {
                name: product.name,
                sku: product.sku,
                category: product.category,
                price: String(product.price),
                stock: String(product.stock),
                description: product.description || '',
                status: product.status,
                image: product.image || ''
            };
            showModal('productModal');
        },
        async saveProduct() {
            const required = ['name', 'sku', 'category', 'price', 'stock', 'status'];
            if (required.some(f => !this.form[f])) { alert('Please fill in all required fields'); return; }
            try {
                const formData = new FormData();
                formData.append('name', this.form.name);
                formData.append('sku', this.form.sku);
                formData.append('description', this.form.description || '');
                formData.append('category', this.form.category);
                formData.append('price', parseFloat(this.form.price) || 0);
                formData.append('stock_quantity', parseInt(this.form.stock) || 0);
                formData.append('is_active', this.form.status === 'published');
                if (this.form.image instanceof File) {
                    formData.append('image', this.form.image);
                } else if (this.form.image) {
                    formData.append('image', this.form.image);
                }
                const url = this.editingId ? `/admin/api/products/${this.editingId}/update/` : '/admin/api/products/create/';
                const method = this.editingId ? 'PATCH' : 'POST';
                const headers = { 'X-CSRFToken': getCsrfToken() };
                if (!(this.form.image instanceof File)) {
                    headers['Accept'] = 'application/json';
                }
                await fetch(url, { method, headers, body: formData });
                const wasEdit = !!this.editingId;
                this.editingId = null;
                this.form = { name: '', sku: '', category: '', price: '', stock: '', description: '', status: 'draft', image: null };
                const modalEl = document.getElementById('productModal');
                if (modalEl) hideModal('productModal');
                window.location.reload();
                this.showNotification(wasEdit ? 'Product updated' : 'Product created', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to save product', 'error');
            }
        },
        showNotification(msg, type = 'info') { alert(msg); }
    }));

    Alpine.data('searchComponent', searchComponent({ getResults: () => [] }));
    Alpine.data('themeSwitch', () => ({
        currentTheme: 'light',
        init() { this.currentTheme = localStorage.getItem('theme') || 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); },
        toggle() { this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); localStorage.setItem('theme', this.currentTheme); }
    }));
});
