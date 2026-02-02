from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.db.models import Avg
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import User, ProviderProfile
from .forms import UserRegistrationForm, ProviderProfileForm
from tiffins.models import Review
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

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user and user.is_authenticated:
            messages.success(self.request, f'Login successful! Welcome {user.username}.')
        return response

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
        return render(request, 'accounts/provider_dashboard.html', {
            'provider_profile': provider_profile,
            'avg_rating': avg_rating,
            'total_orders': total_orders,
            'pending_tiffins_count': pending_tiffins_count,
        })
    else:
        return render(request, 'accounts/customer_dashboard.html')

@login_required
def provider_profile_create(request):
    if request.user.user_type != 'provider':
        messages.error(request, 'Only providers can create business profiles.')
        return redirect('dashboard')
    
    if hasattr(request.user, 'provider_profile'):
        messages.info(request, 'You already have a business profile.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ProviderProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Business profile created successfully!')
            return redirect('dashboard')
        else:
            # Show a generic error message (field-level errors also displayed as toasts)
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = ProviderProfileForm()
    
    return render(request, 'accounts/provider_profile_form.html', {'form': form})
