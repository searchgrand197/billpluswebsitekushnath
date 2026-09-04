# Generated migration for Customer and CustomerLedgerEntry (A/R credit billing)

import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_invoice_credit_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('outstanding_balance', models.DecimalField(decimal_places=2, default=0, help_text='Total amount owed by customer (A/R)', max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'unique_together': [['name', 'phone']],
            },
        ),
        migrations.CreateModel(
            name='CustomerLedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_type', models.CharField(choices=[('invoice', 'Invoice / Bill'), ('payment', 'Payment Received'), ('adjustment', 'Adjustment')], max_length=20)),
                ('debit', models.DecimalField(decimal_places=2, default=0, help_text='Amount added to balance (bill)', max_digits=12)),
                ('credit', models.DecimalField(decimal_places=2, default=0, help_text='Amount deducted from balance (payment)', max_digits=12)),
                ('balance_after', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('entry_date', models.DateField(default=django.utils.timezone.localdate)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ledger_entries', to='billing.customer')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_entries', to='billing.invoice')),
            ],
            options={
                'ordering': ['-entry_date', '-id'],
                'verbose_name_plural': 'Customer ledger entries',
            },
        ),
    ]
