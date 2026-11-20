import { v as createChart } from "./main-db-DdQNj.js";

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
async function fetchJSON(url) {
    const res = await fetch(url, { headers: jsonHeaders() });
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
}

document.addEventListener('DOMContentLoaded', async () => {
    if (document.body.dataset.page !== 'dashboard') return;

    try {
        const [stats, chartData, ordersData] = await Promise.all([
            fetchJSON('/admin/api/dashboard-stats/'),
            fetchJSON('/admin/api/dashboard/charts/?days=7'),
            fetchJSON('/admin/api/dashboard/recent-orders/?limit=5')
        ]);

        // Update stat cards
        const statEls = document.querySelectorAll('[data-stat-value]');
        if (statEls[0]) statEls[0].textContent = stats.total_customers.toLocaleString();
        if (statEls[1]) statEls[1].textContent = stats.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (statEls[2]) statEls[2].textContent = stats.total_orders.toLocaleString();
        if (statEls[3]) statEls[3].textContent = stats.low_stock_products.toLocaleString();

        // Revenue chart
        const revenueEl = document.getElementById('revenueChart');
        if (revenueEl) {
            createChart(revenueEl, {
                type: 'line',
                data: {
                    labels: chartData.revenue.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: chartData.revenue.data,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37,99,235,0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top' } },
                    scales: { y: { beginAtZero: true } }
                }
            }, { height: 320 });
        }

        // User growth chart
        const userGrowthEl = document.getElementById('userGrowthChart');
        if (userGrowthEl) {
            createChart(userGrowthEl, {
                type: 'bar',
                data: {
                    labels: chartData.user_growth.labels,
                    datasets: [{
                        label: 'New Users',
                        data: chartData.user_growth.data,
                        backgroundColor: '#2563eb',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true } }
                }
            }, { height: 280 });
        }

        // Order status chart
        const orderStatusEl = document.getElementById('orderStatusChart');
        if (orderStatusEl) {
            createChart(orderStatusEl, {
                type: 'doughnut',
                data: {
                    labels: chartData.order_status.labels,
                    datasets: [{
                        data: chartData.order_status.data,
                        backgroundColor: ['#16a34a', '#0d9488', '#d97706', '#dc2626'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    cutout: '60%'
                }
            }, { height: 280 });
        }

        // Storage status chart
        const storageEl = document.getElementById('storageStatusChart');
        if (storageEl) {
            const total = stats.total_products || 1;
            const low = stats.low_stock_products || 0;
            const used = Math.round(low / total * 100);
            createChart(storageEl, {
                type: 'doughnut',
                data: {
                    labels: ['Used Space', 'Free Space'],
                    datasets: [{
                        data: [used, Math.max(0, 100 - used)],
                        backgroundColor: used > 50 ? '#dc2626' : '#16a34a',
                        borderWidth: 0,
                        borderRadius: [{ outerStart: 12, outerEnd: 12, innerStart: 12, innerEnd: 12 }, 0]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: ctx => `${ctx.label}: ${ctx.parsed}%` } }
                    },
                    cutout: '78%',
                    layout: { padding: 24 }
                }
            }, { height: 280 });
        }

        // Sales by location chart
        const salesEl = document.getElementById('salesByLocationChart');
        if (salesEl) {
            createChart(salesEl, {
                type: 'doughnut',
                data: {
                    labels: chartData.order_status.labels,
                    datasets: [{
                        data: chartData.order_status.data,
                        backgroundColor: ['#2563eb', '#0d9488', '#d97706', '#dc2626'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } }
                }
            }, { height: 350 });
        }

        // Populate recent orders table
        const tableBody = document.getElementById('recent-orders-table');
        if (tableBody && ordersData.orders) {
            tableBody.innerHTML = ordersData.orders.map(order => `
                <tr>
                    <td><strong>#${order.order_number}</strong></td>
                    <td>${order.customer}</td>
                    <td>$${order.total.toFixed(2)}</td>
                    <td><span class="badge bg-${order.status === 'delivered' ? 'success' : order.status === 'pending' ? 'warning' : order.status === 'cancelled' ? 'danger' : 'primary'}">${order.status}</span></td>
                    <td>${order.created_at}</td>
                </tr>
            `).join('');
        }

    } catch (e) {
        console.error('Dashboard load failed', e);
    }
});
