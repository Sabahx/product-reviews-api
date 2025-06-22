# user_dashboard/forms.py

from django import forms
from reviews.models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'rating':      forms.Select(choices=[(i, f"{i} نجوم") for i in range(1,6)], attrs={'class':'form-select'}),
            'review_text': forms.Textarea(attrs={'class':'form-control', 'rows':2, 'placeholder':'اكتب مراجعتك…'}),
        }
        labels = {
            'rating': 'التقييم',
            'review_text': 'نص المراجعة',
        }
