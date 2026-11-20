from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ecommerce.ui.models import Product

from .models import AdminNotification, AuditLog, SiteSettings, StaffProfile

User = get_user_model()


class StaffProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff1", email="staff@example.com", password="pass1234",
            is_staff=True,
        )

    def test_staff_profile_creation(self):
        profile = StaffProfile.objects.create(
            user=self.user, role=StaffProfile.Role.ADMIN, is_active=True,
        )
        self.assertEqual(str(profile), "staff1 (Administrator)")
        self.assertTrue(profile.is_active)


class SiteSettingsTest(TestCase):
    def test_singleton_settings(self):
        s1 = SiteSettings.load()
        s1.site_name = "My Store"
        s1.save()
        s2 = SiteSettings.load()
        self.assertEqual(s1.pk, s2.pk)
        self.assertEqual(s2.site_name, "My Store")
        self.assertEqual(SiteSettings.objects.count(), 1)


class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin1", email="admin@example.com", password="pass1234",
            is_staff=True,
        )

    def test_audit_log_creation(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="create",
            model_name="Product",
            object_id="1",
            object_repr="Test Product",
            details={},
        )
        self.assertIn("create", str(log))
        self.assertIn("Product", str(log))


class AdminNotificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin2", email="admin2@example.com", password="pass1234",
            is_staff=True,
        )

    def test_notification_creation(self):
        notif = AdminNotification.objects.create(
            recipient=self.user,
            title="New Order",
            message="A new order was placed.",
            level=AdminNotification.Level.INFO,
        )
        self.assertEqual(str(notif), "New Order — admin2")
        self.assertFalse(notif.is_read)


class DashboardViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin3", email="admin3@example.com", password="pass1234",
            is_staff=True, is_superuser=True,
        )
        self.client.login(username="admin3", password="pass1234")

    def test_dashboard_requires_staff(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_stats_api(self):
        response = self.client.get(reverse("dashboard_stats_api"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("orders_by_status", response.json())


class ModelsSmokeTest(TestCase):
    def test_product_str(self):
        product = Product.objects.create(
            name="Test Widget", sku="TW-001", price="9.99", stock_quantity=5,
        )
        self.assertEqual(str(product), "Test Widget")
