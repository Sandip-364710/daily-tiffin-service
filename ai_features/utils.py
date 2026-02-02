import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from django.db.models import Count, Avg
from tiffins.models import TiffinService, Review, Category
from accounts.models import User

class TiffinRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.scaler = MinMaxScaler()
    
    def get_popular_tiffins(self, limit=5):
        """Get most popular tiffins based on order count and ratings"""
        from orders.models import OrderItem
        
        popular_tiffins = TiffinService.objects.annotate(
            order_count=Count('order_items'),
            avg_rating=Avg('reviews__rating')
        ).filter(
            is_available=True,
            is_approved=True,
            order_count__gt=0
        ).order_by('-order_count', '-avg_rating')[:limit]
        
        return popular_tiffins
    
    def get_content_based_recommendations(self, tiffin_id, limit=5):
        """Get similar tiffins based on content (ingredients, description, etc.)"""
        try:
            target_tiffin = TiffinService.objects.get(id=tiffin_id)
        except TiffinService.DoesNotExist:
            return []
        
        # Get all available tiffins except the target one
        all_tiffins = TiffinService.objects.filter(
            is_available=True,
            is_approved=True
        ).exclude(id=tiffin_id)
        
        if not all_tiffins.exists():
            return []
        
        # Prepare text data for TF-IDF
        all_tiffins_list = list(all_tiffins) + [target_tiffin]
        text_data = [
            f"{t.name} {t.description} {t.ingredients} {t.meal_type} {t.spice_level}"
            for t in all_tiffins_list
        ]
        
        # Create TF-IDF matrix
        tfidf_matrix = self.vectorizer.fit_transform(text_data)
        
        # Calculate cosine similarity
        cosine_sim = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])
        
        # Get top similar tiffins
        sim_scores = list(enumerate(cosine_sim[0]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get the tiffin indices
        tiffin_indices = [i[0] for i in sim_scores[:limit]]
        
        return [all_tiffins[i] for i in tiffin_indices]
    
    def get_user_based_recommendations(self, user_id, limit=5):
        """Get tiffin recommendations based on user's order history and preferences"""
        from orders.models import Order, OrderItem
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return self.get_popular_tiffins(limit)
        
        # Get user's ordered tiffins
        ordered_tiffins = TiffinService.objects.filter(
            order_items__order__customer=user
        ).distinct()
        
        if not ordered_tiffins.exists():
            return self.get_popular_tiffins(limit)
        
        # Find similar users based on ordered tiffins
        similar_users = User.objects.filter(
            orders__items__tiffin_service__in=ordered_tiffins
        ).exclude(id=user_id).annotate(
            common_orders=Count('orders__items__tiffin_service', distinct=True)
        ).order_by('-common_orders')[:10]
        
        if not similar_users.exists():
            return self.get_popular_tiffins(limit)
        
        # Get tiffins ordered by similar users but not by current user
        recommended_tiffins = TiffinService.objects.filter(
            order_items__order__customer__in=similar_users,
            is_available=True,
            is_approved=True
        ).exclude(
            id__in=ordered_tiffins.values_list('id', flat=True)
        ).annotate(
            order_count=Count('order_items')
        ).order_by('-order_count')[:limit]
        
        return recommended_tiffins

class PriceOptimizer:
    @staticmethod
    def calculate_optimal_price(tiffin_service):
        """Calculate optimal price based on various factors"""
        # Base price from the tiffin service
        base_price = float(tiffin_service.price)
        
        # Get average price of similar tiffins in the same category and area
        similar_tiffins = TiffinService.objects.filter(
            category=tiffin_service.category,
            provider__city=tiffin_service.provider.city,
            is_available=True,
            is_approved=True
        ).exclude(id=tiffin_service.id)
        
        if similar_tiffins.exists():
            avg_similar_price = similar_tiffins.aggregate(avg_price=Avg('price'))['avg_price']
            # Weighted average of current price and market average
            optimal_price = (base_price * 0.6) + (float(avg_similar_price) * 0.4)
        else:
            optimal_price = base_price
        
        # Adjust based on ratings (higher ratings can charge more)
        avg_rating = tiffin_service.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 3.0
        rating_factor = 1 + ((avg_rating - 3) * 0.05)  # 5% increase per rating point above 3
        optimal_price *= rating_factor
        
        # Round to nearest 5 rupees
        optimal_price = round(optimal_price / 5) * 5
        
        return max(optimal_price, base_price * 0.8)  # Don't go below 80% of original price

class DemandPredictor:
    @staticmethod
    def predict_demand(tiffin_service, days=7):
        """Predict demand for the next 'days' days"""
        from orders.models import OrderItem
        from datetime import datetime, timedelta
        
        # Get historical order data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Last 30 days data
        
        daily_orders = OrderItem.objects.filter(
            tiffin_service=tiffin_service,
            order__ordered_date__range=(start_date, end_date)
        ).values('order__ordered_date__date').annotate(
            total_quantity=Count('id')
        ).order_by('order__ordered_date__date')
        
        if not daily_orders:
            # No historical data, return default prediction
            return [{
                'date': (datetime.now() + timedelta(days=i)).date(),
                'predicted_demand': 5  # Default prediction
            } for i in range(days)]
        
        # Simple moving average (you can replace with more sophisticated models)
        df = pd.DataFrame(list(daily_orders))
        df['moving_avg'] = df['total_quantity'].rolling(window=7, min_periods=1).mean()
        
        # Predict next 'days' days
        last_avg = df['moving_avg'].iloc[-1]
        predictions = []
        
        for i in range(1, days + 1):
            date = (end_date + timedelta(days=i)).date()
            # Simple adjustment for weekends (you can add more sophisticated logic)
            if date.weekday() >= 5:  # Saturday or Sunday
                prediction = last_avg * 1.2  # 20% higher on weekends
            else:
                prediction = last_avg
                
            predictions.append({
                'date': date,
                'predicted_demand': round(prediction)
            })
            
        return predictions
