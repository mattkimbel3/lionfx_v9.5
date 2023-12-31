# Generated by Django 3.2.16 on 2023-10-30 06:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forex', '0047_alter_optiontrade_close_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optiontrade',
            name='close_time',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='optiontrade',
            name='countdown',
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
    ]
