from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from .models import TiffinService, Review
from .forms import TiffinServiceForm, ReviewForm
from django.http import JsonResponse

def home(request):
    featured_tiffins = TiffinService.objects.filter(is_available=True, is_approved=True)[:6]
    return render(request, 'tiffins/home.html', {
        'featured_tiffins': featured_tiffins
    })

def tiffin_list(request):
    tiffins = TiffinService.objects.filter(is_available=True, is_approved=True)
    
    # Search functionality
    search_raw = request.GET.get('search', '')
    search_query = (search_raw or '').strip()
    if search_query:
        sq = search_query.lower()

        # If user types 'all' or similar, do not narrow results
        all_tokens = {'all', 'all meal', 'all meals', 'badhu', 'baddhu', 'sabka', 'saru badhu'}
        if sq in all_tokens:
            pass
        else:
            # Map common Gujarati/typo variants to canonical meal types
            normalized_meal = None
            if any(k in sq for k in ['breakfast', 'brekfast', 'breckfast', 'nashto', 'nasto', 'nashta', 'morning']):
                normalized_meal = 'breakfast'
            elif any(k in sq for k in ['lunch', 'luch', 'lanch', 'bapor']):
                normalized_meal = 'lunch'
            elif any(k in sq for k in ['dinner', 'dinnar', 'ratri', 'sanj']):
                normalized_meal = 'dinner'
            elif any(k in sq for k in ['snack', 'snacks', 'nasta', 'nashta', 'evening']):
                normalized_meal = 'snacks'

            # Map veg/non-veg tokens
            veg_token = any(k in sq for k in ['veg', 'vegetarian', 'shakahari', 'shakahariyo']) and not any(k in sq for k in ['non-veg', 'nonveg', 'non veg'])
            nonveg_token = any(k in sq for k in ['non-veg', 'nonveg', 'non veg', 'nonvegitarian', 'mashahari'])

            q_obj = (
                Q(name__icontains=sq) |
                Q(description__icontains=sq) |
                Q(ingredients__icontains=sq) |
                Q(meal_type__icontains=sq) |
                Q(spice_level__icontains=sq) |
                Q(provider__business_name__icontains=sq) |
                Q(provider__user__city__icontains=sq)
            )

            if normalized_meal:
                q_obj = q_obj | Q(meal_type=normalized_meal)

            # Apply composed query first
            tiffins = tiffins.filter(q_obj)

            # Then apply explicit veg/non-veg narrowing if detected
            if veg_token and not nonveg_token:
                tiffins = tiffins.filter(is_vegetarian=True)
            elif nonveg_token and not veg_token:
                tiffins = tiffins.filter(is_vegetarian=False)
    
    # (Category filter removed)

    # Filter by meal type
    meal_type_raw = request.GET.get('meal_type', '')
    meal_type = (meal_type_raw or '').strip().lower()
    if meal_type in {'breakfast', 'lunch', 'dinner', 'snacks'}:
        tiffins = tiffins.filter(meal_type=meal_type)
    
    # Filter by vegetarian
    is_veg_raw = request.GET.get('is_veg', '')
    is_veg = (is_veg_raw or '').strip().lower()
    if is_veg in {'true', '1', 'yes'}:
        tiffins = tiffins.filter(is_vegetarian=True)
    
    # Filter by city
    city_raw = request.GET.get('city', '')
    city = (city_raw or '').strip()
    if city:
        tiffins = tiffins.filter(provider__user__city__icontains=city)
    
    return render(request, 'tiffins/tiffin_list.html', {
        'tiffins': tiffins,
        'search_query': search_query,
        'selected_meal_type': meal_type,
        'selected_city': city,
        'selected_is_veg': is_veg if is_veg in {'true', '1', 'yes'} else '',
    })

def tiffin_detail(request, pk):
    tiffin = get_object_or_404(TiffinService, pk=pk, is_available=True, is_approved=True)
    reviews = tiffin.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'tiffin': tiffin,
        'reviews': reviews,
        'avg_rating': avg_rating,
    }
    
    if request.user.is_authenticated and request.user.user_type == 'customer':
        # Check if user has already reviewed this tiffin
        user_has_reviewed = reviews.filter(customer=request.user).exists()
        if not user_has_reviewed:
            context['review_form'] = ReviewForm()
        context['user_has_reviewed'] = user_has_reviewed
    
    return render(request, 'tiffins/tiffin_detail.html', context)

