from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from .models import User
import uuid

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        car_number = request.POST.get('car_number')

        if password != confirm_password:
            # Возвращаем ошибку
            return render(request, 'users/register.html', {'error': 'Пароли не совпадают'})

        user = User.objects.create_user(email=email, password=password, car_number=car_number)
        user.is_active = False  # станет True после подтверждения
        user.save()

        # Генерируем ссылку для подтверждения
        confirmation_link = f"http://127.0.0.1:8000/users/confirm_email/{user.id}/{uuid.uuid4()}/"
        # В реальном проекте UUID стоит хранить где-то в модели или Redis, чтобы проверить при подтверждении.
        # Здесь для примера просто генерируем ссылку и отправляем.

        send_mail(
            'Подтверждение регистрации',
            f'Пожалуйста, перейдите по ссылке, чтобы активировать аккаунт: {confirmation_link}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False
        )

        return render(request, 'users/register.html', {'message': 'На вашу почту отправлено письмо для подтверждения.'})

    return render(request, 'users/register.html')
def confirm_email_view(request, user_id, code):
    # В реальном проекте code должен быть связан с user_id (например, храниться в отдельном поле).
    try:
        user = User.objects.get(pk=user_id)
        user.is_active = True
        user.save()
        # Можно автоматически логинить пользователя после активации
        login(request, user)
        return redirect('users:profile')  # например, перенаправить на страницу профиля
    except User.DoesNotExist:
        return render(request, 'users/confirm_email.html', {'error': 'Неверная ссылка или пользователь не существует'})

from django.contrib.auth.decorators import login_required
from booking.models import Booking

@login_required
def profile_view(request):
    user = request.user
    bookings = Booking.objects.filter(user=user).order_by('-start_datetime')
    return render(request, 'users/profile.html', {'bookings': bookings})