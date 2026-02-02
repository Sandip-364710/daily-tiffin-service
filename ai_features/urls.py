from django.urls import path
from . import views

app_name = 'ai_features'

urlpatterns = [
    # Tiffin recommendations
    path('recommendations/', views.TiffinRecommendationView.as_view(), name='tiffin_recommendations'),
    
    # Price optimization
    path('price-optimization/<int:tiffin_id>/', views.PriceOptimizationView.as_view(), name='price_optimization'),
    
    # Demand prediction
    path('demand-prediction/<int:tiffin_id>/', views.DemandPredictionView.as_view(), name='demand_prediction'),
    
    # Customer segmentation
    path('customer-segmentation/', views.CustomerSegmentationView.as_view(), name='customer_segmentation'),
]
