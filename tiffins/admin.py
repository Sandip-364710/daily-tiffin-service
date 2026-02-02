from django.contrib import admin
from .models import Category, TiffinService, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(TiffinService)
class TiffinServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'meal_type', 'price', 'is_available', 'is_vegetarian', 'is_approved')
    list_filter = ('meal_type', 'is_available', 'is_vegetarian', 'is_approved', 'spice_level', 'category')
    search_fields = ('name', 'provider__business_name')
    list_editable = ('is_available',)
    actions = ['approve_selected']

    def approve_selected(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"Approved {updated} tiffin(s).")
    approve_selected.short_description = "Approve selected tiffins"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('tiffin_service', 'customer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('tiffin_service__name', 'customer__username')
