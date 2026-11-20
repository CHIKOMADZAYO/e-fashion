from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('admin/', include('ecommerce.admin.urls')),
    path('account/', include('ecommerce.accounts.urls')),
    path('',include('ecommerce.ui.urls')),
    path('payments/',include('ecommerce.payments.urls')),


]
