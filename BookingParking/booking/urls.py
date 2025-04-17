# booking/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
app_name = 'booking'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('confirm_email/<int:user_id>/<str:token>/', views.confirm_email, name='confirm_email'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('parking/<int:parking_id>/', views.parking_detail, name='parking_detail'),
    path('parking/<int:parking_id>/', views.parking_detail, name='parking_detail'),
    path('payment/<int:booking_id>/', views.payment_view, name='payment'),
    path('pay_penalty/<int:booking_id>/', views.pay_penalty, name='pay_penalty'),
    path('booking_success/<int:booking_id>/', views.booking_success, name='booking_success'),
    path('profile/', views.profile_view, name='profile'),
    path('open_barrier/<int:booking_id>/', views.open_barrier, name='open_barrier'),
    path('leave_parking/<int:booking_id>/', views.leave_parking, name='leave_parking'),
    path('extend_parking/<int:booking_id>/', views.extend_parking, name='extend_parking'),
    path('check-status/', views.check_booking_status, name='check_booking_status'),
    path('confirm-exit/<int:booking_id>/', views.confirm_exit, name='confirm_exit'),
    path('fines/', views.user_fines, name='user_fines'),
    path('update-car-number/', views.update_car_number, name='update_car_number'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='booking/password_reset_form.html',
             email_template_name='booking/password_reset_email.html',
             subject_template_name='booking/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='booking/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='booking/password_reset_confirm.html',
             success_url='/reset/done/'),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='booking/password_reset_complete.html'),
         name='password_reset_complete'),
    path('metrics/', views.metrics_view, name='metrics'),

]
