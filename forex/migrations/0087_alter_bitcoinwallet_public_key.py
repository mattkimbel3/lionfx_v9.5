# Generated by Django 3.2.16 on 2023-11-23 09:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forex', '0086_auto_20231122_1658'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bitcoinwallet',
            name='public_key',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]