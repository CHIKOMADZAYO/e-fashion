import { n as Alpine } from "./vendor-ui-Bygqz38G.js";
import { b as Chart, l as scaleCfg, o as colorRgba, i as colorAlpha, a as colorAt, s as neutralColor, d as getColor, l as chartCtor, y as plugin } from "./main-db-DdQNj.js";
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
    Alpine.data('userTable', () => ({
        users: [],
        filteredUsers: [],
        selectedUsers: [],
        currentPage: 1,
        itemsPerPage: 10,
        searchQuery: '',
        statusFilter: '',
        roleFilter: '',
        sortField: 'name',
        sortDirection: 'asc',
        isLoading: false,

        async init() {
            await this.fetchUsers();
            this.filterUsers();
        },

        async fetchUsers() {
            this.isLoading = true;
            try {
                const data = await (await fetch('/admin/api/users/', { headers: jsonHeaders() })).json();
                this.users = (data.users || []).map(u => ({
                    id: u.id,
                    name: u.fullName || u.username,
                    email: u.email,
                    role: u.isStaff ? 'admin' : 'user',
                    status: u.isActive ? 'active' : 'inactive',
                    lastActive: u.lastLogin ? String(u.lastLogin).slice(0, 16) : 'Never',
                    joinDate: u.dateJoined ? String(u.dateJoined).slice(0, 10) : '',
                    avatar: './assets/images/avatar-placeholder.svg',
                    phone: '',
                    department: '',
                }));
            } catch (e) {
                console.error('Failed to load users', e);
                this.showNotification('Failed to load users', 'error');
            } finally {
                this.isLoading = false;
            }
        },

        filterUsers() {
            const q = this.searchQuery.toLowerCase();
            this.filteredUsers = this.users.filter(u => {
                const matchQuery = !q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
                const matchStatus = !this.statusFilter || u.status === this.statusFilter;
                const matchRole = !this.roleFilter || u.role === this.roleFilter;
                return matchQuery && matchStatus && matchRole;
            });
            this.sortUsers();
            this.currentPage = 1;
        },

        sortUsers() {
            this.filteredUsers.sort((a, b) => {
                let x = a[this.sortField], y = b[this.sortField];
                if (typeof x === 'string') { x = x.toLowerCase(); y = y.toLowerCase(); }
                return this.sortDirection === 'asc' ? (x < y ? -1 : x > y ? 1 : 0) : (x > y ? -1 : x < y ? 1 : 0);
            });
        },

        sortBy(field) {
            if (this.sortField === field) this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            else { this.sortField = field; this.sortDirection = 'asc'; }
            this.filterUsers();
        },

        toggleAll(checked) {
            this.selectedUsers = checked ? this.paginatedUsers.map(u => u.id) : [];
        },

        toggleUser(id) {
            this.selectedUsers = this.selectedUsers.includes(id)
                ? this.selectedUsers.filter(i => i !== id)
                : [...this.selectedUsers, id];
        },

        async bulkAction(action) {
            if (this.selectedUsers.length === 0) return;
            if (action === 'delete') {
                if (!confirm(`Delete ${this.selectedUsers.length} user(s)?`)) return;
                for (const id of this.selectedUsers) {
                    if (id === (window.currentUserId || -1)) continue;
                    try {
                        await fetch(`/admin/api/users/${id}/delete/`, { method: 'DELETE', headers: jsonHeaders() });
                    } catch (e) { console.error('Delete failed', id, e); }
                }
            } else {
                const isActive = action === 'activate';
                for (const id of this.selectedUsers) {
                    try {
                        await fetch(`/admin/api/users/${id}/update/`, {
                            method: 'PATCH', headers: jsonHeaders(),
                            body: JSON.stringify({ is_active: isActive })
                        });
                    } catch (e) { console.error('Update failed', id, e); }
                }
            }
            this.selectedUsers = [];
            await this.fetchUsers();
            this.filterUsers();
            this.showNotification('Bulk action completed', 'success');
        },

        async deleteUser(user) {
            if (!confirm(`Delete "${user.name}"?`)) return;
            if (user.id === (window.currentUserId || -1)) { this.showNotification('Cannot delete yourself', 'error'); return; }
            try {
                await fetch(`/admin/api/users/${user.id}/delete/`, { method: 'DELETE', headers: jsonHeaders() });
                await this.fetchUsers();
                this.filterUsers();
                this.showNotification('User deleted', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to delete user', 'error');
            }
        },

        exportUsers() {
            const rows = [['ID', 'Name', 'Email', 'Role', 'Status', 'Join Date', 'Last Active']];
            this.filteredUsers.forEach(u => rows.push([u.id, u.name, u.email, u.role, u.status, u.joinDate, u.lastActive]));
            const csv = rows.map(r => r.join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'users-export.csv';
            a.style.visibility = 'hidden';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },

        sendBulkInvites() {
            if (this.selectedUsers.length === 0) { alert('Please select users to send invites to'); return; }
            alert(`Sent invites to ${this.selectedUsers.length} user(s)`);
            this.selectedUsers = [];
        },

        generateReport() {
            const report = {
                generatedAt: new Date().toISOString(),
                totalUsers: this.users.length,
                stats: this.stats,
            };
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'user-report.json';
            a.style.visibility = 'hidden';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },

        editUser(user) {
            const formEl = document.querySelector('[x-data="userForm"]');
            if (formEl && formEl.__x) {
                formEl.__x.userForm.openEdit(user);
            } else {
                this.showNotification('Edit form not available', 'error');
            }
        },

        viewUser(user) {
            this.showNotification(`View: ${user.name}`, 'info');
        },

        get paginatedUsers() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            return this.filteredUsers.slice(start, start + this.itemsPerPage);
        },
        get totalPages() { return Math.ceil(this.filteredUsers.length / this.itemsPerPage); },
        get visiblePages() {
            const pages = [];
            if (this.totalPages <= 1) return [1];
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

    Alpine.data('userForm', () => ({
        form: { firstName: '', lastName: '', email: '', role: 'user', status: 'active', phone: '' },
        editingUserId: null,
        openEdit(user) {
            this.editingUserId = user.id;
            const parts = (user.name || '').split(' ');
            this.form = {
                firstName: parts[0] || '',
                lastName: parts.slice(1).join(' ') || '',
                email: user.email || '',
                role: user.role,
                status: user.status,
                phone: user.phone || ''
            };
            showModal('userModal');
        },
        async saveUser() {
            if (!this.form.firstName || !this.form.lastName || !this.form.email) { alert('Please fill in all required fields'); return; }
            try {
                const payload = {
                    username: (this.form.firstName + this.form.lastName + Math.random()).replace(/\s+/g, '').toLowerCase(),
                    email: this.form.email,
                    password: 'ChangeMe123!',
                    first_name: this.form.firstName,
                    last_name: this.form.lastName,
                    is_active: this.form.status === 'active',
                    is_staff: this.form.role === 'admin'
                };
                const url = this.editingUserId ? `/admin/api/users/${this.editingUserId}/update/` : '/admin/api/users/create/';
                await fetch(url, { method: this.editingUserId ? 'PATCH' : 'POST', headers: jsonHeaders(), body: JSON.stringify(payload) });
                this.editingUserId = null;
                this.form = { firstName: '', lastName: '', email: '', role: 'user', status: 'active', phone: '' };
                hideModal('userModal');
                const table = document.querySelector('[x-data="userTable"]');
                if (table && table.__x) { await table.__x.userTable.fetchUsers(); table.__x.userTable.filterUsers(); }
                this.showNotification(this.editingUserId ? 'User updated' : 'User created', 'success');
            } catch (e) {
                console.error(e);
                this.showNotification('Failed to save user', 'error');
            }
        },
        showNotification(msg, type = 'info') { alert(msg); }
    }));

    Alpine.data('searchComponent', searchComponent({ delayMs: 300, getResults(q) {
        const table = document.querySelector('[x-data="userTable"]');
        if (table && table.__x) { table.__x.userTable.searchQuery = q; table.__x.userTable.filterUsers(); }
        const r = q.toLowerCase();
        return [{ title: 'Dashboard', url: '/', type: 'page' }, { title: 'Users', url: '/users.html', type: 'page' }].filter(x => x.title.toLowerCase().includes(r));
    } }));
    Alpine.data('themeSwitch', () => ({
        currentTheme: 'light',
        init() { this.currentTheme = localStorage.getItem('theme') || 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); },
        toggle() { this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light'; document.documentElement.setAttribute('data-bs-theme', this.currentTheme); localStorage.setItem('theme', this.currentTheme); }
    }));
});
