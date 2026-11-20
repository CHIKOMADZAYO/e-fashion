import uuid
from decimal import Decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "categories"},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("sku", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                ("image", models.CharField(blank=True, max_length=255)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("compare_at_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ("stock_quantity", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="ui.category")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("address_line_1", models.CharField(blank=True, max_length=255)),
                ("address_line_2", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("county", models.CharField(blank=True, max_length=100)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="customer_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(blank=True, max_length=40, null=True, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="carts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("customer_name", models.CharField(max_length=180)),
                ("customer_email", models.EmailField(max_length=254)),
                ("customer_phone", models.CharField(blank=True, max_length=32)),
                ("shipping_address_line_1", models.CharField(max_length=255)),
                ("shipping_address_line_2", models.CharField(blank=True, max_length=255)),
                ("shipping_city", models.CharField(max_length=100)),
                ("shipping_county", models.CharField(blank=True, max_length=100)),
                ("shipping_postal_code", models.CharField(blank=True, max_length=20)),
                ("currency", models.CharField(default="KES", editable=False, max_length=3)),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("shipping_fee", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("processing", "Processing"), ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("customer_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="store_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ui.cart")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cart_items", to="ui.product")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=180)),
                ("product_sku", models.CharField(blank=True, max_length=64)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ui.order")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_items", to="ui.product")),
            ],
            options={"ordering": ["pk"]},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["is_active", "category"], name="ui_prod_active_cat_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["is_featured", "is_active"], name="ui_prod_featured_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["status", "created_at"], name="ui_order_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["customer_email", "created_at"], name="ui_order_email_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=("cart", "product"), name="ui_cart_product_uniq"),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="ui_cart_qty_gte_1"),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="ui_order_item_qty_gte_1"),
        ),
    ]
