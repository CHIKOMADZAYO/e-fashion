from django.contrib import admin

from .models import Address, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "county", "updated_at")
    search_fields = ("user__username", "user__email", "phone", "city", "county")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "county", "is_default", "updated_at")
    list_filter = ("is_default", "county", "city")
    search_fields = ("full_name", "user__username", "user__email", "phone", "city")
