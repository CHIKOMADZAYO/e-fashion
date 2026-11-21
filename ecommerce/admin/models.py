from django.conf import settings
from django.db import models
from django.utils import timezone


class StaffProfile(models.Model):
    """Staff/admin user profile with role-based access."""

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Administrator"
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Manager"
        SUPPORT = "support", "Support Staff"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False, help_text="Must be approved by a superadmin before they can log in.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "staff profile"
        verbose_name_plural = "staff profiles"
        indexes = [models.Index(fields=["role", "is_active"])]

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"


class SiteSettings(models.Model):
    """Global store configuration editable from the admin (singleton)."""

    site_name = models.CharField(max_length=100, default="Upstep")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_address = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="KES")
    low_stock_threshold = models.PositiveIntegerField(default=10)
    default_shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    maintenance_mode = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settings_updates",
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Enforce a single settings row.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditLog(models.Model):
    """Immutable audit trail of administrative actions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.action} on {self.model_name} ({self.created_at:%Y-%m-%d %H:%M})"
