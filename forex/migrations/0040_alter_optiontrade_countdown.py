# Generated by Django 3.2.16 on 2023-10-28 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forex', '0039_alter_optiontrade_countdown'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optiontrade',
            name='countdown',
            field=models.DurationField(blank=True, null=True),
        ),
    ]