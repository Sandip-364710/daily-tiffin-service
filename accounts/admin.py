from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ProviderProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_verified', 'is_active')
    list_filter = ('user_type', 'is_verified', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'address', 'city', 'state', 'pincode', 'profile_picture', 'is_verified')
        }),
    )

@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'is_active', 'rating', 'total_orders')
    list_filter = ('is_active', 'user__city')
    search_fields = ('business_name', 'user__username')

admin.site.register(User, CustomUserAdmin)
