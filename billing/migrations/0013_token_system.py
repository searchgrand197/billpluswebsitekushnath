from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_product_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='enable_token_system',
            field=models.BooleanField(
                default=False,
                help_text='When enabled, generate kitchen tokens for each bill and show kitchen/token display pages.',
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='token_number',
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='token_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('preparing', 'Preparing'),
                    ('ready', 'Ready'),
                    ('delivered', 'Delivered'),
                ],
                default='pending',
                help_text='Kitchen token status for this bill',
                max_length=20,
            ),
        ),
    ]

