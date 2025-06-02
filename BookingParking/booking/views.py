import uuid
from datetime import datetime
from datetime import timedelta

import requests
from django.db.models import Sum
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST
from .metrics import get_prometheus_metrics
from .forms import VerificationForm, ParkingZoneForm, ParkingZoneEditForm, ReviewForm
from .forms import RegistrationForm, LoginForm
from .models import User, ParkingZone, Booking, Fine, Review
from booking.services.encryption import encrypt_data
from django.db.models import Avg
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
def home(request):
    if request.user.is_authenticated:

        parkings = ParkingZone.objects.filter(is_visible=True).annotate(avg_rating=Avg('reviews__rating'))
        active_bookings = (
            Booking.objects.select_related("parkingzone")
            .prefetch_related("fines")
            .filter(user=request.user, status__in=["active", "inside", "overdue"])
            .order_by("-start_datetime")
        )

        return render(request,"booking/home_authenticated.html",
            {
                "parkings": parkings,
                "active_bookings": active_bookings,
                "now": timezone.now(),
            },
        )
    else:
        return render(request, 'booking/home_unauthenticated.html')

@csrf_exempt
def servo_control(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            esp_ip = request.META.get('REMOTE_ADDR')
            return JsonResponse({"status": 0})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Метод не поддерживается"}, status=405)


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                password = form.cleaned_data['password']
                user.set_password(password)
                user.is_active = False
                user.save()
                token = str(uuid.uuid4())
                confirmation_link = request.build_absolute_uri(
                    reverse('booking:confirm_email', args=[user.id, token])
                )
                send_mail(
                    'Подтверждение регистрации',
                    f'Для подтверждения регистрации перейдите по ссылке: {confirmation_link}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Ошибка регистрации: {e}")
                messages.error(request, "Произошла ошибка при регистрации.")
            messages.success(request, 'Регистрация прошла успешно. Проверьте почту для подтверждения.')
            return redirect('booking:login')
    else:
        form = RegistrationForm()
    return render(request, 'booking/register.html', {'form': form})

def confirm_email(request, user_id, token):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    login(request, user)
    return redirect('booking:profile')

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "Вы не подтвердили почту. Проверьте email для активации аккаунта.")
                return redirect('booking:login')
            login(request, user)
            return redirect('booking:home')
    else:
        form = LoginForm()
    return render(request, 'booking/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('booking:home')

def calculate_extension(booking):
    now = timezone.now()
    overdue_seconds = (now - booking.end_datetime).total_seconds()
    if overdue_seconds <= 0:
        return timedelta(0)
    overdue_minutes = overdue_seconds / 60.0
    if overdue_minutes <= 10:
        return timedelta(minutes=10)
    elif overdue_minutes <= 30:
        return timedelta(minutes=30)
    else:
        hours = int((overdue_minutes + 59) // 60)
        return timedelta(hours=hours)


@login_required
def pay_penalty(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'overdue':
        messages.error(request, "Штраф не требуется для данной брони.")
        return redirect('booking:profile')
    if not booking.has_unpaid_fines():
        messages.info(request, "У вас нет неоплаченных штрафов для этой брони.")
        return redirect('booking:profile')
    penalty_amount = booking.total_fine_amount()

    if penalty_amount <= 0:
        messages.info(request, "У вас нет неоплаченных штрафов для этой брони.")
        return redirect('booking:profile')

    if request.method == 'POST':
        unpaid_fines = booking.fines.filter(is_paid=False)
        for fine in unpaid_fines:
            fine.is_paid = True
            fine.save()

        extension = calculate_extension_duration(booking)
        booking.end_datetime += extension
        booking.penalty = 0
        booking.status = 'inside'
        booking.save()

        user = request.user
        user.is_blocked = False
        user.save()

        local_end = timezone.localtime(booking.end_datetime)
        formatted_end = local_end.strftime("%d.%m.%Y %H:%M")

        receipt_text = (
            f"Оплата штрафов за просрочку.\n"
            f"Парковка: {booking.parkingzone.name}\n"
            f"Сумма штрафов: {penalty_amount:.2f} руб.\n"
            f"Новая дата окончания брони: {formatted_end}\n"
            f"Код бронирования: {booking.reservation_code}\n"
        )

        send_mail(
            "Чек оплаты штрафа",
            receipt_text,
            settings.EMAIL_HOST_USER,
            [booking.user.email],
            fail_silently=False,
        )

        messages.success(request, "Штрафы успешно оплачены. Бронь продлена.")
        return redirect('booking:profile')

    extension = calculate_extension_duration(booking)
    return render(request, 'booking/pay_penalty.html', {
        'booking': booking,
        'penalty': penalty_amount,
        'extension': extension,
    })



@login_required
def user_fines(request):
    user = request.user

    fines = Booking.objects.filter(user=request.user, penalty__gt=0).order_by('-start_datetime')
    return render(request, 'booking/user_fines.html', {'fines': fines})
def create_fine(booking: Booking, amount: float, reason: str) -> None:
    if amount <= 0:
        return
    has_active_fine = booking.fines.filter(is_paid=False).exists()
    if not has_active_fine:
        Fine.objects.create(
            booking=booking,
            amount=amount,
            reason=reason,
            is_paid=False,
        )
@login_required
def profile_view(request):
    user = request.user
    now = timezone.now()

    bookings_to_check = Booking.objects.filter(user=user, status__in=["active", "inside"])
    for booking in bookings_to_check:
        if booking.status == "active" and now > booking.end_datetime:
            booking.status = "finished"
            booking.save(update_fields=["status"])
            messages.info(
                request,
                f"Бронь {booking.reservation_code} завершена, так как вы не воспользовались парковкой.",
            )
            continue

        if booking.status == "inside" and now > booking.end_datetime:
            overdue_seconds = (now - booking.end_datetime).total_seconds()
            if overdue_seconds <= 10 * 60:
                booking.status = "overdue"
                booking.penalty = calculate_penalty(booking)
                booking.save(update_fields=["status", "penalty"])
                create_fine(
                    booking,
                    booking.penalty,
                    reason="Просрочка менее 10 минут",
                )
                messages.warning(
                    request,
                    f"Время брони {booking.reservation_code} истекло. "
                    "Оплатите штраф, чтобы продлить бронь на 10 минут.",
                )
            elif overdue_seconds <= 40 * 60:
                booking.end_datetime += timedelta(minutes=30)
                booking.save(update_fields=["end_datetime"])
                messages.info(
                    request,
                    f"Бронь {booking.reservation_code} продлена на 30 минут из‑за просрочки.",
                )
            else:
                penalty = calculate_penalty(booking)
                booking.status = "overdue"
                booking.penalty = penalty
                booking.user.is_blocked = True
                booking.user.save(update_fields=["is_blocked"])
                booking.save(update_fields=["status", "penalty"])
                create_fine(
                    booking,
                    penalty,
                    reason="Просрочка более 40 минут",
                )
                messages.error(
                    request,
                    f"Бронь {booking.reservation_code} просрочена. Начислен штраф: {penalty} руб.",
                )
    active_bookings = (
        Booking.objects.filter(user=user, status__in=["active", "inside", "overdue"])
        .order_by("-start_datetime")
    )
    finished_bookings = (
        Booking.objects.filter(user=user, status="finished").order_by("-start_datetime")
    )
    fines = Fine.objects.filter(booking__user=user).order_by("-issued_at")
    total_fines = (
        Fine.objects.filter(booking__user=user, is_paid=False).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    return render(
        request,
        "booking/profile.html",
        {
            "active_bookings": active_bookings,
            "finished_bookings": finished_bookings,
            "fines": fines,
            "now": now,
            "total_fines": total_fines,
            "YANDEX_API_KEY": settings.YANDEX_API_KEY,
        },
    )



def mark_overdue_bookings():
    now = timezone.now()
    overdue_bookings = Booking.objects.filter(status='inside', end_datetime__lt=now)

    for booking in overdue_bookings:
        booking.status = 'overdue'
        booking.penalty = calculate_penalty(booking)
        booking.save()

@login_required
def parking_detail(request, parking_id):
    if not request.user.car_number:
        messages.error(request, "Чтобы бронировать парковку, добавьте номер автомобиля в настройках профиля.")
        return redirect('booking:profile')
    parking = get_object_or_404(ParkingZone, id=parking_id)
    today = timezone.localdate()
    has_booking = Booking.objects.filter(user=request.user, parkingzone=parking, status='finished').exists()
    can_review = request.user.is_verified and has_booking
    existing_review = Review.objects.filter(parking=parking, user=request.user).first()
    if request.user.is_blocked:
        messages.error(request, "Ваш аккаунт заблокирован, бронирование невозможно. Обратитесь на контактную почту для того, чтобы узнать подобрости.")
        return redirect('booking:profile')
    context = {
        'parking': parking,
        'today': today,
        'YANDEX_API_KEY': settings.YANDEX_API_KEY
    }
    if not parking.is_available:
        context['unavailable'] = True
        return render(request, 'booking/parking_detail.html', context)
    if 'review_submit' in request.POST:
        if can_review and not existing_review:
            review_form = ReviewForm(request.POST, instance=existing_review)
            if review_form.is_valid():
                new_review = review_form.save(commit=False)
                new_review.user = request.user
                new_review.parking = parking
                new_review.save()
                messages.success(request, "Спасибо за отзыв!")
                return redirect('booking:parking_detail', parking_id=parking.id)
        else:
            messages.error(request, "Вы не можете оставить отзыв.")

    if request.method == "POST":
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time')
        end_date = request.POST.get('end_date')
        end_time = request.POST.get('end_time')
        try:
            start_dt = parse_datetime(start_date, start_time)
            end_dt = parse_datetime(end_date, end_time)
        except Exception as e:
            context['error'] = "Неверный формат даты/времени."
            return render(request, 'booking/parking_detail.html', context)

        if start_dt < timezone.now():
            context['error'] = "Нельзя выбрать дату/время в прошлом."
            return render(request, 'booking/parking_detail.html', context)

        if start_dt >= end_dt:
            context['error'] = "Дата начала должна быть раньше даты окончания."
            return render(request, 'booking/parking_detail.html', context)

        overlapping_bookings = Booking.objects.filter(
            parkingzone=parking,
            end_datetime__gt=start_dt,
            start_datetime__lt=end_dt
        ).count()

        if overlapping_bookings >= parking.total_places:
            context['error'] = "Нет свободных мест на указанный период."
            return render(request, 'booking/parking_detail.html', context)

        user_overlap = Booking.objects.filter(
            user=request.user,
            parkingzone=parking,
            end_datetime__gt=start_dt,
            start_datetime__lt=end_dt,
            status__in=['pending', 'active', 'inside']
        ).exists()

        if user_overlap:
            context['error'] = "У вас уже есть бронь на это время в этой парковке."
            return render(request, 'booking/parking_detail.html', context)

        new_booking = Booking.objects.create(
            user=request.user,
            parkingzone=parking,
            start_datetime=start_dt,
            end_datetime=end_dt,
            reservation_code=str(uuid.uuid4())[:8],
            status='pending',
            paid=False
        )
        return redirect('booking:payment', booking_id=new_booking.id)
    reviews = parking.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    context.update({
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_form': ReviewForm(instance=existing_review) if can_review else None,
        'can_review': can_review,
    })
    return render(request, 'booking/parking_detail.html', context)



def parse_datetime(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return timezone.make_aware(dt, timezone.get_current_timezone())

@login_required
@require_POST
def update_car_number(request):
    new_number = request.POST.get('new_car_number')
    if new_number:
        request.user.car_number = new_number
        request.user.save()
        messages.success(request, "Госномер успешно обновлён.")
    else:
        messages.error(request, "Пожалуйста, введите новый госномер.")
    return redirect('booking:profile')

@login_required
def payment_view(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    duration_seconds = (booking.end_datetime - booking.start_datetime).total_seconds()
    duration_hours = duration_seconds / 3600.0
    cost = duration_hours * float(booking.parkingzone.tariff_per_hour)

    if request.method == 'POST':
        booking.paid = True
        booking.status = 'active'
        booking.price = cost
        booking.save()

        receipt_text = (
            f"Бронирование парковки: {booking.parkingzone.name}\n"
            f"Адрес: {booking.parkingzone.address}\n"
            f"Период: {timezone.localtime(booking.start_datetime).strftime('%d.%m.%Y %H:%M')} - {timezone.localtime(booking.end_datetime).strftime('%d.%m.%Y %H:%M')}\n"
            f"Стоимость: {cost:.2f} руб.\n"
            f"Код бронирования: {booking.reservation_code}"
        )
        send_mail(
            "Чек бронирования парковки",
            receipt_text,
            settings.EMAIL_HOST_USER,
            [booking.user.email],
            fail_silently=False,
        )
        return redirect('booking:booking_success', booking_id=booking.id)

    return render(request, 'booking/payment.html', {
        'booking': booking,
        'cost': cost,
    })

def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    now = timezone.now()
    return render(request, 'booking/booking_success.html', {
        'booking': booking,
        'now': now
    })

def calculate_penalty(booking: Booking) -> float:
    now = timezone.now()
    overdue_seconds = (now - booking.end_datetime).total_seconds()
    if overdue_seconds <= 0:
        return 0.0
    overdue_minutes = overdue_seconds / 60.0
    tariff_per_hour = float(booking.parkingzone.tariff_per_hour)
    if overdue_minutes <= 10:
        penalty = (10 / 60.0) * tariff_per_hour
    elif overdue_minutes <= 30:
        penalty = (30 / 60.0) * tariff_per_hour
    else:
        penalty = (overdue_seconds / 3600.0) * tariff_per_hour
    return round(penalty, 2)

def calculate_extension_duration(booking):
    now = timezone.now()
    overdue_seconds = (now - booking.end_datetime).total_seconds()
    if overdue_seconds <= 10 * 60:
        return timedelta(minutes=10)
    elif overdue_seconds <= 40 * 60:
        return timedelta(minutes=30)
    else:
        hours = int((overdue_seconds + 3599) // 3600)
        return timedelta(hours=hours)

def apply_overdue_penalty(booking: Booking, reason: str = "Просрочка") -> None:
    penalty = calculate_penalty(booking)
    booking.status = "overdue"
    booking.penalty = penalty
    booking.save(update_fields=["status", "penalty"])
    Fine.objects.update_or_create(
        booking=booking,
        is_paid=False,
        defaults={"amount": penalty, "reason": reason},
    )

@login_required
def open_barrier(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    now = timezone.now()
    if booking.status != 'active':
        messages.error(request, "Бронь не активна или уже использована.")
        return redirect('booking:profile')
    if now > booking.end_datetime:
        booking.status = 'finished'
        booking.save()
        messages.error(request, "Срок бронирования истёк. Бронь завершена.")
        return redirect('booking:profile')
    barrier_ip = booking.parkingzone.barrier_ip
    if not barrier_ip:
        messages.error(request, "IP-адрес шлагбаума не указан для этой парковки.")
        return redirect('booking:profile')
    esp_url = f"http://{barrier_ip}/servo"

    try:
        response = requests.post(esp_url, json={"status": 0}, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        messages.error(request, f"Шлагбаум сейчас недоступен. Обратитесь к администратору. {e}")
        return redirect('booking:profile')
    booking.status = 'inside'
    booking.save(update_fields=["status"])
    messages.success(request, "Шлагбаум открыт.")
    return redirect('booking:profile')

@login_required
def check_booking_status(request):
    bookings = Booking.objects.filter(user=request.user, status__in=['active', 'inside', 'overdue'])
    now = timezone.now()

    result = []
    for b in bookings:
        result.append({
            'id': b.id,
            'status': b.status,
            'penalty': b.penalty,
            'start': b.start_datetime.isoformat(),
            'end': b.end_datetime.isoformat(),
        })

    return JsonResponse({'bookings': result, 'now': now.isoformat()})

@login_required
def leave_parking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    now = timezone.now()

    if booking.status == "inside" and now > booking.end_datetime:
        apply_overdue_penalty(booking, "Просрочка при попытке выезда")

    if booking.status == "overdue" and booking.has_unpaid_fines():
        messages.error(request, "У вас есть неоплаченный штраф. Оплатите штраф, чтобы покинуть парковку.")
        return redirect("booking:pay_penalty", booking_id=booking.id)

    if booking.status not in ["inside", "overdue"]:
        messages.error(request, "Вы не на парковке или статус бронирования неверен.")
        return redirect("booking:profile")

    barrier_ip = booking.parkingzone.barrier_ip
    if not barrier_ip:
        messages.error(request, "IP-адрес шлагбаума не указан для этой парковки.")
        return redirect("booking:profile")

    esp_url = f"http://{barrier_ip}/servo"

    try:
        response = requests.post(esp_url, json={"status": 0}, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        messages.error(request, f"Шлагбаум сейчас недоступен. Обратитесь к администратору. {e}")
        return redirect("booking:profile")

    booking.status = "finished"
    booking.save(update_fields=["status"])
    messages.success(request, "Вы успешно покинули парковку.")
    return redirect('booking:profile')

@login_required
def confirm_exit(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    now = timezone.now()

    if booking.status == "inside" and now > booking.end_datetime:
        overdue_seconds = (now - booking.end_datetime).total_seconds()
        if overdue_seconds <= 10 * 60:
            apply_overdue_penalty(booking, "Просрочка менее 10 минут")
        elif overdue_seconds <= 40 * 60:
            booking.end_datetime += timedelta(minutes=30)
            booking.save(update_fields=["end_datetime"])
        else:
            apply_overdue_penalty(booking, "Просрочка более 40 минут")
            booking.user.is_blocked = True
            booking.user.save()

    if booking.status == "overdue" and booking.penalty > 0:
        return redirect("booking:pay_penalty", booking_id=booking.id)

    return render(request, "booking/confirm_exit.html", {"booking": booking})

    return render(request, 'booking/confirm_exit.html', {'booking': booking})

@login_required
def extend_parking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'inside':
        return redirect('booking:profile')

    if request.method == 'POST':
        extra_time = request.POST.get('extra_time')
        try:
            extra_time = int(extra_time)
            if extra_time < 1:
                raise ValueError
        except ValueError:
            return redirect('booking:profile')

        from datetime import timedelta
        booking.end_datetime += timedelta(hours=extra_time)
        booking.save()

    return redirect('booking:profile')


def metrics_view(request):
    data = get_prometheus_metrics()
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
@login_required
def verify_account(request):
    if not request.user.is_active:
        messages.error(request, "Подтвердите свою почту перед подачей заявки на верификацию.")
        return redirect('booking:profile')
    if request.user.is_verified:
        messages.info(request, "Ваш аккаунт уже подтверждён.")
        return redirect('booking:profile')
    if request.user.account_type:
        messages.info(request, "Вы уже подали заявку на подтверждение. Ожидайте решения администратора.")
        return redirect('booking:profile')
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            user = request.user
            user.account_type = form.cleaned_data['account_type']
            user.company_name = form.cleaned_data['company_name'] if form.cleaned_data['account_type'] == 'company' else None

            if form.cleaned_data['account_type'] == 'company':
                if form.cleaned_data['inn']:
                    user.inn = encrypt_data(form.cleaned_data['inn'])
                else:
                    user.inn = None
            elif form.cleaned_data['account_type'] == 'individual':
                if form.cleaned_data.get('passport_data'):
                    user.passport_data = encrypt_data(form.cleaned_data['passport_data'])
                else:
                    user.passport_data = None

            user.phone_number = encrypt_data(form.cleaned_data['phone_number'])
            user.is_verified = False
            user.save()
            send_mail(
                "Новая заявка на верификацию",
                f"Пользователь {user.email} отправил заявку на подтверждение аккаунта.",
                settings.EMAIL_HOST_USER,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "Заявка на верификацию отправлена. Ожидайте подтверждения администратора.")
            return redirect('booking:profile')
    else:
        form = VerificationForm()

    return render(request, 'booking/verify_account.html', {'form': form})


@login_required
def add_parking_zone(request):
    if not request.user.is_verified:
        messages.error(request, "Только подтверждённые пользователи могут добавлять парковки.")
        return redirect('booking:profile')

    if request.method == 'POST':
        form = ParkingZoneForm(request.POST, request.FILES)
        if form.is_valid():
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")

            if not latitude or not longitude:
                form.add_error(None, "Пожалуйста, укажите точку на карте, нажав по нужному месту.")
            else:
                parking_zone = form.save(commit=False)
                parking_zone.latitude = latitude
                parking_zone.longitude = longitude
                parking_zone.owner = request.user
                parking_zone.save()
                messages.success(request, "Парковка успешно добавлена.")
                return redirect('booking:profile')
    else:
        form = ParkingZoneForm()

    return render(request, 'booking/add_parking_zone.html', {'form': form})

@login_required
def my_parking_zones(request):
    user = request.user
    zones = ParkingZone.objects.filter(owner=user)
    return render(request, 'booking/my_parking_zones.html', {'zones': zones})

@login_required
def hide_parking_zone(request, pk):
    parking = get_object_or_404(ParkingZone, pk=pk, owner=request.user)
    parking.is_visible = False
    parking.save()
    messages.success(request, "Парковка скрыта.")
    return redirect('booking:my_parking_zones')

@login_required
def edit_parking_zone(request, pk):
    parking = get_object_or_404(ParkingZone, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = ParkingZoneEditForm(request.POST, request.FILES, instance=parking)
        if form.is_valid():
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")

            if not latitude or not longitude:
                form.add_error(None, "Пожалуйста, укажите точку на карте.")
            else:
                parking = form.save(commit=False)
                try:
                    parking.latitude = float(latitude.replace(',', '.'))
                    parking.longitude = float(longitude.replace(',', '.'))
                except ValueError:
                    form.add_error(None, "Ошибка при сохранении координат.")
                    return render(request, 'booking/edit_parking_zone.html', {'form': form})

                parking.save()
                messages.success(request, "Парковка успешно обновлена.")
                return redirect('booking:my_parking_zones')

    else:
        form = ParkingZoneEditForm(instance=parking)

    return render(request, 'booking/edit_parking_zone.html', {
        'form': form,
        'YANDEX_API_KEY': settings.YANDEX_API_KEY
    })

@login_required
def show_parking_zone(request, pk):
    parking = get_object_or_404(ParkingZone, pk=pk, owner=request.user)
    parking.is_visible = True
    parking.save()
    messages.success(request, "Парковка снова отображается.")
    return redirect('booking:my_parking_zones')


@require_GET
@login_required
def check_availability(request, parking_id):
    from django.utils.dateparse import parse_datetime

    parking = get_object_or_404(ParkingZone, id=parking_id)

    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    try:
        start = parse_datetime(start_str)
        end = parse_datetime(end_str)
    except Exception:
        return JsonResponse({"error": "Неверный формат даты"}, status=400)

    overlapping = Booking.objects.filter(
        parkingzone=parking,
        end_datetime__gt=start,
        start_datetime__lt=end,
        status__in=["pending", "active", "inside"]
    ).count()

    available = parking.total_places - overlapping

    return JsonResponse({
        "available": available > 0,
        "available_places": max(0, available)
    })
