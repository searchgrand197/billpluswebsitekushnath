from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0013_token_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='token_ready_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                db_index=True,
                help_text='Timestamp when token was marked Ready (for auto-hide on display)',
            ),
        ),
    ]

