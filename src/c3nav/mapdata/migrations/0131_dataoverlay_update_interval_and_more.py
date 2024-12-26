# Generated by Django 5.1.3 on 2024-12-26 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mapdata', '0130_dataoverlay_edit_access_restriction'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataoverlay',
            name='update_interval',
            field=models.PositiveIntegerField(blank=True, help_text='in seconds', null=True, verbose_name='frontend update interval'),
        ),
        migrations.AlterField(
            model_name='dataoverlay',
            name='fill_opacity',
            field=models.FloatField(blank=True, null=True, verbose_name='default fill opacity'),
        ),
    ]
