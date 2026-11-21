from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ecommerce.admin'
    label = 'ecommerce_admin'

    def ready(self):
        import ecommerce.admin.signals  # noqa: F401
