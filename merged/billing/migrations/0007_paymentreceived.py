# Generated migration for PaymentReceived model

import django.core.validators
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_customer_customerledgerentry'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentReceived',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('upi', 'UPI'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card'), ('other', 'Other')], default='cash', max_length=20)),
                ('payment_date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('reference_number', models.CharField(blank=True, help_text='Cheque no, UPI ref, etc.', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments_received', to='billing.customer')),
                ('invoice', models.ForeignKey(blank=True, help_text='Optional: link to specific invoice', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments_received', to='billing.invoice')),
            ],
            options={
                'ordering': ['-payment_date', '-id'],
                'verbose_name_plural': 'Payments received',
            },
        ),
    ]
