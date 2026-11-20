from django.contrib import admin

from .models import AuditLog, SiteSettings, StaffProfile

# Note: Category, Product, Order, Cart, CartItem, Wishlist and WishlistItem
# are already registered with django.contrib.admin.site by ecommerce.ui.admin.
# This file registers only the models specific to the admin app.


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("user__username", "user__email")
    list_editable = ("role", "is_active")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "site_name", "contact_email", "currency", "maintenance_mode", "updated_at",
    )
    list_editable = ("maintenance_mode",)
    readonly_fields = ("updated_at", "updated_by")

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "object_repr", "created_at")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("user__username", "action", "model_name", "object_repr")
    readonly_fields = (
        "user", "action", "model_name", "object_id", "object_repr",
        "details", "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
