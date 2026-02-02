from rest_framework import serializers
from .models import TiffinService, Review, Category
from accounts.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image', 'is_active']

class ReviewSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'customer', 'rating', 'comment', 'created_at']
        read_only_fields = ['created_at']

class TiffinServiceSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    provider = serializers.StringRelatedField()
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TiffinService
        fields = [
            'id', 'name', 'description', 'category', 'provider', 'meal_type',
            'price', 'image', 'is_available', 'is_vegetarian', 'spice_level',
            'ingredients', 'preparation_time', 'serves', 'created_at', 'updated_at',
            'reviews', 'average_rating', 'review_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'average_rating', 'review_count']
    
    def get_average_rating(self, obj):
        return obj.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    def get_review_count(self, obj):
        return obj.reviews.count()

class TiffinServiceDetailSerializer(TiffinServiceSerializer):
    # Include additional details for the detail view
    class Meta(TiffinServiceSerializer.Meta):
        fields = TiffinServiceSerializer.Meta.fields + ['is_approved', 'order_count']
        
    def get_order_count(self, obj):
        return obj.order_items.count()
