from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # أضفنا كلاس بووتستراب لكل الحقول
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