@login_required
def add_review(request, pk):
    if request.user.user_type != 'customer':
        messages.error(request, 'Only customers can add reviews.')
        return redirect('tiffin_detail', pk=pk)
    
    tiffin = get_object_or_404(TiffinService, pk=pk)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.tiffin_service = tiffin
            review.customer = request.user
            try:
                review.save()
                messages.success(request, 'Review added successfully!')
            except Exception as e:
                if 'Duplicate entry' in str(e):
                    messages.warning(request, 'You have already reviewed this tiffin service.')
                else:
                    messages.error(request, 'Error adding review. Please try again.')
    
    return redirect('tiffin_detail', pk=pk)

@login_required
def provider_tiffins(request):
    if request.user.user_type != 'provider':
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        provider_profile = request.user.provider_profile
        tiffins = provider_profile.tiffin_services.all()
        return render(request, 'tiffins/provider_tiffins.html', {'tiffins': tiffins})
    except:
        messages.error(request, 'Please create your provider profile first.')
        return redirect('provider_profile_create')

@login_required
def add_tiffin(request):
    if request.user.user_type != 'provider':
        messages.error(request, 'Only providers can add tiffin services.')
        return redirect('home')
    
    try:
        provider_profile = request.user.provider_profile
    except:
        messages.error(request, 'Please create your provider profile first.')
        return redirect('provider_profile_create')
    
    if request.method == 'POST':
        form = TiffinServiceForm(request.POST, request.FILES)
        if form.is_valid():
            tiffin = form.save(commit=False)
            tiffin.provider = provider_profile
            # is_approved defaults to False; keep pending until admin approves
            tiffin.is_approved = False
            tiffin.save()
            messages.success(request, 'Tiffin submitted successfully. Admin approval is pending — it will show on your dashboard after approval.')
            return redirect('dashboard')
    else:
        form = TiffinServiceForm()
    
    return render(request, 'tiffins/add_tiffin.html', {'form': form})

@login_required
def edit_tiffin(request, pk):
    if request.user.user_type != 'provider':
        messages.error(request, 'Access denied.')
        return redirect('home')

    tiffin = get_object_or_404(TiffinService, pk=pk)
    try:
        provider_profile = request.user.provider_profile
    except:
        messages.error(request, 'Please create your provider profile first.')
        return redirect('provider_profile_create')

    if tiffin.provider_id != provider_profile.id:
        messages.error(request, 'You can edit only your own tiffins.')
        return redirect('provider_tiffins')

    if request.method == 'POST':
        form = TiffinServiceForm(request.POST, request.FILES, instance=tiffin)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tiffin service updated successfully!')
            return redirect('provider_tiffins')
    else:
        form = TiffinServiceForm(instance=tiffin)

    return render(request, 'tiffins/add_tiffin.html', {
        'form': form,
        'edit_mode': True,
    })

