from django.db import models
from django.utils import timezone
from accounts.models import User, ProviderProfile, DeliveryPerson
from tiffins.models import TiffinService
import uuid


class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders'
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name='received_orders'
    )

    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default='pending'
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending'
    )

    # Delivery details
    delivery_address = models.TextField()
    delivery_phone = models.CharField(max_length=17)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()

    delivery_person = models.ForeignKey(
        DeliveryPerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )

    # ✅ Location stored as lat/lng JSON
    delivery_location = models.JSONField(
        null=True,
        blank=True,
        help_text="Stores location as {'lat': 0.0, 'lng': 0.0}"
    )

    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Additional info
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer.username}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    tiffin_service = models.ForeignKey(TiffinService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.tiffin_service.name}"

    @property
    def total_price(self):
        return self.quantity * self.price


class OrderReview(models.Model):
    """Model for customers to rate and review their order experience"""
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='review'
    )
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)
    
    # Rating fields (1-5 stars)
    food_quality_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    delivery_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    overall_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    
    # Review text
    comment = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('order', 'customer')
    
    def __str__(self):
        return f"Review for Order #{self.order.order_number} - {self.overall_rating} stars"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update provider's average rating
        self.update_provider_rating()
    
    def update_provider_rating(self):
        """Update provider's average rating based on all reviews"""
        reviews = OrderReview.objects.filter(provider=self.provider)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('overall_rating'))['overall_rating__avg']
            self.provider.rating = round(avg_rating, 2)
            self.provider.save(update_fields=['rating'])


class SavedCart(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='saved_cart'
    )
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SavedCart for {self.user.username}"


class DeliveryTracking(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='tracking'
    )
    status = models.CharField(
        max_length=20,
        choices=Order.ORDER_STATUS_CHOICES,
        default='pending'
    )
    delivery_person = models.ForeignKey(
        DeliveryPerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # ✅ Current location as JSON
    current_location = models.JSONField(
        null=True,
        blank=True,
        help_text="Stores location as {'lat': 0.0, 'lng': 0.0}"
    )

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Delivery Tracking'

    def __str__(self):
        return f"Tracking for Order #{self.order.order_number}"

    def update_location(self, lat, lng):
        self.current_location = {'lat': lat, 'lng': lng}
        self.last_updated = timezone.now()
        self.save(update_fields=['current_location', 'last_updated'])
        self.calculate_eta()

    def calculate_eta(self):
        if not self.current_location or not self.order.delivery_location:
            return None

        # Dummy ETA logic (can be replaced with Google Maps API later)
        self.order.eta = timezone.now() + timezone.timedelta(minutes=15)
        self.order.save(update_fields=['eta'])
        return self.order.eta
