from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    # Delivery dashboard
    path('', views.delivery_dashboard, name='dashboard'),
    
    # API endpoints
    path('api/update-location/<int:order_id>/', views.update_location, name='update_location'),
    
    # Order management
    path('orders/<int:order_id>/', views.order_details, name='order_details'),
    path('orders/<int:order_id>/complete/', views.complete_delivery, name='complete_delivery'),
    path('orders/<int:order_id>/cancel/', views.cancel_delivery, name='cancel_delivery'),
    
    # Delivery person profile
    path('profile/', views.delivery_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    
    # Earnings and statistics
    path('earnings/', views.earnings, name='earnings'),
    path('statistics/', views.delivery_statistics, name='statistics'),
]
