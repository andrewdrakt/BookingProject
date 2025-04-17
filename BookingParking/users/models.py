from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
        user = self.create_user(email, password, car_number, **extra_fields)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    car_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Госномер автомобиля")
    is_active = models.BooleanField(default=False, verbose_name="Активен (подтверждение email)")
    is_staff = models.BooleanField(default=False)  # Для доступа в админку
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован (штрафы и т.д.)")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
