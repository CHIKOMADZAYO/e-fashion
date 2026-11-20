from django.contrib import admin

from .models import Payment, PaymentEvent


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    can_delete = False
    readonly_fields = (
        "provider_event_id", "event_type", "data", "received_at",
        "processed_at", "processing_error",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "order", "method", "provider", "amount", "currency",
        "status", "created_at",
    )
    list_filter = ("status", "method", "provider", "currency", "created_at")
    search_fields = ("reference", "provider_reference", "order__customer_email")
    readonly_fields = (
        "reference", "idempotency_key", "provider_reference", "amount",
        "currency", "metadata", "created_at", "updated_at", "completed_at",
    )
    inlines = (PaymentEventInline,)


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "payment", "provider_event_id", "received_at", "processed_at")
    list_filter = ("event_type", "received_at", "processed_at")
    search_fields = ("provider_event_id", "payment__reference", "payment__provider_reference")
    readonly_fields = (
        "payment", "provider_event_id", "event_type", "data", "received_at",
        "processed_at", "processing_error",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
