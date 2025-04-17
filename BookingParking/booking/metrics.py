# booking/metrics.py
from prometheus_client import Gauge, generate_latest
from .models import Booking, Fine

booking_status_count = Gauge('booking_status_count', 'Количество бронирований по статусам', ['status'])
total_fines_amount = Gauge('total_fines_amount', 'Общая сумма штрафов')

def collect_metrics():
    statuses = ['pending', 'active', 'inside', 'finished', 'overdue']
    for status in statuses:
        count = Booking.objects.filter(status=status).count()
        booking_status_count.labels(status=status).set(count)
    total_fines = Fine.objects.all().aggregate_sum = sum(f.amount for f in Fine.objects.all())
    total_fines_amount.set(total_fines)

def get_prometheus_metrics():
    collect_metrics()
    return generate_latest()
