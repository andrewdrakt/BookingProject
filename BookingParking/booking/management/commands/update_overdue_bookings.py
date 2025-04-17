from django.core.management.base import BaseCommand
from booking.models import Booking
from django.utils import timezone
from booking.views import calculate_penalty
from datetime import timedelta

class Command(BaseCommand):
    help = 'Обновляет просроченные бронирования и начисляет штрафы'

    def handle(self, *args, **kwargs):
        now = timezone.now()

        overdue_bookings = Booking.objects.filter(status='inside', end_datetime__lt=now)

        updated_count = 0
        for booking in overdue_bookings:
            overdue_seconds = (now - booking.end_datetime).total_seconds()

            if overdue_seconds <= 10 * 60:
                booking.status = 'overdue'
                booking.penalty = calculate_penalty(booking)
                booking.save()
                updated_count += 1

            elif overdue_seconds <= 40 * 60:
                booking.end_datetime += timedelta(minutes=30)
                booking.status = 'inside'
                booking.penalty = 0
                booking.save()

            else:
                booking.status = 'overdue'
                booking.penalty = calculate_penalty(booking)
                booking.user.is_blocked = True
                booking.user.save()
                booking.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Обновлено {updated_count} просроченных бронирований'))
