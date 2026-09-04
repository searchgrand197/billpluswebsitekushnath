from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0030_invoiceitem_gst_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='customer',
            name='pincode',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='customer',
            name='state',
            field=models.CharField(default='', help_text='Required when creating a customer', max_length=100),
        ),
    ]
