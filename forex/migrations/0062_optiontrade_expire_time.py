# Generated by Django 3.2.16 on 2023-10-30 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forex', '0061_alter_optiontrade_time_now'),
    ]

    operations = [
        migrations.AddField(
            model_name='optiontrade',
            name='expire_time',
            field=models.PositiveSmallIntegerField(default=2),
            preserve_default=False,
        ),
    ]
