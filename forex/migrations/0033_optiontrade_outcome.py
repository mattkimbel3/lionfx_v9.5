# Generated by Django 3.2.16 on 2023-09-25 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forex', '0032_auto_20230925_0314'),
    ]

    operations = [
        migrations.AddField(
            model_name='optiontrade',
            name='outcome',
            field=models.CharField(blank=True, max_length=4, null=True),
        ),
    ]