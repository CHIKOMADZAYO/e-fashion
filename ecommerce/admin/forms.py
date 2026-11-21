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


class AdminRegisterForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'account-input', 'autocomplete': 'username'})
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'account-input', 'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        label='First name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'account-input', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        label='Last name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'account-input', 'autocomplete': 'family-name'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'account-input', 'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'account-input', 'autocomplete': 'new-password'})
    )
    role = forms.ChoiceField(
        label='Role',
        choices=StaffProfile.Role.choices,
        initial=StaffProfile.Role.ADMIN,
        widget=forms.Select(attrs={'class': 'account-input'})
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2