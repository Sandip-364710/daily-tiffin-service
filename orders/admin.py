from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'provider', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'delivery_date')
    search_fields = ('order_number', 'customer__username', 'provider__business_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'customer', 'provider', 'status', 'payment_status')
        }),
        ('Delivery Details', {
            'fields': ('delivery_address', 'delivery_phone', 'delivery_date', 'delivery_time')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'delivery_charge', 'total_amount')
        }),
        ('Additional Info', {
            'fields': ('special_instructions', 'created_at', 'updated_at')
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'tiffin_service', 'quantity', 'price', 'total_price')
    list_filter = ('order__status', 'order__created_at')
