# Generated by Django 5.1.6 on 2025-03-21 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_booking_penalty_alter_booking_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена бронирования'),
        ),
    ]
