from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.gis.geos import Point
from orders.models import Order, DeliveryTracking

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_location(request, order_id):
    """
    API endpoint for delivery app to update location
    Expected POST data: {"lat": 22.1234, "lng": 73.4567}
    """
    if not hasattr(request.user, 'delivery_person'):
        return JsonResponse(
            {'error': 'Only delivery personnel can update location'}, 
            status=403
        )
    
    try:
        lat = float(request.POST.get('lat'))
        lng = float(request.POST.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse(
            {'error': 'Invalid coordinates'}, 
            status=400
        )
    
    # Get the order assigned to this delivery person
    try:
        order = Order.objects.get(
            id=order_id, 
            delivery_person=request.user.delivery_person,
            status__in=['ready', 'out_for_delivery']
        )
    except Order.DoesNotExist:
        return JsonResponse(
            {'error': 'Order not found or not assigned to you'}, 
            status=404
        )
    
    # Update or create delivery tracking
    tracking, created = DeliveryTracking.objects.get_or_create(order=order)
    tracking.update_location(lat, lng)
    
    # If this is the first location update, mark the order as out for delivery
    if order.status == 'ready':
        order.status = 'out_for_delivery'
        order.save(update_fields=['status'])
    
    return JsonResponse({
        'status': 'success',
        'order_status': order.get_status_display(),
        'location_updated': tracking.last_location_update.isoformat()
    })

@login_required
def delivery_dashboard(request):
    """Dashboard for delivery personnel to see their assigned orders"""
    if not hasattr(request.user, 'delivery_person'):
        return JsonResponse(
            {'error': 'Only delivery personnel can access this page'}, 
            status=403
        )
    
    # Get active deliveries
    active_deliveries = Order.objects.filter(
        delivery_person=request.user.delivery_person,
        status__in=['ready', 'out_for_delivery']
    ).select_related('customer', 'tiffin_service')
    
    # Get recent completed deliveries
    recent_deliveries = Order.objects.filter(
        delivery_person=request.user.delivery_person,
        status='delivered'
    ).order_by('-delivered_at')[:10]
    
    context = {
        'active_deliveries': active_deliveries,
        'recent_deliveries': recent_deliveries,
        'google_maps_api_key': 'YOUR_GOOGLE_MAPS_API_KEY',  # Replace with your actual API key
    }
    
    return render(request, 'delivery/dashboard.html', context)