@login_required
def toggle_availability(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    if request.user.user_type != 'provider':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    tiffin = get_object_or_404(TiffinService, pk=pk)
    try:
        provider_profile = request.user.provider_profile
    except Exception:
        return JsonResponse({'success': False, 'error': 'Provider profile missing'}, status=400)

    if tiffin.provider_id != provider_profile.id:
        return JsonResponse({'success': False, 'error': 'Not your tiffin'}, status=403)

    tiffin.is_available = not tiffin.is_available
    tiffin.save(update_fields=['is_available'])
    return JsonResponse({
        'success': True,
        'is_available': tiffin.is_available,
        'label': 'Disable' if tiffin.is_available else 'Enable'
    })

def chatbot(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    msg = (request.POST.get('message') or '').strip().lower()
    if not msg:
        return JsonResponse({'success': True, 'reply': "Please type your question. For example: 'show lunch in Ahmedabad', 'price of paneer', 'how to order'"})

    # Basic intent routing
    # 1) Help/How to order
    if any(k in msg for k in ['how to order', 'order', 'place order', 'order kar', 'book']):
        return JsonResponse({'success': True, 'reply': 'To order: open any tiffin detail page, click Add to Cart, then open Cart and proceed to checkout.'})

    # 2) Delivery info
    if any(k in msg for k in ['deliver', 'delivery', 'reach', 'kitla time']):
        return JsonResponse({'success': True, 'reply': 'Delivery time depends on provider and your area. See Provider Info on the tiffin detail page for delivery areas and charges.'})

    # Vegetarian toggle detection
    veg_token = ('veg' in msg or 'vegetarian' in msg) and not any(k in msg for k in ['non-veg', 'non veg', 'nonveg'])

    # 3) Price query
    if 'price' in msg or 'rate' in msg:
        # Try to extract a keyword and find matching tiffins
        keyword = msg.replace('price', '').replace('rate', '').strip()
        qs = TiffinService.objects.filter(is_available=True, is_approved=True)
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(description__icontains=keyword) | Q(ingredients__icontains=keyword))
        if veg_token:
            qs = qs.filter(is_vegetarian=True)
        qs = qs.order_by('price')[:3]
        if qs:
            lines = [f"{t.name} - ₹{t.price}" for t in qs]
            return JsonResponse({'success': True, 'reply': 'Here are some options:\n' + '\n'.join(lines)})
        return JsonResponse({'success': True, 'reply': 'No matching tiffins found for that price query.'})

    # 4) Meal and city quick search like: 'lunch in surat' or 'breakfast ahmedabad'
    meal_map = {
        'breakfast': 'breakfast', 'nashta': 'breakfast', 'nasto': 'breakfast',
        'lunch': 'lunch', 'dinner': 'dinner', 'snack': 'snacks', 'snacks': 'snacks'
    }
    meal = None
    for k, v in meal_map.items():
        if k in msg:
            meal = v
            break

    qs = TiffinService.objects.filter(is_available=True)
    if meal:
        qs = qs.filter(meal_type=meal)
    if veg_token:
        qs = qs.filter(is_vegetarian=True)

    # crude city detection after 'in '
    city = None
    if ' in ' in msg:
        try:
            city = msg.split(' in ', 1)[1].strip()
        except Exception:
            city = None
    if city:
        qs = qs.filter(provider__user__city__icontains=city)

    if meal or city:
        items = qs[:5]
        if items:
            lines = [f"{t.name} (₹{t.price}) - {t.provider.user.city}" for t in items]
            return JsonResponse({'success': True, 'reply': 'Here are some matching tiffins:\n' + '\n'.join(lines)})
        return JsonResponse({'success': True, 'reply': 'No matching tiffins found for your query.'})

    # Fallback generic search on keywords
    qs = TiffinService.objects.filter(is_available=True)
    if veg_token:
        qs = qs.filter(is_vegetarian=True)
    qs = qs.filter(
        Q(name__icontains=msg) | Q(description__icontains=msg) | Q(ingredients__icontains=msg) | Q(provider__business_name__icontains=msg)
    )[:5]
    if qs:
        lines = [f"{t.name} - ₹{t.price}" for t in qs]
        return JsonResponse({'success': True, 'reply': 'I found these tiffins:\n' + '\n'.join(lines)})

    return JsonResponse({'success': True, 'reply': "Sorry, I couldn't find that. Try: 'lunch in Ahmedabad' or 'price paneer' or 'how to order'"})


@login_required
def provider_reviews(request):
    if request.user.user_type != 'provider':
        messages.error(request, 'Access denied.')
        return redirect('home')

    try:
        provider_profile = request.user.provider_profile
    except Exception:
        messages.error(request, 'Please create your provider profile first.')
        return redirect('provider_profile_create')

    reviews = Review.objects.filter(tiffin_service__provider=provider_profile).select_related('tiffin_service', 'customer').order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    return render(request, 'tiffins/provider_reviews.html', {
        'reviews': reviews,
        'avg_rating': avg_rating,
        'provider_profile': provider_profile,
    })
