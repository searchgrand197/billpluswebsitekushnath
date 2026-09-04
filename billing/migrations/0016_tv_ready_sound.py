# Generated migration for TV ready sound choice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0015_print_bill_token_toggles'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='tv_ready_sound',
            field=models.CharField(
                choices=[('none', 'No sound'), ('beep', 'Beep'), ('beep_double', 'Double beep'), ('beep_triple', 'Triple beep'), ('chime', 'Chime')],
                default='beep',
                help_text='Sound played on TV display when an order becomes ready.',
                max_length=20
            ),
        ),
    ]
