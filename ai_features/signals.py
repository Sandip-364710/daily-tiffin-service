from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from tiffins.models import Review, TiffinService
from orders.models import Order
from .utils import TiffinRecommender

@receiver(post_save, sender=Review)
def update_tiffin_rating(sender, instance, created, **kwargs):
    """Update tiffin service rating when a new review is added or updated"""
    if created or 'rating' in instance.get_dirty_fields():
        tiffin_service = instance.tiffin_service
        # Update the average rating
        tiffin_service.update_average_rating()

@receiver(post_save, sender=Order)
@receiver(post_delete, sender=Order)
def update_recommendations_on_order_change(sender, instance, **kwargs):
    """Update recommendations when an order is created, updated, or deleted"""
    # In a real-world scenario, you might want to update recommendation models here
    # For now, we'll just clear the recommendation cache for the user
    if hasattr(instance, 'customer'):
        # Clear any cached recommendations for this user
        # This is a placeholder - in a real app, you'd invalidate the relevant cache
        pass

@receiver(post_save, sender=TiffinService)
@receiver(post_delete, sender=TiffinService)
def update_tiffin_recommendations(sender, instance, **kwargs):
    """Update recommendations when a tiffin service is created, updated, or deleted"""
    # In a real-world scenario, you might want to update recommendation models here
    # This is a placeholder for the actual implementation
    pass
