from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings

from django.db.models import Sum
from django.utils.timezone import now

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, car_number=None, **extra_fields):
        if not email:
            raise ValueError("Пользователь должен иметь email")
        email = self.normalize_email(email)
        user = self.model(email=email, car_number=car_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, car_number=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        return self.create_user(email, password, car_number, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    car_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер автомобиля")
    is_active = models.BooleanField(default=False, verbose_name="Активен (подтверждение email)")
    is_staff = models.BooleanField(default=False, verbose_name="Администратор")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован")
    date_joined = models.DateTimeField(default=now, verbose_name="Дата регистрации")
    passport_data = models.CharField(max_length=255, blank=True, null=True, verbose_name="Паспортные данные")
    is_verified = models.BooleanField(default=False, verbose_name="Подтверждённый пользователь")
    ACCOUNT_TYPE_CHOICES = (
        ('individual', 'Частное лицо'),
        ('company', 'Компания'),
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, blank=True, null=True, verbose_name="Тип аккаунта")
    company_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название компании")
    inn = models.CharField(max_length=20, blank=True, null=True, verbose_name="ИНН компании")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class ParkingZone(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название парковочной зоны")
    address = models.TextField(verbose_name="Адрес")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    barrier_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP шлагбаума")
    total_places = models.PositiveIntegerField(verbose_name="Количество мест")
    tariff_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Тариф за час")
    is_available = models.BooleanField(default=True, verbose_name="Доступна")
    photo = models.ImageField(upload_to='parking_photos/', null=True, blank=True, verbose_name="Фото парковки")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Владелец парковки")
    is_visible = models.BooleanField(default=True, verbose_name="Отображать парковку на сайте")

    def __str__(self):
        return self.name
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает оплаты'),
        ('active', 'Активна'),
        ('inside', 'На парковке'),
        ('finished', 'Завершена'),
        ('overdue', 'Просрочена'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parkingzone = models.ForeignKey(ParkingZone, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reservation_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid = models.BooleanField(default=False)
    penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Цена бронирования")
    def __str__(self):
        return f"Бронь {self.reservation_code} для {self.user.email}"
    def total_fine_amount(self):
        return self.fines.aggregate(Sum('amount'))['amount__sum'] or 0
    def total_cost(self):
        return float(self.price) + float(self.total_fine_amount())
    def has_unpaid_fines(self):
        return self.fines.filter(is_paid=False).exists()
class Fine(models.Model):
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='fines')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(default='Просрочка парковки')
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Штраф {self.amount} руб. за {self.booking}"


class Review(models.Model):
    parking = models.ForeignKey(ParkingZone, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parking', 'user')

    def __str__(self):
        return f"{self.rating}★ для {self.parking.name}"
