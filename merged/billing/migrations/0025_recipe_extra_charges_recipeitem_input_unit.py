# Generated manually

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0024_manufacturinglog_labor_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='extra_charges',
            field=models.JSONField(blank=True, default=list, help_text='Dynamic recipe charges e.g. labour, electricity'),
        ),
        migrations.AddField(
            model_name='recipeitem',
            name='input_unit',
            field=models.CharField(blank=True, help_text='Unit the user entered (e.g. g, ml)', max_length=10),
        ),
        migrations.AlterField(
            model_name='recipeitem',
            name='quantity_required',
            field=models.DecimalField(
                decimal_places=6,
                max_digits=14,
                validators=[MinValueValidator(Decimal('0.000001'))],
            ),
        ),
    ]
