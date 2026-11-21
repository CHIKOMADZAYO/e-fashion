from django.urls import path
from . import views

urlpatterns = [
    path("stk-push/", views.start_stk_push_view, name="mpesa_stk_push"),
    path("status/<uuid:reference>/", views.payment_status, name="payment_status"),
    path("callback/stk/", views.stk_callback, name="mpesa_stk_callback"),
]
