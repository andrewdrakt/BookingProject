from .models import Booking
from django.utils import timezone

def active_bookings_processor(request):
    if request.user.is_authenticated:
        active_bookings = Booking.objects.filter(
            user=request.user,
            status__in=['active', 'inside', 'overdue']
        )
        return {
            'active_bookings': active_bookings,
            'now': timezone.now()
        }
    return {}
