# booking/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, ParkingZone

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Подтверждение пароля")

    class Meta:
        model = User
        fields = ['email', 'car_number']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Пароли не совпадают")
        return cleaned_data

class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}), label="Email")

class ParkingZoneForm(forms.ModelForm):
    class Meta:
        model = ParkingZone
        fields = ['name', 'address', 'total_places', 'tariff_per_hour', 'is_available', 'photo']
