import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")

_application = get_wsgi_application()


def handler(event, context):
    return _application(event, context)
