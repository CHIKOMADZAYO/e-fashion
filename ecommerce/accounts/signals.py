from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from ecommerce.ui.models import Cart, CartItem


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, user, request, **kwargs):
    """Merge a guest (session) cart into the authenticated user's cart on login."""
    session_key = request.session.session_key
    if not session_key:
        return
    guest_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if not guest_cart:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user, defaults={"session_key": ""})
    for item in guest_cart.items.select_related("product").all():
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity", "updated_at"])
        else:
            item.cart = user_cart
            item.save(update_fields=["cart", "updated_at"])
    guest_cart.items.all().delete()
    guest_cart.delete()
