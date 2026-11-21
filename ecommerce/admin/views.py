import json
from functools import wraps
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import StaffProfile, SiteSettings, AuditLog
from .forms import AdminLoginForm, AdminRegisterForm


def admin_login_required(view_func):
    """Redirect unauthenticated users to the admin login page instead of the storefront login."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('admin_login')}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_login(request):
    if request.user.is_authenticated and StaffProfile.objects.filter(user=request.user, is_active=True).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                staff_profile, created = StaffProfile.objects.get_or_create(user=user)
                if staff_profile.is_active:
                    login(request, user)
                    AuditLog.objects.create(
                        user=user,
                        action='login',
                        model_name='staff_profile',
                        object_repr=f'Staff: {staff_profile}',
                        details={'ip': request.META.get('REMOTE_ADDR', '')}
                    )
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Your account is disabled.')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AdminLoginForm()

    return render(request, 'metis/auth/admin_login.html', {'form': form, 'next': request.GET.get('next', '')})


def admin_register(request):
    """Admin: Register a new staff user."""
    User = get_user_model()

    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        form = AdminRegisterForm(data)
        if not form.is_valid():
            return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)

        cd = form.cleaned_data
        if User.objects.filter(username=cd['username']).exists():
            return JsonResponse({'success': False, 'errors': {'username': ['Username already exists.']}}, status=400)
        if User.objects.filter(email=cd['email']).exists():
            return JsonResponse({'success': False, 'errors': {'email': ['Email already exists.']}}, status=400)

        user = User.objects.create_user(username=cd['username'], email=cd['email'], password=cd['password1'])
        user.first_name = cd.get('first_name', '')
        user.last_name = cd.get('last_name', '')
        user.is_staff = True
        user.is_active = True
        user.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        StaffProfile.objects.get_or_create(user=user, defaults={'role': cd['role'], 'is_active': True})

        login(request, user)

        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='user_create',
            model_name='user',
            object_repr=f'User: {user.username}',
            details={'created_by': request.user.username if request.user.is_authenticated else 'system'},
        )

        return JsonResponse({'success': True, 'id': user.id, 'username': user.username})

    form = AdminRegisterForm()
    return render(request, 'metis/auth/admin_register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def admin_logout(request):
    if request.user.is_authenticated:
        user = request.user
        AuditLog.objects.create(
            user=user,
            action='logout',
            model_name='staff_profile',
            object_repr=f'Staff: {user.staff_profile if hasattr(user, "staff_profile") else "N/A"}',
            details={'ip': request.META.get('REMOTE_ADDR', '')}
        )
    logout(request)
    return redirect('admin_login')


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def dashboard(request):
    from ecommerce.ui.models import Order, Product
    from django.contrib.auth import get_user_model

    User = get_user_model()
    settings = SiteSettings.load()

    total_orders = 0
    total_revenue = 0
    pending_orders = 0
    completed_orders = 0
    total_products = 0
    low_stock_products = 0
    total_customers = 0

    try:
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(total=Sum('total'))['total'] or 0
        pending_orders = Order.objects.filter(status='pending').count()
        completed_orders = Order.objects.filter(status='delivered').count()
        total_products = Product.objects.count()
        low_stock_products = Product.objects.filter(stock_quantity__lte=settings.low_stock_threshold if settings else 10).count()
        total_customers = User.objects.filter(is_staff=False, is_superuser=False).count()
    except Exception:
        pass

    recent_audit_logs = AuditLog.objects.select_related('user').order_by('-created_at')[:10]
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    context = {
        'settings': settings,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_customers': total_customers,
        'recent_audit_logs': recent_audit_logs,
        'recent_orders': recent_orders,
    }
    return render(request, 'metis/pages/index.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def orders(request):
    from ecommerce.ui.models import Order

    status_filter = request.GET.get('status', '')

    if status_filter:
        orders_list = Order.objects.filter(status=status_filter).order_by('-created_at')
    else:
        orders_list = Order.objects.all().order_by('-created_at')

    context = {
        'orders': orders_list,
        'status_filter': status_filter,
    }
    return render(request, 'metis/pages/orders.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def order_detail(request, order_number):
    from ecommerce.ui.models import Order, OrderItem

    order = get_object_or_404(Order, order_number=order_number)

    context = {
        'order': order,
        'items': order.items.all(),
    }
    return render(request, 'metis/pages/orders.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def products(request):
    from ecommerce.ui.models import Product, Category

    products_list = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    if category_id:
        products_list = products_list.filter(category_id=category_id)

    context = {
        'products': products_list,
        'categories': categories,
        'selected_category': int(category_id) if category_id else 0,
    }
    return render(request, 'metis/pages/products.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def users(request):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users_list = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')

    context = {
        'users': users_list,
    }
    return render(request, 'metis/pages/users.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def categories(request):
    from ecommerce.ui.models import Category

    categories_list = Category.objects.all().order_by('name')
    context = {
        'categories': categories_list,
    }
    return render(request, 'metis/pages/categories.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def settings_modal(request):
    from django.db import transaction

    settings = SiteSettings.load()

    if request.method == 'POST':
        site_name = request.POST.get('site_name', '')
        contact_email = request.POST.get('contact_email', '')
        contact_phone = request.POST.get('contact_phone', '')
        contact_address = request.POST.get('contact_address', '')
        currency = request.POST.get('currency', 'KES')
        low_stock_threshold = request.POST.get('low_stock_threshold', '')
        default_shipping_fee = request.POST.get('default_shipping_fee', '')

        settings.site_name = site_name
        settings.contact_email = contact_email
        settings.contact_phone = contact_phone
        settings.contact_address = contact_address
        settings.currency = currency

        if low_stock_threshold:
            settings.low_stock_threshold = int(low_stock_threshold)
        if default_shipping_fee:
            settings.default_shipping_fee = float(default_shipping_fee)

        settings.save()

        messages.success(request, 'Settings updated successfully.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Settings updated successfully.'})

        return redirect('settings')

    context = {
        'settings': settings,
    }
    return render(request, 'metis/pages/settings.html', context)


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def deprecated_page_redirect(request):
    """Redirect deprecated Metis pages to dashboard."""
    return redirect('dashboard')


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_settings_get(request):
    """API: Get SiteSettings."""
    settings = SiteSettings.load()
    return JsonResponse({
        'siteName': settings.site_name,
        'contactEmail': settings.contact_email,
        'contactPhone': settings.contact_phone,
        'contactAddress': settings.contact_address,
        'currency': settings.currency,
        'lowStockThreshold': settings.low_stock_threshold,
        'defaultShippingFee': str(settings.default_shipping_fee),
        'maintenanceMode': settings.maintenance_mode,
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["PATCH", "POST"])
def api_settings_update(request):
    """API: Update SiteSettings."""
    settings = SiteSettings.load()

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    fields_to_update = []
    for field, attr in [
        ('siteName', 'site_name'),
        ('contactEmail', 'contact_email'),
        ('contactPhone', 'contact_phone'),
        ('contactAddress', 'contact_address'),
        ('currency', 'currency'),
        ('lowStockThreshold', 'low_stock_threshold'),
        ('defaultShippingFee', 'default_shipping_fee'),
        ('maintenanceMode', 'maintenance_mode'),
    ]:
        if field in payload:
            if attr in ['low_stock_threshold']:
                setattr(settings, attr, int(payload[field]))
            elif attr in ['default_shipping_fee']:
                setattr(settings, attr, float(payload[field]))
            elif attr in ['maintenance_mode']:
                setattr(settings, attr, bool(payload[field]))
            else:
                setattr(settings, attr, payload[field])
            fields_to_update.append(attr)

    if fields_to_update:
        settings.save(update_fields=fields_to_update + ['updated_at'])

        AuditLog.objects.create(
            user=request.user,
            action='settings_update',
            model_name='site_settings',
            object_repr='Site Settings',
            details={'updated_fields': fields_to_update},
        )

    return JsonResponse({'success': True, 'message': 'Settings updated successfully.'})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def audit_logs(request):
    from ecommerce.admin.models import AuditLog

    return render(request, 'metis/pages/audit-logs.html', {})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_audit_logs(request):
    """API: List audit logs with pagination, filtering, sorting."""
    from ecommerce.admin.models import AuditLog

    queryset = AuditLog.objects.select_related('user').order_by('-created_at')

    action_filter = request.GET.get('action')
    if action_filter:
        queryset = queryset.filter(action__icontains=action_filter)

    model_filter = request.GET.get('model')
    if model_filter:
        queryset = queryset.filter(model_name=model_filter)

    date_filter = request.GET.get('date_filter')
    if date_filter == 'today':
        queryset = queryset.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        queryset = queryset.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7))
    elif date_filter == 'month':
        queryset = queryset.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30))

    sort_by = request.GET.get('sort', 'created_at')
    sort_dir = request.GET.get('dir', 'desc')
    if sort_dir == 'desc':
        sort_by = f'-{sort_by}'
    if sort_by.lstrip('-') in ['created_at', 'action', 'model_name', 'user__username']:
        queryset = queryset.order_by(sort_by)

    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)

    def serialize_log(log):
        return {
            'id': log.id,
            'user': str(log.user) if log.user else 'System',
            'action': log.action,
            'modelName': log.model_name,
            'objectId': log.object_id,
            'objectRepr': log.object_repr,
            'details': log.details,
            'createdAt': log.created_at.isoformat(),
        }

    return JsonResponse({
        'logs': [serialize_log(l) for l in page_obj],
        'pagination': {
            'currentPage': page_obj.number,
            'totalPages': paginator.num_pages,
            'totalItems': paginator.count,
            'perPage': per_page,
            'hasNext': page_obj.has_next(),
            'hasPrevious': page_obj.has_previous(),
        },
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def export_data(request):
    from ecommerce.ui.models import Order, Product

    export_type = request.GET.get('type', 'orders')

    if export_type == 'orders':
        queryset = Order.objects.all().values(
            'order_number', 'customer_name', 'customer_email', 'status',
            'total', 'created_at', 'payment_method'
        )
        data = list(queryset)
    elif export_type == 'products':
        queryset = Product.objects.all().values('name', 'sku', 'price', 'stock_quantity', 'is_active', 'created_at')
        data = list(queryset)
    else:
        data = []

    return JsonResponse({'data': data, 'type': export_type, 'exported_at': timezone.now().isoformat()})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics."""
    from ecommerce.ui.models import Order, Product
    from ecommerce.admin.models import AuditLog
    from django.contrib.auth import get_user_model

    User = get_user_model()

    settings = SiteSettings.load()

    # Basic stats
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total'))['total'] or 0
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='delivered').count()
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock_quantity__lte=settings.low_stock_threshold if settings else 10).count()

    # Recent activity
    recent_logs = AuditLog.objects.select_related('user').order_by('-created_at')[:5]

    data = {
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_customers': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'recent_logs': [
            {
                'action': log.action,
                'user': str(log.user),
                'created_at': log.created_at.isoformat(),
            }
            for log in recent_logs
        ],
    }
    return JsonResponse(data)


