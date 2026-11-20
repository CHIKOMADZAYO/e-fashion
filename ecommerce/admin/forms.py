from django import forms
from django.contrib.auth import get_user_model, authenticate

from ecommerce.admin.models import StaffProfile

User = get_user_model()


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'account-input', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'account-input', 'autocomplete': 'current-password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if username and password:
            user = authenticate(request=None, username=username, password=password)
            if not user:
                raise forms.ValidationError('Invalid username or password.')
            if not user.staff_profile.is_active:
                raise forms.ValidationError('Your account is disabled.')
        return cleaned_data