# Generated manually

from decimal import Decimal

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


def backfill_product_batches(apps, schema_editor):
    ManufacturingLog = apps.get_model('billing', 'ManufacturingLog')
    ProductBatch = apps.get_model('billing', 'ProductBatch')
    Product = apps.get_model('billing', 'Product')
    Stock = apps.get_model('billing', 'Stock')

    for log in ManufacturingLog.objects.all():
        ProductBatch.objects.get_or_create(
            manufacturing=log,
            defaults={
                'product_id': log.product_id,
                'batch_number': log.batch_number,
                'produced_quantity': log.production_quantity,
                'remaining_quantity': log.production_quantity,
                'mfg_date': log.mfg_date,
                'exp_date': log.exp_date,
                'unit_cost': log.unit_cost or 0,
            },
        )

    for product in Product.objects.all():
        batches = list(ProductBatch.objects.filter(product=product).order_by('mfg_date', 'id'))
        if not batches:
            continue
        try:
            stock_qty = Decimal(str(Stock.objects.get(product=product).quantity or 0))
        except Stock.DoesNotExist:
            stock_qty = Decimal('0')
        total_rem = sum((b.remaining_quantity or Decimal('0')) for b in batches)
        extra = total_rem - stock_qty
        if extra <= 0:
            continue
        remaining = extra
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.remaining_quantity, remaining)
            batch.remaining_quantity = batch.remaining_quantity - take
            batch.save(update_fields=['remaining_quantity'])
            remaining -= take


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0026_stockmovementlog_unit_cost_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(max_length=100)),
                ('produced_quantity', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('remaining_quantity', models.DecimalField(
                    decimal_places=3,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                )),
                ('mfg_date', models.DateField(blank=True, null=True)),
                ('exp_date', models.DateField(blank=True, null=True)),
                ('unit_cost', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('manufacturing', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='finished_batch',
                    to='billing.manufacturinglog',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='batches',
                    to='billing.product',
                )),
            ],
            options={
                'ordering': ['mfg_date', 'id'],
            },
        ),
        migrations.RunPython(backfill_product_batches, migrations.RunPython.noop),
    ]
