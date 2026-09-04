from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0032_invoice_customer_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='gstin',
            field=models.CharField(blank=True, help_text='Customer GSTIN (optional)', max_length=15),
        ),
    ]
