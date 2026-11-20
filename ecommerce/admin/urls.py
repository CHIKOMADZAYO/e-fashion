from django.urls import path
from . import views

urlpatterns = [
    # Admin authentication
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('index.html', views.dashboard, name='index-redirect'),

    # Data export
    path('export/', views.export_data, name='export_data'),

    # Settings modal (AJAX load)
    path('settings-modal/', views.settings_modal, name='settings-modal'),

    # Dashboard stats API
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/dashboard/charts/', views.api_dashboard_charts, name='api_dashboard_charts'),
    path('api/dashboard/recent-orders/', views.api_dashboard_recent_orders, name='api_dashboard_recent_orders'),

    # Admin registration
    path('register/', views.admin_register, name='admin_register'),

    # Orders (HTML pages)
    path('orders/', views.orders, name='orders'),
    path('orders.html', views.orders, name='orders_html'),
    path('orders/<uuid:order_number>/', views.order_detail, name='order-detail'),

    # Products (HTML pages)
    path('products/', views.products, name='products'),
    path('products.html', views.products, name='products_html'),

    # Users / customers (HTML pages)
    path('users/', views.users, name='users'),
    path('users.html', views.users, name='users_html'),

    # Categories (HTML page)
    path('categories/', views.categories, name='categories'),
    path('categories.html', views.categories, name='categories_html'),

    # Settings
    path('settings/', views.settings_modal, name='settings'),
    path('settings.html', views.settings_modal, name='settings_html'),

    # Audit logs
    path('audit-logs/', views.audit_logs, name='audit-logs'),
    path('audit-logs.html', views.audit_logs, name='audit-logs_html'),

    # ==================== API ENDPOINTS ====================
    # Orders API
    path('api/orders/', views.api_orders_list, name='api_orders_list'),
    path('api/orders/<uuid:order_number>/', views.api_order_detail, name='api_order_detail'),
    path('api/orders/<uuid:order_number>/status/', views.api_order_update_status, name='api_order_update_status'),
    path('api/orders/bulk/', views.api_orders_bulk, name='api_orders_bulk'),

    # Products API
    path('api/products/', views.api_products_list, name='api_products_list'),
    path('api/products/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/products/create/', views.api_product_create, name='api_product_create'),
    path('api/products/<int:product_id>/update/', views.api_product_update, name='api_product_update'),
    path('api/products/<int:product_id>/delete/', views.api_product_delete, name='api_product_delete'),

    # Users API
    path('api/users/', views.api_users_list, name='api_users_list'),
    path('api/users/create/', views.api_user_create, name='api_user_create'),
    path('api/users/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
    path('api/users/<int:user_id>/update/', views.api_user_update, name='api_user_update'),
    path('api/users/<int:user_id>/delete/', views.api_user_delete, name='api_user_delete'),

    # Categories API
    path('api/categories/', views.api_categories_list, name='api_categories_list'),
    path('api/categories/create/', views.api_category_create, name='api_category_create'),
    path('api/categories/<int:category_id>/update/', views.api_category_update, name='api_category_update'),
    path('api/categories/<int:category_id>/delete/', views.api_category_delete, name='api_category_delete'),

    # Audit Logs API
    path('api/audit-logs/', views.api_audit_logs, name='api_audit_logs'),

    # Settings API
    path('api/settings/', views.api_settings_get, name='api_settings_get'),
    path('api/settings/update/', views.api_settings_update, name='api_settings_update'),

    # Deprecated Metis pages (redirect to dashboard)
    path('analytics.html', views.deprecated_page_redirect, name='analytics_redirect'),
    path('reports.html', views.deprecated_page_redirect, name='reports_redirect'),
    path('messages.html', views.deprecated_page_redirect, name='messages_redirect'),
    path('calendar.html', views.deprecated_page_redirect, name='calendar_redirect'),
    path('files.html', views.deprecated_page_redirect, name='files_redirect'),
    path('forms.html', views.deprecated_page_redirect, name='forms_redirect'),
    path('help.html', views.deprecated_page_redirect, name='help_redirect'),
    path('security.html', views.deprecated_page_redirect, name='security_redirect'),

    # Auth pages (redirect to admin login/register)
    path('login.html', views.admin_login, name='login_html'),
    path('register.html', views.deprecated_page_redirect, name='register_html'),
    path('forgot-password.html', views.deprecated_page_redirect, name='forgot_password_redirect'),
    path('reset-password.html', views.deprecated_page_redirect, name='reset_password_redirect'),
    path('two-factor.html', views.deprecated_page_redirect, name='two_factor_redirect'),
]
