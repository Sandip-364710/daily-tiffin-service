from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .utils import TiffinRecommender, PriceOptimizer, DemandPredictor
from tiffins.models import TiffinService
from accounts.models import User

class TiffinRecommendationView(APIView):
    """API endpoint for getting tiffin recommendations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, format=None):
        recommender = TiffinRecommender()
        
        # Get recommendation type from query params (default: 'popular')
        rec_type = request.query_params.get('type', 'popular')
        limit = int(request.query_params.get('limit', 5))
        
        if rec_type == 'similar' and 'tiffin_id' in request.query_params:
            # Get similar tiffins based on content
            tiffin_id = request.query_params.get('tiffin_id')
            recommendations = recommender.get_content_based_recommendations(tiffin_id, limit)
        elif rec_type == 'user' and request.user.is_authenticated:
            # Get personalized recommendations for the user
            recommendations = recommender.get_user_based_recommendations(request.user.id, limit)
        else:
            # Get popular tiffins by default
            recommendations = recommender.get_popular_tiffins(limit)
        
        # Serialize the recommendations
        from tiffins.serializers import TiffinServiceSerializer
        serializer = TiffinServiceSerializer(recommendations, many=True)
        
        return Response({
            'status': 'success',
            'recommendations': serializer.data,
            'recommendation_type': rec_type,
            'timestamp': timezone.now()
        })

class PriceOptimizationView(APIView):
    """API endpoint for price optimization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, tiffin_id, format=None):
        # Only allow tiffin service providers to access this endpoint
        tiffin_service = get_object_or_404(TiffinService, id=tiffin_id, provider__user=request.user)
        
        optimizer = PriceOptimizer()
        current_price = float(tiffin_service.price)
        optimal_price = optimizer.calculate_optimal_price(tiffin_service)
        
        return Response({
            'status': 'success',
            'tiffin_service': tiffin_service.name,
            'current_price': current_price,
            'suggested_price': optimal_price,
            'price_difference': optimal_price - current_price,
            'price_change_percentage': ((optimal_price - current_price) / current_price) * 100,
            'recommendation': 'Increase price' if optimal_price > current_price else 'Decrease price' if optimal_price < current_price else 'Price is optimal',
            'timestamp': timezone.now()
        })

class DemandPredictionView(APIView):
    """API endpoint for demand prediction"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, tiffin_id, format=None):
        # Only allow tiffin service providers to access this endpoint
        tiffin_service = get_object_or_404(TiffinService, id=tiffin_id, provider__user=request.user)
        
        days = min(int(request.query_params.get('days', 7)), 30)  # Max 30 days
        
        predictor = DemandPredictor()
        predictions = predictor.predict_demand(tiffin_service, days)
        
        return Response({
            'status': 'success',
            'tiffin_service': tiffin_service.name,
            'predictions': predictions,
            'prediction_days': days,
            'timestamp': timezone.now()
        })

class CustomerSegmentationView(APIView):
    """API endpoint for customer segmentation"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, format=None):
        # Only allow tiffin service providers to access this endpoint
        if not hasattr(request.user, 'providerprofile'):
            return Response(
                {'error': 'Only tiffin service providers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the provider's tiffin services
        tiffin_services = TiffinService.objects.filter(provider=request.user.providerprofile)
        
        if not tiffin_services.exists():
            return Response(
                {'error': 'No tiffin services found for this provider'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Simple segmentation based on order frequency and average order value
        from orders.models import Order
        from django.db.models import Sum, Count, F, Value, CharField
        from django.db.models.functions import Concat
        
        # Get all customers who ordered from this provider
        customers = User.objects.filter(
            orders__items__tiffin_service__in=tiffin_services
        ).annotate(
            order_count=Count('orders', distinct=True),
            total_spent=Sum('orders__total_amount'),
            last_order_date=Max('orders__ordered_date'),
            segment=Case(
                When(order_count__gt=10, then=Value('loyal')),
                When(order_count__gt=5, then=Value('regular')),
                When(order_count__gt=0, then=Value('new')),
                default=Value('inactive'),
                output_field=CharField()
            )
        ).distinct()
        
        # Count customers in each segment
        segment_counts = customers.values('segment').annotate(
            count=Count('id'),
            avg_order_count=Avg('order_count'),
            avg_total_spent=Avg('total_spent')
        )
        
        # Prepare response
        response_data = {
            'status': 'success',
            'total_customers': customers.count(),
            'segments': {},
            'timestamp': timezone.now()
        }
        
        for segment in segment_counts:
            response_data['segments'][segment['segment']] = {
                'count': segment['count'],
                'avg_order_count': segment['avg_order_count'],
                'avg_total_spent': segment['avg_total_spent']
            }
        
        return Response(response_data)
