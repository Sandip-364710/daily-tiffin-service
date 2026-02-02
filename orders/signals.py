from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import SavedCart

@receiver(user_logged_in)
def restore_cart_on_login(sender, request, user, **kwargs):
    """
    When a user logs in, merge any SavedCart into the session cart.
    """
    try:
        saved, _ = SavedCart.objects.get_or_create(user=user)
    except Exception:
        return
    session_cart = request.session.get('cart', {}) or {}
    saved_cart = saved.data or {}
    # Merge: increment quantities for overlapping items
    for key, item in saved_cart.items():
        if key in session_cart:
            session_cart[key]['quantity'] = int(session_cart[key].get('quantity', 0)) + int(item.get('quantity', 0))
        else:
            session_cart[key] = item
    request.session['cart'] = session_cart
    request.session.modified = True
