from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.db.models import Avg, Sum, Count, Q
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import User, ProviderProfile
from .forms import UserRegistrationForm, ProviderProfileForm
from tiffins.models import Review, TiffinService
from orders.models import Order

class SignUpView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/signup.html'
    
    def form_valid(self, form):
        user = form.save()
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'Account created for {username}!')
        return redirect('login')
    
    def form_invalid(self, form):
        # Add error messages to show on signup page
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.title()}: {error}')
        return self.render_to_response(self.get_context_data(form=form))

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        # Add error messages to show on signup page
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.title()}: {error}')
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        next_url = self.get_redirect_url()
        user = getattr(self.request, 'user', None)
        if next_url and '/admin' in next_url:
            if not (user and user.is_staff):
                messages.error(self.request, 'You do not have admin access. Redirected to dashboard.')
                return reverse_lazy('dashboard')
        return next_url or reverse_lazy('dashboard')

@login_required
def dashboard(request):
    if request.user.user_type == 'provider':
        try:
            provider_profile = request.user.provider_profile
        except ProviderProfile.DoesNotExist:
            provider_profile = None
        
        # Get basic stats
        avg_rating = None
        total_orders = 0
        pending_tiffins_count = 0
        
        if provider_profile:
            avg_rating = Review.objects.filter(tiffin_service__provider=provider_profile).aggregate(Avg('rating'))['rating__avg']
            total_orders = Order.objects.filter(provider=provider_profile).count()
            try:
                pending_tiffins_count = provider_profile.tiffin_services.filter(is_approved=False).count()
            except Exception:
                pending_tiffins_count = 0
        
        # Get recent orders (last 5)
        recent_orders = Order.objects.filter(
            provider=provider_profile
        ).exclude(
            status='delivered'
        ).order_by('-created_at')[:5] if provider_profile else []
        
        # Calculate total earnings
        total_earnings = Order.objects.filter(
            provider=provider_profile,
            status='delivered'
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0 if provider_profile else 0
        
        # Get top performing tiffins with revenue
        today = timezone.now().date()
        top_tiffins = []
        if provider_profile:
            top_tiffins_data = TiffinService.objects.filter(
                provider=provider_profile,
                is_approved=True
            ).annotate(
                order_count=Count('orderitem', filter=Q(orderitem__order__created_at__date=today)),
                total_revenue=Sum('orderitem__order__total_amount', filter=Q(orderitem__order__created_at__date=today))
            ).filter(
                order_count__gt=0
            ).order_by('-total_revenue')[:3]
            
            for tiffin in top_tiffins_data:
                top_tiffins.append({
                    'name': tiffin.name,
                    'order_count': tiffin.order_count or 0,
                    'total_revenue': tiffin.total_revenue or 0
                })
        
        # Get provider's tiffins
        provider_tiffins = TiffinService.objects.filter(
            provider=provider_profile,
            is_approved=True
        ).order_by('-created_at')[:4] if provider_profile else []
        
        # Get recent reviews
        recent_reviews = Review.objects.filter(
            tiffin_service__provider=provider_profile
        ).order_by('-created_at')[:3] if provider_profile else []
        
        return render(request, 'accounts/provider_dashboard.html', {
            'provider_profile': provider_profile,
            'avg_rating': avg_rating,
            'total_orders': total_orders,
            'pending_tiffins_count': pending_tiffins_count,
            'recent_orders': recent_orders,
            'total_earnings': total_earnings,
            'top_tiffins': top_tiffins,
            'provider_tiffins': provider_tiffins,
            'recent_reviews': recent_reviews,
        })
    else:
        # Customer dashboard data
        # Get current active order
        current_order = Order.objects.filter(
            customer=request.user
        ).exclude(
            status__in=['delivered', 'cancelled']
        ).order_by('-created_at').first()
        
        # Get next delivery
        next_delivery = Order.objects.filter(
            customer=request.user,
            delivery_date__gte=timezone.now().date()
        ).order_by('delivery_date', 'delivery_time').first()
        
        # Get recent orders (last 5)
        recent_orders = Order.objects.filter(
            customer=request.user
        ).order_by('-created_at')[:5]
        
        # Calculate usage statistics
        total_orders = Order.objects.filter(customer=request.user).count()
        total_spent = Order.objects.filter(
            customer=request.user,
            status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Monthly orders
        current_month = timezone.now().replace(day=1)
        monthly_orders = Order.objects.filter(
            customer=request.user,
            created_at__gte=current_month
        ).count()
        
        # Generate usage chart data (simplified)
        usage_chart = [20, 34, 26, 50, 42, 62, 48, 18, 28, 40, 55, 70]
        weekly_usage_chart = [20, 34, 26, 50, 42, 62, 48]
        
        # Get popular tiffins
        popular_tiffins = TiffinService.objects.filter(
            is_approved=True,
            is_available=True
        ).order_by('-created_at')[:3]
        
        # Get favorite vendors (providers with most orders from this customer)
        favorite_vendors = []
        vendor_data = Order.objects.filter(
            customer=request.user
        ).values('provider_id').annotate(
            order_count=Count('id')
        ).order_by('-order_count')[:3]
        
        for vendor in vendor_data:
            try:
                provider = ProviderProfile.objects.get(id=vendor['provider_id'])
                avg_rating = Review.objects.filter(
                    tiffin_service__provider=provider
                ).aggregate(avg=Avg('rating'))['avg'] or 0
                
                favorite_vendors.append({
                    'business_name': provider.business_name,
                    'description': provider.description,
                    'avg_rating': avg_rating
                })
            except ProviderProfile.DoesNotExist:
                continue
        
        return render(request, 'accounts/customer_dashboard.html', {
            'current_order': current_order,
            'next_delivery': next_delivery,
            'recent_orders': recent_orders,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'monthly_orders': monthly_orders,
            'usage_chart': usage_chart,
            'weekly_usage_chart': weekly_usage_chart,
            'popular_tiffins': popular_tiffins,
            'favorite_vendors': favorite_vendors,
        })

@login_required
def provider_profile_create(request):
    if request.user.user_type != 'provider':
        messages.error(request, 'Only providers can create business profiles.')
        return redirect('dashboard')
    
    try:
        provider_profile = request.user.provider_profile
        is_edit = True
    except ProviderProfile.DoesNotExist:
        provider_profile = None
        is_edit = False
    
    if request.method == 'POST':
        form = ProviderProfileForm(request.POST, instance=provider_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            if is_edit:
                messages.success(request, 'Business profile updated successfully!')
            else:
                messages.success(request, 'Business profile created successfully!')
            return redirect('dashboard')
    else:
        form = ProviderProfileForm(instance=provider_profile)
    
    return render(request, 'accounts/provider_profile_form.html', {
        'form': form,
        'is_edit': is_edit
    })

@login_required
@require_POST
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    try:
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user is a provider
        if request.user.user_type != 'provider':
            return JsonResponse({
                'success': False,
                'error': 'Only providers can update order status'
            })
        
        # Check if the user has a provider profile
        try:
            provider_profile = request.user.provider_profile
        except ProviderProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Provider profile not found. Please create your business profile first.'
            })
        
        # Check if the user is the provider for this order
        if order.provider != provider_profile:
            return JsonResponse({
                'success': False,
                'error': 'You are not authorized to update this order'
            })
        
        # Parse the new status
        data = json.loads(request.body)
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            })
        
        # Update the order status
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Log the status change (optional)
        print(f"Order #{order.id} status changed from {old_status} to {new_status} by provider {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {order.get_status_display()}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request data. Please try again.'
        })
    except Exception as e:
        print(f"Error updating order status: {str(e)}")  # Debug log
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })
