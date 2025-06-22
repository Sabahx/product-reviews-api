from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
       'class':'w-full px-4 py-2 border rounded','placeholder':'you@example.com'
    }))

    class Meta:
        model  = User
        fields = ['username','email','password1','password2']
        widgets = {
          'username': forms.TextInput(attrs={'class':'w-full px-4 py-2 border rounded','placeholder':'user123'}),
        }
        
from django import forms
from reviews.models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control', 'rows':3}),
            'price': forms.NumberInput(attrs={'class':'form-control'}),
        }
        