from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, ParkingZone, Review

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Подтверждение пароля")

    class Meta:
        model = User
        fields = ['email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and len(password) < 6:
            self.add_error('password', "Пароль должен быть не менее 6 символов.")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Пароли не совпадают")
        return cleaned_data
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("На эту почту уже зарегистрирован аккаунт.")
        return email

class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}), label="Email")
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("Вы ещё не подтвердили почту. Проверьте email и перейдите по ссылке для активации.", code='inactive')

class ParkingZoneForm(forms.ModelForm):
    class Meta:
        model = ParkingZone
        fields = ['name', 'address', 'total_places', 'tariff_per_hour', 'is_available', 'photo','barrier_mac']
class ParkingZoneEditForm(forms.ModelForm):
    class Meta:
        model = ParkingZone
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'total_places', 'tariff_per_hour', 'barrier_ip',
            'is_available', 'barrier_mac', 'photo'
        ]

class VerificationForm(forms.Form):
    account_type = forms.ChoiceField(
        choices=[('individual', 'Частное лицо'), ('company', 'Компания')],
        label="Тип аккаунта",
        widget=forms.Select(attrs={'id': 'id_account_type'})
    )
    phone_number = forms.CharField(
        required=True,
        label="Номер телефона",
        widget=forms.TextInput(attrs={'placeholder': 'Номер телефона'})
    )
    passport_data = forms.CharField(
        required=False,
        label="Паспортные данные",
        widget=forms.TextInput(attrs={'placeholder': 'Серия и номер паспорта'})
    )
    company_name = forms.CharField(
        required=False,
        label="Название компании"
    )
    inn = forms.CharField(
        required=False,
        label="ИНН компании"
    )

    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')

        if account_type == 'individual':
            if not cleaned_data.get('passport_data'):
                self.add_error('passport_data', "Необходимо указать паспортные данные.")
        elif account_type == 'company':
            if not cleaned_data.get('company_name'):
                self.add_error('company_name', "Необходимо указать название компании.")
            if not cleaned_data.get('inn'):
                self.add_error('inn', "Необходимо указать ИНН.")
        return cleaned_data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        labels = {
            'rating': 'Оценка (от 1 до 5)',
            'comment': 'Комментарий',
        }
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
