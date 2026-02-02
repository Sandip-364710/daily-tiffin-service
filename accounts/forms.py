from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ProviderProfile


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password1',
            'password2',
            'user_type',
        )

class ProviderProfileForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = ('business_name', 'description', 'delivery_areas', 
                 'min_order_amount', 'delivery_charge', 'preparation_time', 'phone_number')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'delivery_areas': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter areas separated by commas'}),
        }
