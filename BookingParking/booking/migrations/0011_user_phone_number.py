# Generated by Django 5.2 on 2025-04-27 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0010_user_passport_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Номер телефона'),
        ),
    ]
