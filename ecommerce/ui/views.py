import json
import os
from decimal import Decimal
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ecommerce.admin.models import AuditLog
from .models import Cart, Category, Order, OrderItem, Product, Wishlist, WishlistItem

# Create your views here.

@ensure_csrf_cookie
def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True).select_related('category')[:8]
    if not featured_products:
        featured_products = Product.objects.filter(is_active=True).select_related('category')[:8]
    return render(request, 'ui/index.html', {
        'featured_products': featured_products,
        'categories': Category.objects.filter(is_active=True),
    })


@ensure_csrf_cookie
def store_page(request, page):
    available_pages = {
        'about', 'blog', 'blog-detail', 'contact', 'home-02', 'home-03',
        'product', 'product-detail', 'shoping-cart', 'checkout', 'wishlist',
    }
    if page not in available_pages:
        raise Http404('Store page not found.')
    context = {}
    if page == 'product':
        products = Product.objects.filter(is_active=True).select_related('category')
        category_slug = request.GET.get('category', '').strip()
        search_query = request.GET.get('q', '').strip()
        if category_slug:
            products = products.filter(category__slug=category_slug)
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(category__name__icontains=search_query)
            )
        context.update({
            'products': products,
            'categories': Category.objects.filter(is_active=True),
            'selected_category': category_slug,
            'search_query': search_query,
        })
    elif page == 'product-detail' and request.GET.get('product'):
        identifier = request.GET['product'].strip()
        product = Product.objects.filter(is_active=True).select_related('category').filter(
            Q(slug=identifier) | Q(sku=identifier)
        ).first()
        if product:
            context['product'] = product
        elif identifier not in {f'up-{number:03}' for number in range(1, 17)}:
            raise Http404('Product not found.')
    return render(request, f'ui/{page}.html', context)


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_cart(request):
    return Cart.objects.get_or_create(session_key=_session_key(request))[0]


def _get_wishlist(request):
    return Wishlist.objects.get_or_create(session_key=_session_key(request))[0]


def _image_url(product):
    if not product.image:
        return ""
    if product.image.startswith(("https://", "http://")):
        return product.image
    return static(product.image)


def _product_url(product):
    return f"{reverse('store_page', args=['product-detail'])}?product={product.slug}"


def _cart_payload(cart):
    items = list(cart.items.select_related("product", "product__category"))
    subtotal = sum((item.line_total for item in items), Decimal("0.00"))
    shipping = Decimal("0.00") if subtotal == 0 or subtotal >= Decimal("6499.50") else Decimal("350.00")
    return {
        "items": [{
            "id": item.product.sku,
            "slug": item.product.slug,
            "product_url": _product_url(item.product),
            "name": item.product.name,
            "category": item.product.category.slug if item.product.category else "other",
            "price": str(item.product.price),
            "image": _image_url(item.product),
            "quantity": item.quantity,
            "line_total": str(item.line_total),
            "stock_quantity": item.product.stock_quantity,
        } for item in items],
        "item_count": sum(item.quantity for item in items),
        "subtotal": str(subtotal),
        "shipping": str(shipping),
        "total": str(subtotal + shipping),
    }


def _wishlist_payload(wishlist):
    return [{
        "id": item.product.sku,
        "slug": item.product.slug,
        "product_url": _product_url(item.product),
        "name": item.product.name,
        "category": item.product.category.slug if item.product.category else "other",
        "price": str(item.product.price),
        "image": _image_url(item.product),
    } for item in wishlist.items.select_related("product", "product__category")]


