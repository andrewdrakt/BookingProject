from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import User, ParkingZone, Booking

class BookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email='test@test.com', password='12345678')
        self.parking = ParkingZone.objects.create(
            name="Test Parking",
            address="Test Address",
            total_places=5,
            tariff_per_hour=100
        )
    def test_registration_page(self):
        response = self.client.get(reverse('booking:register'))
        self.assertEqual(response.status_code, 200)
    def test_login_page(self):
        response = self.client.get(reverse('booking:login'))
        self.assertEqual(response.status_code, 200)
    def test_create_booking(self):
        self.client.login(email='test@test.com', password='12345678')
        start_time = timezone.now() + timezone.timedelta(hours=1)
        end_time = start_time + timezone.timedelta(hours=2)
        booking = Booking.objects.create(
            user=self.user,
            parkingzone=self.parking,
            start_datetime=start_time,
            end_datetime=end_time,
            reservation_code="ABC123",
            status='pending',
            paid=False
        )
        self.assertEqual(Booking.objects.count(), 1)
    def test_home_page_authenticated(self):
        self.client.login(email='test@test.com', password='12345678')
        response = self.client.get(reverse('booking:home'))
        self.assertEqual(response.status_code, 200)
    def test_home_page_unauthenticated(self):
        response = self.client.get(reverse('booking:home'))
        self.assertEqual(response.status_code, 200)
