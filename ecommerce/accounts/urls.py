from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("register/", views.register, name="account_register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
        ),
        name="account_login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="account_logout",
    ),
    path("", views.profile, name="account_profile"),
    path("orders/", views.order_history, name="account_orders"),
    path("orders/<uuid:order_number>/", views.order_detail, name="account_order_detail"),
    path("addresses/", views.addresses, name="account_addresses"),
    path("addresses/<int:pk>/default/", views.set_default_address, name="account_address_default"),
    path("addresses/<int:pk>/delete/", views.delete_address, name="account_address_delete"),
]
