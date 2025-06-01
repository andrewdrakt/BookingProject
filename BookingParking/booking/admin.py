from django.contrib import admin
from .models import ParkingZone
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
import requests
from .models import ParkingZone
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from booking.services.encryption import decrypt_data
from django.contrib.admin import SimpleListFilter
from .models import DeviceCommand
def display_passport_data(obj):
    try:
        return decrypt_data(obj.passport_data)
    except:
        return "Ошибка расшифровки"

def display_inn(obj):
    try:
        return decrypt_data(obj.inn)
    except:
        return "Ошибка расшифровки"

@admin.action(description="Подтвердить выбранные аккаунты")
def confirm_users(modeladmin, request, queryset):
    for user in queryset:
        if not user.is_verified:
            user.is_verified = True

            user.save()
            send_mail(
                "Ваш аккаунт подтверждён!",
                "Здравствуйте!\n\nВаша заявка на верификацию успешно одобрена. Теперь вы можете добавлять свои парковочные зоны.\n\n С уважением, команда Automatics Systems",
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
class VerificationStatusFilter(SimpleListFilter):
    title = 'Статус верификации'
    parameter_name = 'verification_status'

    def lookups(self, request, model_admin):
        return [
            ('pending', 'Ожидают подтверждения'),
            ('verified', 'Подтверждённые'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(is_verified=False, account_type__isnull=False)
        if self.value() == 'verified':
            return queryset.filter(is_verified=True)
        return queryset
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'is_verified', 'account_type',
                    'company_name', 'display_inn', 'display_passport_data', 'display_phone',
                    'car_number', 'is_staff', 'is_active', 'is_superuser')
    list_filter = ('is_verified', 'account_type', VerificationStatusFilter, 'account_type')
    ordering = ('email',)
    search_fields = ('email', 'car_number','company_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('car_number',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_blocked', 'groups', 'user_permissions')}),
    )

    def display_passport_data(self, obj):
        if obj.passport_data:
            try:
                return decrypt_data(obj.passport_data)
            except Exception:
                return "Ошибка расшифровки"
        return "-"

    def display_inn(self, obj):
        if obj.inn:
            try:
                return decrypt_data(obj.inn)
            except Exception:
                return "Ошибка расшифровки"
        return "-"

    def display_phone(self, obj):
        if obj.phone_number:
            try:
                return decrypt_data(obj.phone_number)
            except Exception:
                return "-"
        return "-"

    actions = [confirm_users]
    display_passport_data.short_description = "Паспортные данные"
    display_inn.short_description = "ИНН компании"
    display_phone.short_description = "Номер телефона"


@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'total_places', 'tariff_per_hour', 'is_available', 'display_owner', 'barrier_ip', 'barrier_mac', 'barrier_control')
    list_filter = ('is_available',)
    search_fields = ('name', 'address')
    fields = ('name', 'address', 'latitude', 'longitude', 'barrier_ip', 'barrier_mac', 'total_places', 'tariff_per_hour', 'photo', 'is_available', 'owner')
    autocomplete_fields = ('owner',)

    class Media:
        js = ('js/parking_admin_map.js',)
        css = {
            'all': ('css/hide_fields.css',)
        }

    def render(self):
        from django.conf import settings
        return format_html(
            '<script id="yandex-key" data-key="{}"></script>',
            settings.YANDEX_API_KEY
        )
    def display_owner(self, obj):
        if obj.owner:
            if obj.owner.account_type == 'company' and obj.owner.company_name:
                return f"Компания: {obj.owner.company_name}"
            else:
                return "Частное лицо"
        return "-"

    display_owner.short_description = "Владелец парковки"
    def barrier_control(self, obj):
        return format_html(
            '<div style="display: flex; flex-wrap: wrap; gap: 5px;">'
            '  <a class="btn" style="padding:5px 10px; background:#28a745; color:white; border-radius:4px; text-decoration:none;" href="{}">Открыть</a>'
            '  <a class="btn" style="padding:5px 10px; background:#fd7e14; color:white; border-radius:4px; text-decoration:none;" href="{}">15 сек</a>'
            '  <a class="btn" style="padding:5px 10px; background:#dc3545; color:white; border-radius:4px; text-decoration:none;" href="{}">Закрыть</a>'
            '  <a class="btn" style="padding:5px 10px; background:#007bff; color:white; border-radius:4px; text-decoration:none;" href="{}">Проверить</a>'
            '</div>',
            f'manual-open-barrier/{obj.pk}/',
            f'timed-open-barrier/{obj.pk}/',
            f'close-barrier/{obj.pk}/',
            f'test-barrier/{obj.pk}/',
        )

    barrier_control.short_description = "Управление шлагбаумом"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('manual-open-barrier/<int:pk>/', self.admin_site.admin_view(self.manual_open), name='manual-open'),
            path('timed-open-barrier/<int:pk>/', self.admin_site.admin_view(self.timed_open), name='timed-open'),
            path('close-barrier/<int:pk>/', self.admin_site.admin_view(self.force_close), name='force-close'),
            path('test-barrier/<int:pk>/', self.admin_site.admin_view(self.test_barrier), name='test-barrier'),
        ]
        return custom + urls

    def _send_command(self, status_code, pk, action_name, request):
        zone = ParkingZone.objects.get(pk=pk)
        if not zone.barrier_mac:
            messages.error(request, f"У парковки {zone.name} не указан MAC ESP.")
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        DeviceCommand.objects.create(device_id=zone.barrier_mac, status=status_code)
        messages.success(request, f"{action_name} → {zone.name}: Команда сохранена")
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def manual_open(self, request, pk):
        return self._send_command(1, pk, "Ручное открытие", request)

    def timed_open(self, request, pk):
        return self._send_command(0, pk, "Открытие на 15 секунд", request)

    def force_close(self, request, pk):
        return self._send_command(2, pk, "Принудительное закрытие", request)

    def test_barrier(self, request, pk):
        zone = ParkingZone.objects.get(pk=pk)
        if not zone.barrier_ip:
            messages.error(request, f"У парковки {zone.name} не указан IP.")
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        fastapi_url = f"http://{zone.barrier_ip}/servo"
        try:
            response = requests.options(fastapi_url, timeout=3)
            if response.status_code in [200, 204]:
                messages.success(request, f"Связь с {zone.barrier_ip} установлена.")
            else:
                messages.warning(request, f"Ответ от {zone.barrier_ip}, но статус: {response.status_code}")
        except requests.RequestException as e:
            messages.error(request, f"Не удалось подключиться к {zone.barrier_ip}: {e}")
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))
