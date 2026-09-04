# Generated migration for TV announcement voice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0016_tv_ready_sound'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='tv_announce_voice',
            field=models.CharField(
                blank=True,
                help_text='System voice used for "Token X please collect your order" on TV display. Empty = browser default.',
                max_length=200
            ),
        ),
    ]
