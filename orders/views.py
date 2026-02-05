from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from .models import Order, OrderItem, OrderReview
from tiffins.models import TiffinService
from .forms import OrderForm
from decimal import Decimal
import json
from accounts.models import ProviderProfile
# Simple distance calculation (in kilometers) using Haversine formula
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    return c * r
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

def _persist_cart(request):
    """Persist current session cart to SavedCart for authenticated customers."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return
    if getattr(request.user, 'user_type', None) != 'customer':
        return
    try:
        from .models import SavedCart
        saved, _ = SavedCart.objects.get_or_create(user=request.user)
        saved.data = request.session.get('cart', {}) or {}
        saved.save()
    except Exception:
        # Do not block request on persistence errors
        pass
@login_required
def add_to_cart(request, tiffin_id):
    if request.user.user_type != 'customer':
        return JsonResponse({'error': 'Only customers can add items to cart'}, status=403)
    
    tiffin = get_object_or_404(TiffinService, id=tiffin_id, is_available=True)
    
    # Get or create cart in session
    cart = request.session.get('cart', {})
    
    if str(tiffin_id) in cart:
        cart[str(tiffin_id)]['quantity'] += 1
    else:
        cart[str(tiffin_id)] = {
            'name': tiffin.name,
            'price': str(tiffin.price),  # store as string for JSON serialization
            'quantity': 1,
            'provider_id': tiffin.provider.id,
            'provider_name': tiffin.provider.business_name
        }
    
    request.session['cart'] = cart
    request.session.modified = True
    _persist_cart(request)
    
    # Calculate total quantity across the cart for badge
    total_qty = sum(item.get('quantity', 0) for item in cart.values())
    return JsonResponse({'success': True, 'cart_count': total_qty})

@login_required
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = Decimal('0.00')
    
    for tiffin_id, item in cart.items():
        price_dec = Decimal(item['price'])
        qty = int(item['quantity'])
        item_total = price_dec * qty
        cart_items.append({
            'id': tiffin_id,
            'name': item['name'],
            'price': float(price_dec),
            'quantity': qty,
            'total': float(item_total),
            'provider_name': item['provider_name']
        })
        total += item_total
    # Estimate delivery charges as sum of unique providers' delivery_charge
    provider_ids = {int(item['provider_id']) for item in cart.values()}
    delivery_charge = Decimal('0.00')
    if provider_ids:
        for pid in provider_ids:
            try:
                delivery_charge += ProviderProfile.objects.get(id=pid).delivery_charge
            except ProviderProfile.DoesNotExist:
                pass
    grand_total = total + delivery_charge
    
    return render(request, 'orders/cart.html', {
        'cart_items': cart_items,
        'subtotal': float(total),
        'delivery_charge': float(delivery_charge),
        'grand_total': float(grand_total),
    })

@login_required
@require_POST
def update_cart_item(request, tiffin_id):
    if request.user.user_type != 'customer':
        return JsonResponse({'error': 'Only customers can update cart'}, status=403)
    cart = request.session.get('cart', {})
    key = str(tiffin_id)
    if key not in cart:
        return JsonResponse({'error': 'Item not in cart'}, status=404)
    try:
        change = int(request.POST.get('change', '0'))
    except ValueError:
        change = 0
    # Update quantity
    current_qty = int(cart[key].get('quantity', 1))
    new_qty = current_qty + change
    removed = False
    if new_qty <= 0:
        cart.pop(key)
        removed = True
    else:
        cart[key]['quantity'] = new_qty
    request.session['cart'] = cart
    request.session.modified = True
    # Recalculate totals
    _persist_cart(request)
    cart_total = Decimal('0.00')
    total_qty = 0
    item_total = Decimal('0.00')
    quantity = 0
    if not removed:
        price_dec = Decimal(cart[key]['price'])
        quantity = int(cart[key]['quantity'])
        item_total = price_dec * quantity
    for it in cart.values():
        cart_total += Decimal(it['price']) * int(it['quantity'])
        total_qty += int(it['quantity'])
    # Provisional delivery equals sum of unique providers' charges
    provider_ids = {int(it['provider_id']) for it in cart.values()}
    delivery_charge = Decimal('0.00')
    if provider_ids:
        for pid in provider_ids:
            try:
                delivery_charge += ProviderProfile.objects.get(id=pid).delivery_charge
            except ProviderProfile.DoesNotExist:
                pass
    cart_grand_total = cart_total + delivery_charge
    return JsonResponse({
        'success': True,
        'removed': removed,
        'quantity': quantity,
        'item_total': float(item_total),
        'cart_subtotal': float(cart_total),
        'cart_delivery': float(delivery_charge),
        'cart_grand_total': float(cart_grand_total),
        'cart_count': total_qty,
    })

@login_required
@require_POST
def remove_cart_item(request, tiffin_id):
    if request.user.user_type != 'customer':
        return JsonResponse({'error': 'Only customers can update cart'}, status=403)
    cart = request.session.get('cart', {})
    key = str(tiffin_id)
    cart.pop(key, None)
    request.session['cart'] = cart
    request.session.modified = True
    _persist_cart(request)
    # Recalculate totals and count
    cart_total = Decimal('0.00')
    total_qty = 0
    for it in cart.values():
        cart_total += Decimal(it['price']) * int(it['quantity'])
        total_qty += int(it['quantity'])
    provider_ids = {int(it['provider_id']) for it in cart.values()}
    delivery_charge = Decimal('0.00')
    if provider_ids:
        for pid in provider_ids:
            try:
                delivery_charge += ProviderProfile.objects.get(id=pid).delivery_charge
            except ProviderProfile.DoesNotExist:
                pass
    cart_grand_total = cart_total + delivery_charge
    return JsonResponse({
        'success': True,
        'cart_subtotal': float(cart_total),
        'cart_delivery': float(delivery_charge),
        'cart_grand_total': float(cart_grand_total),
        'cart_count': total_qty,
    })

@login_required
def checkout(request):
    if request.user.user_type != 'customer':
        messages.error(request, 'Only customers can place orders.')
        return redirect('home')
    
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('tiffin_list')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Group items by provider
            providers = {}
            for tiffin_id, item in cart.items():
                provider_id = item['provider_id']
                if provider_id not in providers:
                    providers[provider_id] = []
                providers[provider_id].append((tiffin_id, item))
            
            # Create separate orders for each provider
            orders_created = []
            for provider_id, items in providers.items():
                provider = ProviderProfile.objects.get(id=provider_id)
                
                # Calculate totals using Decimal
                subtotal = sum(Decimal(item['price']) * int(item['quantity']) for _, item in items)
                delivery_charge = provider.delivery_charge  # already Decimal
                total_amount = subtotal + delivery_charge
                
                # Create order
                order = Order.objects.create(
                    customer=request.user,
                    provider=provider,
                    delivery_address=form.cleaned_data['delivery_address'],
                    delivery_phone=form.cleaned_data['delivery_phone'],
                    delivery_date=form.cleaned_data['delivery_date'],
                    delivery_time=form.cleaned_data['delivery_time'],
                    subtotal=subtotal,
                    delivery_charge=delivery_charge,
                    total_amount=total_amount,
                    special_instructions=form.cleaned_data['special_instructions']
                )
                
                # Create order items
                for tiffin_id, item in items:
                    tiffin = TiffinService.objects.get(id=tiffin_id)
                    OrderItem.objects.create(
                        order=order,
                        tiffin_service=tiffin,
                        quantity=int(item['quantity']),
                        price=Decimal(item['price'])
                    )
                
                orders_created.append(order)
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            # Clear saved cart as well
            try:
                from .models import SavedCart
                SavedCart.objects.filter(user=request.user).update(data={})
            except Exception:
                pass
            
            messages.success(request, f'{len(orders_created)} order(s) placed successfully!')
            return redirect('order_history')
    else:
        form = OrderForm()
    
    # Calculate cart totals
    cart_items = []
    total = Decimal('0.00')
    for tiffin_id, item in cart.items():
        price_dec = Decimal(item['price'])
        qty = int(item['quantity'])
        item_total = price_dec * qty
        cart_items.append({
            'name': item['name'],
            'price': float(price_dec),
            'quantity': qty,
            'total': float(item_total),
            'provider_name': item['provider_name']
        })
        total += item_total
    # Provisional delivery charges (sum of unique providers)
    provider_ids = {int(item['provider_id']) for item in cart.values()}
    delivery_charge = Decimal('0.00')
    if provider_ids:
        for pid in provider_ids:
            try:
                delivery_charge += ProviderProfile.objects.get(id=pid).delivery_charge
            except ProviderProfile.DoesNotExist:
                pass
    grand_total = total + delivery_charge
    
    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': float(total),
        'delivery_charge': float(delivery_charge),
        'grand_total': float(grand_total),
    })

@login_required
def order_history(request):
    if request.user.user_type == 'customer':
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    else:
        try:
            orders = Order.objects.filter(provider=request.user.provider_profile).order_by('-created_at')
        except:
            orders = Order.objects.none()
    
    return render(request, 'orders/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    if request.user.user_type == 'customer':
        order = get_object_or_404(Order, id=order_id, customer=request.user)
    else:
        try:
            order = get_object_or_404(Order, id=order_id, provider=request.user.provider_profile)
        except:
            messages.error(request, 'Order not found.')
            return redirect('order_history')
    
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'order_items': order.items.all(),
        'can_cancel': order.status in ['pending', 'confirmed', 'preparing']
    })

@login_required
def track_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Check if the user has permission to view this order
    if request.user != order.customer and (hasattr(request.user, 'provider_profile') and request.user.provider_profile != order.provider):
        return HttpResponseForbidden("You don't have permission to view this order.")
    
    # Get or create delivery tracking info
    from .models import DeliveryTracking
    tracking, created = DeliveryTracking.objects.get_or_create(
        order=order,
        defaults={'delivery_person': order.delivery_person}
    )
    
    # Get location data
    delivery_location = None
    if tracking.current_location:
        delivery_location = {
            'lat': tracking.current_location.get('lat'),
            'lng': tracking.current_location.get('lng')
        }
    
    # If this is an AJAX request for live location update
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'delivery_person_location': delivery_location,
            'status': tracking.status,
            'eta': tracking.order.eta.isoformat() if tracking.order.eta else None,
            'last_updated': tracking.last_updated.isoformat(),
        })
    
    # For regular page load, render the tracking template
    context = {
        'order': order,
        'tracking': tracking,
        'delivery_location': delivery_location,
        'restaurant_location': {
            'lat': order.provider.latitude if hasattr(order.provider, 'latitude') else 0,
            'lng': order.provider.longitude if hasattr(order.provider, 'longitude') else 0,
        },
        'customer_location': order.get_delivery_point().json if order.get_delivery_point() else None,
    }
    
    return render(request, 'orders/track_delivery.html', context)
    
    # For regular page load
    context = {
        'order': order,
        'google_maps_api_key': 'YOUR_GOOGLE_MAPS_API_KEY',  # Replace with your actual API key
        'restaurant_location': {
            'lat': order.tiffin_service.location.y if order.tiffin_service.location else 22.3072,  # Default to Vadodara
            'lng': order.tiffin_service.location.x if order.tiffin_service.location else 73.1812,
        },
        'delivery_address': order.delivery_address,
        'delivery_person': tracking.delivery_person,
        'status': tracking.status,
    }
    
    return render(request, 'orders/track_delivery.html', context)

@login_required
@require_POST
def update_delivery_location(request, order_id):
    if not hasattr(request.user, 'delivery_person'):
        return JsonResponse({'error': 'Only delivery personnel can update location'}, status=403)
    
    try:
        lat = float(request.POST.get('lat'))
        lng = float(request.POST.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    
    # Update the delivery person's location
    delivery_person = request.user.delivery_person
    delivery_person.update_location(lat, lng)
    
    # Get the order and update tracking
    order = get_object_or_404(Order, id=order_id, delivery_person=delivery_person)
    
    # Update or create delivery tracking
    from .models import DeliveryTracking
    tracking, created = DeliveryTracking.objects.get_or_create(
        order=order,
        defaults={'delivery_person': delivery_person}
    )
    
    # Update the tracking with current location
    tracking.update_location(lat, lng)
    
    return JsonResponse({
        'status': 'success',
        'location': {'lat': lat, 'lng': lng},
        'updated_at': tracking.last_updated.isoformat()
    })

@login_required
@require_POST
def update_order_status(request, order_id):
    if request.user.user_type != 'provider':
        return JsonResponse({'error': 'Only providers can update order status'}, status=403)
    
    try:
        order = get_object_or_404(Order, id=order_id, provider=request.user.provider_profile)
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.status = new_status
            order.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found or you do not have permission to update it'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

@login_required
@require_POST
def submit_review(request, order_id):
    """Handle review submission for delivered orders"""
    if request.user.user_type != 'customer':
        return JsonResponse({'error': 'Only customers can submit reviews'}, status=403)
    
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Check if order is delivered
    if order.status != 'delivered':
        return JsonResponse({'error': 'You can only review delivered orders'}, status=400)
    
    # Check if review already exists
    if OrderReview.objects.filter(order=order).exists():
        return JsonResponse({'error': 'You have already reviewed this order'}, status=400)
    
    try:
        # Get rating data
        food_quality_rating = int(request.POST.get('food_quality_rating'))
        delivery_rating = int(request.POST.get('delivery_rating'))
        overall_rating = int(request.POST.get('overall_rating'))
        comment = request.POST.get('comment', '').strip()
        
        # Validate ratings
        for rating in [food_quality_rating, delivery_rating, overall_rating]:
            if not 1 <= rating <= 5:
                return JsonResponse({'error': 'Ratings must be between 1 and 5'}, status=400)
        
        # Create review
        review = OrderReview.objects.create(
            order=order,
            customer=request.user,
            provider=order.provider,
            food_quality_rating=food_quality_rating,
            delivery_rating=delivery_rating,
            overall_rating=overall_rating,
            comment=comment
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your review!',
            'review': {
                'overall_rating': review.overall_rating,
                'comment': review.comment
            }
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': 'Invalid rating values'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
