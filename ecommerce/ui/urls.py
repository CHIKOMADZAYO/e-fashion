from django.urls  import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/store-state/', views.store_state, name='store_state'),
    path('api/cart/add/', views.cart_add, name='cart_add'),
    path('api/cart/update/', views.cart_update, name='cart_update'),
    path('api/cart/remove/', views.cart_remove, name='cart_remove'),
    path('api/cart/clear/', views.cart_clear, name='cart_clear'),
    path('api/wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    path('api/checkout/', views.checkout_submit, name='checkout_submit'),
    path('track-order/', views.track_order, name='track_order'),
    path('support-chat/', views.support_chat, name='support_chat'),
    path('<slug:page>/', views.store_page, name='store_page'),
]

