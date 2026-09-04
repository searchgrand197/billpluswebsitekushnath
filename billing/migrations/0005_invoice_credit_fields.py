# Generated migration for credit billing fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_product_uom_purchaseorderitem_uom_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='customer_phone',
            field=models.CharField(blank=True, help_text='For A/R ledger matching', max_length=20, default=''),
        ),
        migrations.AddField(
            model_name='invoice',
            name='outstanding_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
