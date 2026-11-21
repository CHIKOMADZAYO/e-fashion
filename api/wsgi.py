import os

from django.core.wsgi import get_wsgi_application
from vercel_wsgi import DjangoWSGIHandler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")

application = get_wsgi_application()

handler = DjangoWSGIHandler(application)
