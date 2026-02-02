from django import forms
from .models import TiffinService, Review

class TiffinServiceForm(forms.ModelForm):
    class Meta:
        model = TiffinService
        fields = ('name', 'description', 'meal_type', 'price', 'image', 
                 'is_vegetarian', 'spice_level', 'ingredients', 'preparation_time', 'serves')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'ingredients': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
            'rating': forms.Select(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)])
        }
