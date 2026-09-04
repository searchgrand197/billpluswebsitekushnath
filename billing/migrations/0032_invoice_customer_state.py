from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0031_customer_state_city_pincode'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='customer_state',
            field=models.CharField(blank=True, help_text='Place of supply (customer state)', max_length=100),
        ),
    ]
