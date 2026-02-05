from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('provider/profile/create/', views.provider_profile_create, name='provider_profile_create'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
]
