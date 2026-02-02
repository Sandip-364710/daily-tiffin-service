from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tiffins/', views.tiffin_list, name='tiffin_list'),
    path('tiffin/<int:pk>/', views.tiffin_detail, name='tiffin_detail'),
    path('tiffin/<int:pk>/review/', views.add_review, name='add_review'),
    path('provider/tiffins/', views.provider_tiffins, name='provider_tiffins'),
    path('provider/tiffin/add/', views.add_tiffin, name='add_tiffin'),
    path('provider/tiffin/<int:pk>/edit/', views.edit_tiffin, name='edit_tiffin'),
    path('provider/tiffin/<int:pk>/toggle/', views.toggle_availability, name='toggle_tiffin'),
    path('provider/reviews/', views.provider_reviews, name='provider_reviews'),
    path('chatbot/', views.chatbot, name='chatbot'),
]
