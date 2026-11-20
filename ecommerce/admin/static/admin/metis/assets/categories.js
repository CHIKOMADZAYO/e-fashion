import { n as Alpine } from "./vendor-ui-Bygqz38G.js";

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
    Alpine.data('categoryTable', () => ({
        categories: [],
        filteredCategories: [],
        selectedCategories: [],
        currentPage: 1,
        itemsPerPage: 10,
        searchQuery: '',
        sortField: 'name',
        sortDirection: 'asc',
        isLoading: false,

        async init() {
            await this.fetchCategories();
            this.filterCategories();
        },

        async fetchCategories() {
            this.isLoading = true;
            try {
                const data = await (await fetch('/admin/api/categories/', { headers: jsonHeaders() })).json();
                this.categories = (data.categories || []).map(c => ({
                    id: c.id,
                    name: c.name,
                    slug: c.slug,
                    description: c.description || '',
                    isActive: c.isActive,
                    productCount: c.productCount || 0,
                    createdAt: c.createdAt ? String(c.createdAt).slice(0, 16) : '',
                }));
            } catch (e) {
                console.error('Failed to load categories', e);
                this.showNotification('Failed to load categories', 'error');
            } finally {
                this.isLoading = false;
            }
        },

        filterCategories() {
            const q = this.searchQuery.toLowerCase();
            this.filteredCategories = this.categories.filter(c => !q || c.name.toLowerCase().includes(q) || c.slug.toLowerCase().includes(q));
            this.sortCategories();
            this.currentPage = 1;
        },

        sortCategories() {
            this.filteredCategories.sort((a, b) => {
                const x = String(a[this.sortField]).toLowerCase();
                const y = String(b[this.sortField]).toLowerCase();
                return this.sortDirection === 'asc' ? (x < y ? -1 : x > y ? 1 : 0) : (x > y ? -1 : x < y ? 1 : 0);
            });
        },

        sortBy(field) {
            if (this.sortField === field) this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            else { this.sortField = field; this.sortDirection = 'asc'; }
            this.filterCategories();
        },

        toggleAll(checked) {
            this.selectedCategories = checked ? this.paginatedCategories.map(c => c.id) : [];
        },

        toggleCat(id) {
            this.selectedCategories = this.selectedCategories.includes(id)
                ? this.selectedCategories.filter(i => i !== id)
                : [...this.selectedCategories, id];
        },

        async bulkAction(action) {
            if (this.selectedCategories.length === 0) return;
            if (action === 'delete') {
                if (!confirm(`Delete ${this.selectedCategories.length} category(ies)?`)) return;
                for (const id of this.selectedCategories) {
                    try { await fetch(`/admin/api/categories/${id}/delete/`, { method: 'DELETE', headers: jsonHeaders() }); }
                    catch (e) { console.error('Delete failed', id, e); }
                }
            } else {
                const isActive = action === 'activate';
                for (const id of this.selectedCategories) {
                    try { await fetch(`/admin/api/categories/${id}/update/`, { method: 'PATCH', headers: jsonHeaders(), body: JSON.stringify({ is_active: isActive }) }); }
                    catch (e) { console.error('Update failed', id, e); }
                }
            }
            this.selectedCategories = [];
            await this.fetchCategories();
            this.filterCategories();
            this.showNotification('Bulk action completed', 'success');
        },

        async deleteCategory(cat) {
            if (!confirm(`Delete "${cat.name}"?`)) return;
            try {
                await fetch(`/admin/api/categories/${cat.id}/delete/`, { method: 'DELETE', headers: jsonHeaders() });
                await this.fetchCategories();
                this.filterCategories();
                this.showNotification('Category deleted', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to delete category', 'error');
            }
        },

        editCategory(cat) {
            const formEl = document.querySelector('[x-data="categoryForm"]');
            if (formEl && formEl.__x) {
                formEl.__x.categoryForm.openEdit(cat);
            } else {
                this.showNotification('Edit form not available', 'error');
            }
        },

        exportCategories() {
            const rows = [['ID', 'Name', 'Slug', 'Description', 'Active', 'Products', 'Created']];
            this.filteredCategories.forEach(c => rows.push([c.id, c.name, c.slug, c.description, c.isActive ? 'Yes' : 'No', c.productCount, c.createdAt]));
            const csv = rows.map(r => r.join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'categories-export.csv';
            a.style.visibility = 'hidden';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },

        get paginatedCategories() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            return this.filteredCategories.slice(start, start + this.itemsPerPage);
        },
        get totalPages() { return Math.ceil(this.filteredCategories.length / this.itemsPerPage); },
        get visiblePages() {
            if (this.totalPages <= 1) return [1];
            const pages = [];
            for (let i = Math.max(2, this.currentPage - 2); i <= Math.min(this.totalPages - 1, this.currentPage + 2); i++) pages.push(i);
            const head = [1];
            if (this.currentPage - 2 > 2) head.push('...');
            const tail = [];
            if (this.currentPage + 2 < this.totalPages - 1) tail.push('...', this.totalPages);
            else if (this.totalPages > 1) tail.push(this.totalPages);
            return head.concat(pages).concat(tail).filter((v, i, a) => a.indexOf(v) === i);
        },
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) this.currentPage = page;
        },

        showNotification(msg) { alert(msg); }
    }));

    Alpine.data('categoryForm', () => ({
        form: { name: '', slug: '', description: '', is_active: true },
        editingCatId: null,
        openEdit(cat) {
            this.editingCatId = cat.id;
            this.form = { name: cat.name, slug: cat.slug, description: cat.description, is_active: cat.isActive };
            showModal('categoryModal');
        },
        async saveCategory() {
            if (!this.form.name) { alert('Name is required'); return; }
            try {
                const payload = {
                    name: this.form.name,
                    slug: this.form.slug || this.form.name.toLowerCase().replace(/\s+/g, '-'),
                    description: this.form.description || '',
                    is_active: this.form.is_active
                };
                const url = this.editingCatId ? `/admin/api/categories/${this.editingCatId}/update/` : '/admin/api/categories/create/';
                await fetch(url, { method: this.editingCatId ? 'PATCH' : 'POST', headers: jsonHeaders(), body: JSON.stringify(payload) });
                this.editingCatId = null;
                this.form = { name: '', slug: '', description: '', is_active: true };
                hideModal('categoryModal');
                const table = document.querySelector('[x-data="categoryTable"]');
                if (table && table.__x) { await table.__x.categoryTable.fetchCategories(); table.__x.categoryTable.filterCategories(); }
                this.showNotification(this.editingCatId ? 'Category updated' : 'Category created', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to save category', 'error');
            }
        },
        showNotification(msg, type = 'info') { alert(msg); }
    }));
});