def _read_json(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _find_product(identifier):
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    return Product.objects.filter(is_active=True).filter(
        Q(slug=identifier.strip()) | Q(sku=identifier.strip())
    ).first()


@ensure_csrf_cookie
def store_state(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    cart = _get_cart(request)
    wishlist = _get_wishlist(request)
    return JsonResponse({"cart": _cart_payload(cart), "wishlist": _wishlist_payload(wishlist)})


@require_POST
def cart_add(request):
    payload = _read_json(request)
    product = _find_product(payload.get("product_id") if payload else None)
    if not product:
        return JsonResponse({"error": "That product is unavailable. Refresh the shop and try again."}, status=404)
    try:
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Enter a valid quantity."}, status=400)
    if quantity < 1:
        return JsonResponse({"error": "Quantity must be at least one."}, status=400)
    cart = _get_cart(request)
    item, created = cart.items.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity", "updated_at"])
    if item.quantity > product.stock_quantity:
        item.quantity -= quantity
        if item.quantity:
            item.save(update_fields=["quantity", "updated_at"])
        else:
            item.delete()
        return JsonResponse({"error": "There is not enough stock for that quantity."}, status=409)
    cart.save(update_fields=["updated_at"])
    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='add_to_cart',
            model_name='product',
            object_id=str(product.id),
            object_repr=product.name,
            details={'quantity': quantity, 'session_key': request.session.session_key or ''},
        )
    except Exception:
        pass
    return JsonResponse({"cart": _cart_payload(cart), "product_name": product.name})


@require_POST
def cart_update(request):
    payload = _read_json(request)
    if payload is None:
        return JsonResponse({"error": "Send valid cart details."}, status=400)
    product = _find_product(payload.get("product_id"))
    if not product:
        return JsonResponse({"error": "That product is unavailable."}, status=404)
    try:
        quantity = int(payload.get("quantity"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Enter a valid quantity."}, status=400)
    if quantity < 1 or quantity > product.stock_quantity:
        return JsonResponse({"error": "That quantity is not available."}, status=409)
    cart = _get_cart(request)
    updated = cart.items.filter(product=product).update(quantity=quantity)
    if not updated:
        return JsonResponse({"error": "That item is no longer in your bag."}, status=404)
    cart.save(update_fields=["updated_at"])
    return JsonResponse({"cart": _cart_payload(cart)})


@require_POST
def cart_remove(request):
    payload = _read_json(request)
    product = _find_product(payload.get("product_id") if payload else None)
    if not product:
        return JsonResponse({"error": "That product is unavailable."}, status=404)
    cart = _get_cart(request)
    cart.items.filter(product=product).delete()
    cart.save(update_fields=["updated_at"])
    return JsonResponse({"cart": _cart_payload(cart)})


@require_POST
def cart_clear(request):
    cart = _get_cart(request)
    cart.items.all().delete()
    cart.save(update_fields=["updated_at"])
    return JsonResponse({"cart": _cart_payload(cart)})


@require_POST
def wishlist_toggle(request):
    payload = _read_json(request)
    product = _find_product(payload.get("product_id") if payload else None)
    if not product:
        return JsonResponse({"error": "That product is unavailable."}, status=404)
    wishlist = _get_wishlist(request)
    item = wishlist.items.filter(product=product)
    removed = item.exists()
    if removed:
        item.delete()
    else:
        wishlist.items.create(product=product)
    wishlist.save(update_fields=["updated_at"])
    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='wishlist_removed' if removed else 'wishlist_added',
            model_name='product',
            object_id=str(product.id),
            object_repr=product.name,
            details={'session_key': request.session.session_key or ''},
        )
    except Exception:
        pass
    return JsonResponse({"wishlist": _wishlist_payload(wishlist), "saved": not removed})


@login_required
@require_POST
def checkout_submit(request):
    payload = _read_json(request)
    if payload is None:
        return JsonResponse({"error": "Send valid checkout details."}, status=400)
    fields = ("first_name", "last_name", "email", "phone", "address", "city", "county")
    values = {field: str(payload.get(field, "")).strip() for field in fields}
    if any(not values[field] for field in fields):
        return JsonResponse({"error": "Complete all required contact and delivery fields."}, status=400)
    maximum_lengths = {
        "first_name": 90, "last_name": 90, "email": 254, "phone": 32,
        "address": 255, "city": 100, "county": 100,
    }
    if any(len(values[field]) > limit for field, limit in maximum_lengths.items()):
        return JsonResponse({"error": "One or more checkout fields are too long."}, status=400)
    try:
        validate_email(values["email"])
    except ValidationError:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    payment_method = payload.get("payment_method", "pay_on_delivery")
    if payment_method not in {
        Order.PaymentMethod.PAY_ON_DELIVERY,
        Order.PaymentMethod.MPESA,
    }:
        return JsonResponse({"error": "Choose pay on delivery or M-Pesa."}, status=400)

    cart = _get_cart(request)
    try:
        with transaction.atomic():
            cart_items = list(cart.items.select_related("product").select_for_update())
            if not cart_items:
                return JsonResponse({"error": "Your bag is empty."}, status=400)
            product_ids = [item.product_id for item in cart_items]
            locked_products = Product.objects.select_for_update().in_bulk(product_ids)
            subtotal = Decimal("0.00")
            for item in cart_items:
                product = locked_products.get(item.product_id)
                if not product or not product.is_active or product.stock_quantity < item.quantity:
                    return JsonResponse({"error": f"{item.product.name} no longer has enough stock. Please update your bag."}, status=409)
                subtotal += product.price * item.quantity
            shipping = Decimal("0.00") if subtotal >= Decimal("6499.50") else Decimal("350.00")
            total = subtotal + shipping
            if payment_method == Order.PaymentMethod.MPESA and total != total.to_integral_value():
                return JsonResponse({
                    "error": "M-Pesa requires a whole-KSh order total. Adjust product prices or choose pay on delivery."
                }, status=400)
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or "",
                customer_name=f"{values['first_name']} {values['last_name']}"[:180],
                customer_email=values["email"],
                customer_phone=values["phone"][:32],
                shipping_address_line_1=values["address"][:255],
                shipping_city=values["city"][:100],
                shipping_county=values["county"][:100],
                currency="KES",
                subtotal=subtotal,
                shipping_fee=shipping,
                total=total,
                status=Order.Status.PENDING,
                payment_method=payment_method,
            )
            for item in cart_items:
                product = locked_products[item.product_id]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    unit_price=product.price,
                    quantity=item.quantity,
                )
                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity", "updated_at"])
            cart.items.all().delete()
    except Exception:
        return JsonResponse({"error": "We could not place your order. Please try again."}, status=500)

    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='order_placed',
            model_name='order',
            object_id=str(order.order_number),
            object_repr=f'Order #{order.order_number}',
            details={
                'customer_email': order.customer_email,
                'customer_name': order.customer_name,
                'total': str(order.total),
                'payment_method': order.payment_method,
                'session_key': request.session.session_key or '',
            },
        )
    except Exception:
        pass

    return JsonResponse({
        "order_number": str(order.order_number),
        "total": str(order.total),
        "status": order.get_status_display(),
    })


