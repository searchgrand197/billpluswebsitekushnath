# Generated migration for print bill/token toggles

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0014_token_ready_timestamp'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='print_bill_enabled',
            field=models.BooleanField(
                default=True,
                help_text='When on, bill/invoice is included when printing. When off, only token can print (if token print is on).'
            ),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='print_token_enabled',
            field=models.BooleanField(
                default=True,
                help_text='When on, token is included when printing (or token-only slip if bill print is off). When off, only bill prints (if bill print is on).'
            ),
        ),
    ]
