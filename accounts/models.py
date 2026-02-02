import json
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

# Simple Point class for location handling
class Point:
    def __init__(self, x, y, srid=4326):
        self.x = x
        self.y = y
        self.srid = srid
    
    def __str__(self):
        return f'POINT({self.x} {self.y})'
    
    @property
    def json(self):
        return {'lng': self.x, 'lat': self.y}
    
    @classmethod
    def from_json(cls, data):
        if isinstance(data, str):
            data = json.loads(data)
        return cls(data['lng'], data['lat'])

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('provider', 'Provider'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer')
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.user_type})"

class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    business_name = models.CharField(max_length=200)
    description = models.TextField()
    delivery_areas = models.TextField(help_text="Comma separated areas where you deliver")
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    preparation_time = models.IntegerField(help_text="Average preparation time in minutes")
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=15)
    
    def __str__(self):
        return self.business_name


class DeliveryPerson(models.Model):
    """Model for delivery personnel who handle order deliveries"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_person')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='delivery_persons')
    phone_number = models.CharField(max_length=15)
    is_available = models.BooleanField(default=True)
    current_location = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Stores current location as {'lat': 0.0, 'lng': 0.0}"
    )
    vehicle_number = models.CharField(max_length=20, blank=True)
    vehicle_type = models.CharField(max_length=50, blank=True, help_text="e.g., Bike, Scooter, etc.")
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_deliveries = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Delivery People'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.provider.business_name})"
    
    def update_location(self, lat, lng):
        """Update the current location of the delivery person"""
        self.current_location = {'lat': float(lat), 'lng': float(lng)}
        self.save(update_fields=['current_location', 'updated_at'])
        return self.current_location
    
    def get_location_point(self):
        """Get the current location as a Point object"""
        if not self.current_location:
            return None
        # Use the local Point class from this module
        return Point(
            self.current_location['lng'],
            self.current_location['lat']
        )