def track_order(request):
    """Track an order by order number."""
    order = None
    error = None
    order_number = ""

    if request.method == "GET" and request.GET.get("order_number"):
        order_number = (request.GET.get("order_number") or "").strip()
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                error = "No order found with that number. Please check and try again."
            except (ValueError, TypeError):
                error = "Invalid order number format."
    elif request.method == "POST":
        order_number = (request.POST.get("order_number") or "").strip()

        if not order_number:
            error = "Please enter your order number."
        else:
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                error = "No order found with that number. Please check and try again."
            except (ValueError, TypeError):
                error = "Invalid order number format."

    return render(request, "ui/track-order.html", {
        "order": order,
        "error": error,
        "order_number": order_number,
    })


@require_POST
def support_chat(request):
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    if cache.add(rate_key, 1, timeout=60):
        request_count = 1
    else:
        try:
            request_count = cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, timeout=60)
            request_count = 1
    if request_count > 12:
        return JsonResponse({
            'error': 'You have sent several messages. Please wait a minute before trying again.'
        }, status=429)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Please send a valid message.'}, status=400)

    messages = payload.get('messages') if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return JsonResponse({'error': 'Please send a valid message.'}, status=400)

    conversation = []
    for message in messages[-10:]:
        if not isinstance(message, dict) or message.get('role') not in {'user', 'assistant'}:
            continue
        content = message.get('content')
        if isinstance(content, str) and content.strip():
            conversation.append({
                'role': message['role'],
                'content': content.strip()[:1500],
            })

    if not conversation or conversation[-1]['role'] != 'user':
        return JsonResponse({'error': 'Please enter a message to continue.'}, status=400)

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return JsonResponse({
            'error': 'AI support is not connected yet. Please email hello@example.com for help.'
        }, status=503)

    request_body = json.dumps({
        'model': os.environ.get('OPENAI_MODEL', 'gpt-6-luna'),
        'instructions': (
            'You are Upsteps customer support. Be friendly, concise, and helpful. '
            'Answer general questions about shopping, shipping, returns, and using the store. '
            'You cannot view orders, change accounts, process refunds, or access customer data. '
            'Never claim you have completed an action or know an order status. '
            'Do not invent store policies, delivery times, prices, or return terms that are not provided. '
            'If you do not know a store-specific answer, say so and direct the customer to support. '
            'For account-specific help, direct the customer to hello@example.com. '
            'Do not ask for passwords, card numbers, or other payment credentials.'
        ),
        'input': conversation,
        'max_output_tokens': 300,
        'store': False,
    }).encode('utf-8')
    api_request = Request(
        'https://api.openai.com/v1/responses',
        data=request_body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(api_request, timeout=25) as response:
            result = json.loads(response.read().decode('utf-8'))
    except (OSError, json.JSONDecodeError):
        return JsonResponse({
            'error': 'Support chat is temporarily unavailable. Please try again shortly.'
        }, status=502)

    answer = ''
    for output_item in result.get('output', []):
        if output_item.get('type') != 'message':
            continue
        for content_item in output_item.get('content', []):
            if content_item.get('type') == 'output_text':
                answer += content_item.get('text', '')

    if not answer.strip():
        return JsonResponse({
            'error': 'I could not prepare a reply. Please try again.'
        }, status=502)
    return JsonResponse({'reply': answer.strip()})


