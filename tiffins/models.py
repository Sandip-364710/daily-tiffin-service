from django.db import models
from accounts.models import User, ProviderProfile

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class TiffinService(models.Model):
    MEAL_TYPE_CHOICES = (
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snacks', 'Snacks'),
    )
    
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='tiffin_services')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='tiffins/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_vegetarian = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False, help_text="Visible to customers only after admin approval")
    spice_level = models.CharField(max_length=20, choices=[
        ('mild', 'Mild'),
        ('medium', 'Medium'),
        ('spicy', 'Spicy'),
    ], default='medium')
    ingredients = models.TextField(help_text="List main ingredients")
    preparation_time = models.IntegerField(help_text="Time in minutes")
    serves = models.IntegerField(default=1, help_text="Number of people this serves")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.provider.business_name}"

class Review(models.Model):
    tiffin_service = models.ForeignKey(TiffinService, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('tiffin_service', 'customer')
    
    def __str__(self):
        return f"{self.rating} stars - {self.tiffin_service.name}"
