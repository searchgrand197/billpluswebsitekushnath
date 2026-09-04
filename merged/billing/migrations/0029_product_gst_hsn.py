from decimal import Decimal

from django.db import migrations, models


def apply_company_gst_defaults(apps, schema_editor):
    CompanySettings = apps.get_model('billing', 'CompanySettings')
    Product = apps.get_model('billing', 'Product')
    RawMaterial = apps.get_model('billing', 'RawMaterial')
    cs = CompanySettings.objects.first()
    default = Decimal(str(cs.gst_percentage)) if cs and cs.gst_percentage is not None else Decimal('5')
    Product.objects.filter(gst_rate=0).update(gst_rate=default)
    RawMaterial.objects.filter(gst_rate=18).update(gst_rate=default)
    RawMaterial.objects.filter(gst_rate=0).update(gst_rate=default)


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0028_purchase_order_gst_receipts'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='hsn_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='product',
            name='gst_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='rawmaterial',
            name='gst_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='companysettings',
            name='gst_percentage',
            field=models.DecimalField(
                decimal_places=2,
                default=5.0,
                help_text='Default GST percentage used on invoices, products, and purchase orders',
                max_digits=5,
            ),
        ),
        migrations.RunPython(apply_company_gst_defaults, migrations.RunPython.noop),
    ]
