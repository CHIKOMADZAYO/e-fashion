import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    """A payment attempt for a store order; never store card credentials here."""

    class Method(models.TextChoices):
        PAY_ON_DELIVERY = "pay_on_delivery", "Pay on delivery"
        MPESA = "mpesa", "M-Pesa"
        CARD = "card", "Card"

    class Provider(models.TextChoices):
        MANUAL = "manual", "Manual / pay on delivery"
        MPESA = "mpesa", "M-Pesa provider"
        CARD_GATEWAY = "card_gateway", "Card payment gateway"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        "ui.Order", on_delete=models.PROTECT, related_name="payments",
    )
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    method = models.CharField(max_length=16, choices=Method.choices)
    provider = models.CharField(
        max_length=16, choices=Provider.choices, default=Provider.MANUAL,
    )
    provider_reference = models.CharField(
        max_length=150, unique=True, null=True, blank=True,
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    currency = models.CharField(max_length=3, default="KES")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"], name="payments_order_status_idx"),
            models.Index(fields=["provider", "created_at"], name="payments_provider_time_idx"),
        ]

    def __str__(self):
        return f"{self.get_method_display()} {self.reference} ({self.get_status_display()})"


class PaymentEvent(models.Model):
    """A deduplicated provider event used to audit and reconcile payment updates."""

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="events",
    )
    provider_event_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    event_type = models.CharField(max_length=100)
    data = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        ordering = ["received_at"]
        indexes = [
            models.Index(fields=["payment", "received_at"], name="payments_event_time_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} for {self.payment.reference}"
