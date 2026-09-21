# Generated manually for estimated vs actual manufacturing output

from decimal import Decimal

from django.db import migrations, models


def backfill_actual_for_completed(apps, schema_editor):
    """Existing completed batches already posted stock from production_quantity."""
    ManufacturingLog = apps.get_model('billing', 'ManufacturingLog')
    for log in ManufacturingLog.objects.filter(status='completed'):
        qty = log.production_quantity or Decimal('0')
        ManufacturingLog.objects.filter(pk=log.pk).update(
            actual_quantity=qty,
            wastage_quantity=Decimal('0'),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0033_customer_gstin'),
    ]

    operations = [
        migrations.AddField(
            model_name='manufacturinglog',
            name='actual_quantity',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Actual good units after production — finished stock is posted from this',
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='manufacturinglog',
            name='wastage_quantity',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Estimated minus actual (wasted / failed units)',
                max_digits=10,
            ),
        ),
        migrations.RunPython(backfill_actual_for_completed, migrations.RunPython.noop),
    ]
