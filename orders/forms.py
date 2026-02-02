from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('delivery_address', 'delivery_phone', 'delivery_date', 'delivery_time', 'special_instructions')
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_time': forms.TimeInput(attrs={'type': 'time'}),
            'special_instructions': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any special instructions for the provider...'}),
        }
