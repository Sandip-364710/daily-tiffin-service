from django.urls import path
from . import views

urlpatterns = [
    # Cart and checkout
    path('add-to-cart/<int:tiffin_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/<int:tiffin_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:tiffin_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Order management
    path('history/', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    # Delivery tracking
    path('track/<int:order_id>/', views.track_delivery, name='track_delivery'),
    path('api/update-location/<int:order_id>/', views.update_delivery_location, name='update_delivery_location'),
]
