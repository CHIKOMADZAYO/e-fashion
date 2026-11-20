from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Product,
    Wishlist,
    WishlistItem,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock_quantity", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "category")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "sku", "description")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "product_sku", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer_name", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "customer_name", "customer_email")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = (OrderItemInline,)


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(WishlistItem)
