from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ecommerce.ui.models import Order
from .forms import AccountDetailsForm, AddressForm, CustomerProfileForm, RegistrationForm
from .models import Address, CustomerProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("account_profile")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        CustomerProfile.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, "Your Upsteps account is ready.")
        return redirect("account_profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    details_form = AccountDetailsForm(request.POST or None, instance=request.user, prefix="details")
    profile_form = CustomerProfileForm(
        request.POST or None,
        instance=customer_profile,
        prefix="profile",
    )
    if request.method == "POST":
        if details_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                details_form.save()
                profile_form.save()
            messages.success(request, "Your account details have been saved.")
            return redirect("account_profile")

    recent_orders = Order.objects.filter(user=request.user).prefetch_related("items")[:5]
    return render(request, "accounts/profile.html", {
        "details_form": details_form,
        "profile_form": profile_form,
        "recent_orders": recent_orders,
        "address_count": Address.objects.filter(user=request.user).count(),
    })


@login_required
def addresses(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            first_address = not Address.objects.filter(user=request.user).exists()
            address = form.save(commit=False)
            address.user = request.user
            address.is_default = address.is_default or first_address
            if address.is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.save()
        messages.success(request, "Your delivery address has been saved.")
        return redirect("account_addresses")
    return render(request, "accounts/addresses.html", {
        "form": form,
        "addresses": Address.objects.filter(user=request.user),
    })


@login_required
def set_default_address(request, pk):
    if request.method != "POST":
        return redirect("account_addresses")
    address = get_object_or_404(Address, pk=pk, user=request.user)
    with transaction.atomic():
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
    messages.success(request, "Your default delivery address has been updated.")
    return redirect("account_addresses")


@login_required
def delete_address(request, pk):
    if request.method != "POST":
        return redirect("account_addresses")
    with transaction.atomic():
        address = get_object_or_404(Address, pk=pk, user=request.user)
        was_default = address.is_default
        address.delete()
        if was_default:
            replacement = Address.objects.filter(user=request.user).first()
            if replacement:
                replacement.is_default = True
                replacement.save(update_fields=["is_default", "updated_at"])
    messages.success(request, "The delivery address has been removed.")
    return redirect("account_addresses")


@login_required
def order_history(request):
    """List the customer's past orders."""
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, "accounts/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    """Show a single order's details."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        order_number=order_number,
        user=request.user,
    )
    return render(request, "accounts/order_detail.html", {"order": order})