# ==================== ORDERS API ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_orders_list(request):
    """API: List orders with pagination, filtering, sorting."""
    from ecommerce.ui.models import Order

    queryset = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created_at')

    # Filters
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)

    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(order_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_email__icontains=search)
        )

    date_filter = request.GET.get('date_filter')
    if date_filter == 'today':
        queryset = queryset.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        queryset = queryset.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7))
    elif date_filter == 'month':
        queryset = queryset.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30))

    # Sorting
    sort_by = request.GET.get('sort', 'created_at')
    sort_dir = request.GET.get('dir', 'desc')
    if sort_dir == 'desc':
        sort_by = f'-{sort_by}'
    if sort_by.lstrip('-') in ['created_at', 'total', 'order_number', 'customer_name', 'status']:
        queryset = queryset.order_by(sort_by)

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 15))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)

    def serialize_order(order):
        items = order.items.all()
        return {
            'id': str(order.order_number),
            'orderNumber': str(order.order_number),
            'customer': {
                'name': order.customer_name,
                'email': order.customer_email,
                'avatar': '',
            },
            'itemCount': items.count(),
            'items': [
                {'name': item.product_name, 'quantity': item.quantity, 'price': str(item.unit_price)}
                for item in items[:3]
            ],
            'total': str(order.total),
            'status': order.status,
            'orderDate': order.created_at.strftime('%Y-%m-%d'),
            'createdAt': order.created_at.isoformat(),
        }

    return JsonResponse({
        'orders': [serialize_order(o) for o in page_obj],
        'pagination': {
            'currentPage': page_obj.number,
            'totalPages': paginator.num_pages,
            'totalItems': paginator.count,
            'perPage': per_page,
            'hasNext': page_obj.has_next(),
            'hasPrevious': page_obj.has_previous(),
        },
        'stats': {
            'total': Order.objects.count(),
            'pending': Order.objects.filter(status='pending').count(),
            'processing': Order.objects.filter(status='processing').count(),
            'shipped': Order.objects.filter(status='shipped').count(),
            'delivered': Order.objects.filter(status='delivered').count(),
            'cancelled': Order.objects.filter(status='cancelled').count(),
            'revenue': float(Order.objects.aggregate(total=Sum('total'))['total'] or 0),
        },
        'statusStats': [
            {'name': 'Pending', 'count': Order.objects.filter(status='pending').count()},
            {'name': 'Processing', 'count': Order.objects.filter(status='processing').count()},
            {'name': 'Shipped', 'count': Order.objects.filter(status='shipped').count()},
            {'name': 'Delivered', 'count': Order.objects.filter(status='delivered').count()},
            {'name': 'Cancelled', 'count': Order.objects.filter(status='cancelled').count()},
        ],
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_order_detail(request, order_number):
    """API: Get order detail."""
    from ecommerce.ui.models import Order, OrderItem

    order = get_object_or_404(Order.objects.select_related('user').prefetch_related('items__product'), order_number=order_number)
    items = order.items.all()

    return JsonResponse({
        'id': str(order.order_number),
        'orderNumber': str(order.order_number),
        'customer': {
            'name': order.customer_name,
            'email': order.customer_email,
            'phone': order.customer_phone,
        },
        'shipping': {
            'address': order.shipping_address_line_1,
            'address2': order.shipping_address_line_2,
            'city': order.shipping_city,
            'county': order.shipping_county,
            'postalCode': order.shipping_postal_code,
        },
        'items': [
            {
                'id': item.id,
                'productName': item.product_name,
                'productSku': item.product_sku,
                'quantity': item.quantity,
                'unitPrice': str(item.unit_price),
                'lineTotal': str(item.line_total),
            }
            for item in items
        ],
        'subtotal': str(order.subtotal),
        'shippingFee': str(order.shipping_fee),
        'total': str(order.total),
        'status': order.status,
        'paymentMethod': order.payment_method,
        'customerNote': order.customer_note,
        'createdAt': order.created_at.isoformat(),
        'updatedAt': order.updated_at.isoformat(),
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["PATCH", "POST"])
def api_order_update_status(request, order_number):
    """API: Update order status."""
    from ecommerce.ui.models import Order

    order = get_object_or_404(Order, order_number=order_number)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    new_status = payload.get('status')
    valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']

    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    old_status = order.status
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    # Log the change
    AuditLog.objects.create(
        user=request.user,
        action='order_status_change',
        model_name='order',
        object_repr=f'Order {order.order_number}',
        details={'old_status': old_status, 'new_status': new_status},
    )

    return JsonResponse({'success': True, 'status': order.status})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["POST"])
def api_orders_bulk(request):
    """API: Bulk update order status."""
    from ecommerce.ui.models import Order

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    order_ids = payload.get('order_ids', [])
    new_status = payload.get('status')

    if not order_ids or new_status not in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    orders = Order.objects.filter(order_number__in=order_ids)
    updated_count = 0

    for order in orders:
        old_status = order.status
        if old_status != new_status:
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
            updated_count += 1

            AuditLog.objects.create(
                user=request.user,
                action='order_status_change',
                model_name='order',
                object_repr=f'Order {order.order_number}',
                details={'old_status': old_status, 'new_status': new_status, 'bulk': True},
            )

    return JsonResponse({'success': True, 'updated': updated_count})


# ==================== PRODUCTS API ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_products_list(request):
    """API: List products with pagination, filtering, sorting."""
    from ecommerce.ui.models import Product, Category

    queryset = Product.objects.select_related('category').order_by('-created_at')

    # Filters
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        settings = SiteSettings.load()
        threshold = settings.low_stock_threshold if settings else 10
        queryset = queryset.filter(stock_quantity__lte=threshold, stock_quantity__gt=0)
    elif stock_filter == 'out':
        queryset = queryset.filter(stock_quantity=0)
    elif stock_filter == 'in':
        queryset = queryset.filter(stock_quantity__gt=0)

    # Sorting
    sort_by = request.GET.get('sort', 'created_at')
    sort_dir = request.GET.get('dir', 'desc')
    if sort_dir == 'desc':
        sort_by = f'-{sort_by}'
    if sort_by.lstrip('-') in ['created_at', 'name', 'price', 'stock_quantity', 'is_active']:
        queryset = queryset.order_by(sort_by)

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 15))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)

    def serialize_product(product):
        return {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'slug': product.slug,
            'category': {
                'id': product.category.id if product.category else None,
                'name': product.category.name if product.category else 'Uncategorized',
                'slug': product.category.slug if product.category else '',
            },
            'price': str(product.price),
            'compareAtPrice': str(product.compare_at_price) if product.compare_at_price else None,
            'stockQuantity': product.stock_quantity,
            'isActive': product.is_active,
            'isFeatured': product.is_featured,
            'image': product.image,
            'createdAt': product.created_at.isoformat(),
        }

    categories = Category.objects.filter(is_active=True).values('id', 'name', 'slug')

    # Stats
    settings = SiteSettings.load()
    threshold = settings.low_stock_threshold if settings else 10
    total_value = sum(
        Decimal(str(p.price)) * p.stock_quantity
        for p in Product.objects.filter(is_active=True)
    )

    return JsonResponse({
        'products': [serialize_product(p) for p in page_obj],
        'categories': list(categories),
        'pagination': {
            'currentPage': page_obj.number,
            'totalPages': paginator.num_pages,
            'totalItems': paginator.count,
            'perPage': per_page,
            'hasNext': page_obj.has_next(),
            'hasPrevious': page_obj.has_previous(),
        },
        'stats': {
            'total': Product.objects.count(),
            'inStock': Product.objects.filter(stock_quantity__gt=0).count(),
            'lowStock': Product.objects.filter(stock_quantity__lte=threshold, stock_quantity__gt=0).count(),
            'outOfStock': Product.objects.filter(stock_quantity=0).count(),
            'totalValue': float(total_value),
        },
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_product_detail(request, product_id):
    """API: Get product detail."""
    from ecommerce.ui.models import Product

    product = get_object_or_404(Product.objects.select_related('category'), pk=product_id)

    return JsonResponse({
        'id': product.id,
        'sku': product.sku,
        'name': product.name,
        'slug': product.slug,
        'description': product.description,
        'category': {
            'id': product.category.id if product.category else None,
            'name': product.category.name if product.category else '',
            'slug': product.category.slug if product.category else '',
        },
        'price': str(product.price),
        'compareAtPrice': str(product.compare_at_price) if product.compare_at_price else None,
        'stockQuantity': product.stock_quantity,
        'isActive': product.is_active,
        'isFeatured': product.is_featured,
        'image': product.image,
        'createdAt': product.created_at.isoformat(),
        'updatedAt': product.updated_at.isoformat(),
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["POST"])
def api_product_create(request):
    """API: Create product."""
    from ecommerce.ui.models import Product, Category

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    required_fields = ['name', 'sku', 'price']
    for field in required_fields:
        if not payload.get(field):
            return JsonResponse({'error': f'{field} is required'}, status=400)

    if Product.objects.filter(sku=payload['sku']).exists():
        return JsonResponse({'error': 'SKU already exists'}, status=400)

    category = None
    if payload.get('category'):
        category = get_object_or_404(Category, pk=payload['category'])

    product = Product.objects.create(
        name=payload['name'],
        slug=payload['name'].lower().replace(' ', '-')[:200],
        sku=payload['sku'],
        description=payload.get('description', ''),
        category=category,
        price=Decimal(payload['price']),
        compare_at_price=Decimal(payload['compare_at_price']) if payload.get('compare_at_price') else None,
        stock_quantity=payload.get('stock_quantity', 0),
        is_active=payload.get('is_active', True),
        is_featured=payload.get('is_featured', False),
        image=payload.get('image', ''),
    )

    AuditLog.objects.create(
        user=request.user,
        action='product_create',
        model_name='product',
        object_repr=f'Product {product.name}',
        details={'sku': product.sku},
    )

    return JsonResponse({'success': True, 'id': product.id, 'sku': product.sku})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["PATCH", "PUT"])
def api_product_update(request, product_id):
    """API: Update product."""
    from ecommerce.ui.models import Product, Category

    product = get_object_or_404(Product, pk=product_id)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'sku' in payload and payload['sku'] != product.sku:
        if Product.objects.filter(sku=payload['sku']).exclude(pk=product_id).exists():
            return JsonResponse({'error': 'SKU already exists'}, status=400)

    fields_to_update = []
    for field in ['name', 'sku', 'description', 'price', 'compare_at_price', 'stock_quantity', 'is_active', 'is_featured', 'image']:
        if field in payload:
            if field == 'price':
                setattr(product, field, Decimal(payload[field]))
            elif field == 'compare_at_price' and payload[field]:
                setattr(product, field, Decimal(payload[field]))
            elif field == 'category':
                if payload[field]:
                    setattr(product, field, get_object_or_404(Category, pk=payload[field]))
                else:
                    setattr(product, field, None)
            else:
                setattr(product, field, payload[field])
            fields_to_update.append(field)

    if 'name' in payload:
        product.slug = payload['name'].lower().replace(' ', '-')[:200]
        fields_to_update.append('slug')

    if fields_to_update:
        fields_to_update.append('updated_at')
        product.save(update_fields=fields_to_update)

        AuditLog.objects.create(
            user=request.user,
            action='product_update',
            model_name='product',
            object_repr=f'Product {product.name}',
            details={'updated_fields': fields_to_update},
        )

    return JsonResponse({'success': True, 'id': product.id})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["DELETE"])
def api_product_delete(request, product_id):
    """API: Delete product."""
    from ecommerce.ui.models import Product

    product = get_object_or_404(Product, pk=product_id)
    product_name = product.name
    product_sku = product.sku

    product.delete()

    AuditLog.objects.create(
        user=request.user,
        action='product_delete',
        model_name='product',
        object_repr=f'Product {product_name}',
        details={'sku': product_sku},
    )

    return JsonResponse({'success': True})


# ==================== USERS API ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_users_list(request):
    """API: List users with pagination, filtering, sorting."""
    from django.contrib.auth import get_user_model
    from ecommerce.ui.models import Order

    User = get_user_model()

    queryset = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')

    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    status_filter = request.GET.get('status')
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    sort_by = request.GET.get('sort', 'date_joined')
    sort_dir = request.GET.get('dir', 'desc')
    if sort_dir == 'desc':
        sort_by = f'-{sort_by}'
    if sort_by.lstrip('-') in ['date_joined', 'username', 'email', 'is_active']:
        queryset = queryset.order_by(sort_by)

    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 15))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)

    def serialize_user(user):
        order_count = Order.objects.filter(user=user).count()
        total_spent = Order.objects.filter(user=user).aggregate(total=Sum('total'))['total'] or 0
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'fullName': f"{user.first_name} {user.last_name}".strip() or user.username,
            'isActive': user.is_active,
            'dateJoined': user.date_joined.isoformat(),
            'orderCount': order_count,
            'totalSpent': float(total_spent),
        }

    # Stats
    now = timezone.now()
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return JsonResponse({
        'users': [serialize_user(u) for u in page_obj],
        'pagination': {
            'currentPage': page_obj.number,
            'totalPages': paginator.num_pages,
            'totalItems': paginator.count,
            'perPage': per_page,
            'hasNext': page_obj.has_next(),
            'hasPrevious': page_obj.has_previous(),
        },
        'stats': {
            'total': User.objects.filter(is_staff=False, is_superuser=False).count(),
            'active': User.objects.filter(is_staff=False, is_superuser=False, is_active=True).count(),
            'inactive': User.objects.filter(is_staff=False, is_superuser=False, is_active=False).count(),
            'newThisMonth': User.objects.filter(is_staff=False, is_superuser=False, date_joined__gte=this_month).count(),
        },
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_user_detail(request, user_id):
    """API: Get user detail with orders."""
    from django.contrib.auth import get_user_model
    from ecommerce.ui.models import Order

    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)

    orders = Order.objects.filter(user=user).order_by('-created_at')[:10]

    return JsonResponse({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'isActive': user.is_active,
        'isStaff': user.is_staff,
        'dateJoined': user.date_joined.isoformat(),
        'lastLogin': user.last_login.isoformat() if user.last_login else None,
        'orders': [
            {
                'id': str(o.order_number),
                'orderNumber': str(o.order_number),
                'status': o.status,
                'total': str(o.total),
                'createdAt': o.created_at.isoformat(),
            }
            for o in orders
        ],
        'orderCount': Order.objects.filter(user=user).count(),
        'totalSpent': float(Order.objects.filter(user=user).aggregate(total=Sum('total'))['total'] or 0),
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["PATCH", "PUT"])
def api_user_update(request, user_id):
    """API: Update user (activate/deactivate, etc.)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    fields_to_update = []
    for field in ['is_active', 'first_name', 'last_name', 'email']:
        if field in payload:
            setattr(user, field, payload[field])
            fields_to_update.append(field)

    if fields_to_update:
        user.save(update_fields=fields_to_update)

        AuditLog.objects.create(
            user=request.user,
            action='user_update',
            model_name='user',
            object_repr=f'User {user.username}',
            details={'updated_fields': fields_to_update},
        )

    return JsonResponse({'success': True, 'id': user.id, 'isActive': user.is_active})


# ==================== CATEGORIES API ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_categories_list(request):
    """API: List categories."""
    from ecommerce.ui.models import Category

    categories = Category.objects.all().order_by('name')
    return JsonResponse({
        'categories': [
            {
                'id': c.id,
                'name': c.name,
                'slug': c.slug,
                'description': c.description,
                'isActive': c.is_active,
                'productCount': c.products.count(),
                'createdAt': c.created_at.isoformat(),
            }
            for c in categories
        ],
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["POST"])
def api_category_create(request):
    """API: Create category."""
    from ecommerce.ui.models import Category

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    slug = (payload.get('slug') or name.lower().replace(' ', '-')).strip()
    if Category.objects.filter(slug=slug).exists():
        return JsonResponse({'error': 'Slug already exists'}, status=400)

    category = Category.objects.create(
        name=name,
        slug=slug,
        description=payload.get('description', ''),
        is_active=payload.get('is_active', True),
    )
    return JsonResponse({'success': True, 'id': category.id, 'slug': category.slug})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["PATCH", "PUT"])
def api_category_update(request, category_id):
    """API: Update category."""
    from ecommerce.ui.models import Category

    category = get_object_or_404(Category, pk=category_id)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    fields_to_update = []
    for field in ['name', 'slug', 'description', 'is_active']:
        if field in payload:
            setattr(category, field, payload[field])
            fields_to_update.append(field)

    if fields_to_update:
        category.save(update_fields=fields_to_update)

    return JsonResponse({'success': True, 'id': category.id})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["DELETE"])
def api_category_delete(request, category_id):
    """API: Delete category."""
    from ecommerce.ui.models import Category

    category = get_object_or_404(Category, pk=category_id)
    category.delete()
    return JsonResponse({'success': True})


# ==================== USERS API (create / delete) ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["POST"])
def api_user_create(request):
    """API: Create user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = (payload.get('username') or '').strip()
    email = (payload.get('email') or '').strip()
    password = payload.get('password', '')

    if not username or not email or not password:
        return JsonResponse({'error': 'Username, email, and password are required'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    user.first_name = payload.get('first_name', '')
    user.last_name = payload.get('last_name', '')
    user.is_active = payload.get('is_active', True)
    user.is_staff = payload.get('is_staff', False)
    user.save()

    return JsonResponse({'success': True, 'id': user.id, 'username': user.username})


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
@require_http_methods(["DELETE"])
def api_user_delete(request, user_id):
    """API: Delete user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)

    if user.pk == request.user.pk:
        return JsonResponse({'error': 'Cannot delete yourself'}, status=400)

    user.delete()
    return JsonResponse({'success': True})


# ==================== DASHBOARD API ====================

@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_dashboard_charts(request):
    """API: Dashboard chart data."""
    from ecommerce.ui.models import Order, Product
    from django.contrib.auth import get_user_model
    from django.db.models import Count
    from django.db.models.functions import TruncDay

    User = get_user_model()
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timezone.timedelta(days=days)

    try:
        # Revenue by day
        revenue_by_day = (
            Order.objects.filter(created_at__gte=start_date)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('total'))
            .order_by('day')
        )
        revenue_labels = [r['day'].strftime('%b %d') for r in revenue_by_day]
        revenue_data = [float(r['total']) for r in revenue_by_day]

        # User growth by day
        user_growth = (
            User.objects.filter(date_joined__gte=start_date, is_staff=False, is_superuser=False)
            .annotate(day=TruncDay('date_joined'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        user_labels = [u['day'].strftime('%b %d') for u in user_growth]
        user_data = [u['count'] for u in user_growth]

        # Order status distribution
        status_dist = (
            Order.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )
        status_labels = [s['status'].title() for s in status_dist]
        status_data = [s['count'] for s in status_dist]
    except Exception:
        revenue_labels = revenue_data = user_labels = user_data = status_labels = status_data = []

    return JsonResponse({
        'revenue': {'labels': revenue_labels, 'data': revenue_data},
        'user_growth': {'labels': user_labels, 'data': user_data},
        'order_status': {'labels': status_labels, 'data': status_data},
    })


@admin_login_required
@user_passes_test(lambda u: StaffProfile.objects.filter(user=u, is_active=True).exists())
def api_dashboard_recent_orders(request):
    """API: Recent orders for dashboard table."""
    from ecommerce.ui.models import Order

    limit = int(request.GET.get('limit', 5))

    try:
        orders = Order.objects.select_related('user').order_by('-created_at')[:limit]
        data = []
        for order in orders:
            data.append({
                'order_number': order.order_number,
                'customer': order.user.get_full_name() or order.user.username if order.user else 'Guest',
                'email': order.user.email if order.user else '',
                'total': float(order.total),
                'status': order.status,
                'created_at': order.created_at.strftime('%b %d, %Y %H:%M'),
            })
    except Exception:
        data = []

    return JsonResponse({'orders': data})
