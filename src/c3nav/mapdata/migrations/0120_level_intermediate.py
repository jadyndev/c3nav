# Generated by Django 5.0.8 on 2024-12-18 20:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mapdata', '0119_dataoverlay_fill_opacity_dataoverlay_stroke_opacity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='level',
            name='intermediate',
            field=models.BooleanField(default=False, verbose_name='intermediate level'),
        ),
    ]
