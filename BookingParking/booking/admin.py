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
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'car_number', 'is_staff', 'is_active', 'is_superuser')
    ordering = ('email',)
    search_fields = ('email', 'car_number',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('car_number',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_blocked', 'groups', 'user_permissions')}),
    )

@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'total_places', 'tariff_per_hour', 'is_available', 'barrier_ip', 'barrier_control')
    list_filter = ('is_available',)
    search_fields = ('name', 'address')
    fields = ('name', 'address', 'latitude', 'longitude', 'barrier_ip', 'total_places', 'tariff_per_hour', 'photo', 'is_available')

    class Media:
        js = ('js/parking_admin_map.js',)
        css = {
            'all': ('css/hide_fields.css',)
        }

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
        if not zone.barrier_ip:
            messages.error(request, f"У парковки {zone.name} не указан IP шлагбаума.")
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        fastapi_url = f"http://{zone.barrier_ip}/servo"
        try:
            response = requests.post(fastapi_url, json={"status": status_code}, timeout=5)
            response.raise_for_status()
            messages.success(request, f"{action_name} → {zone.name}: УСПЕХ")
        except requests.RequestException as e:
            messages.error(request, f"{action_name} → {zone.name}: !!! Ошибка: {e}")
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