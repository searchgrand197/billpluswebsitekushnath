# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0025_recipe_extra_charges_recipeitem_input_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovementlog',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='stockmovementlog',
            name='unit_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
