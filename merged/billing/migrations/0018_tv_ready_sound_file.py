# Generated migration for custom TV ready sound file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0017_tv_announce_voice'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='tv_ready_sound_file',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='sounds/',
                help_text='Custom sound file played when order is ready on TV display (WAV, MP3, etc.). If set, this is used instead of built-in beep/chime.'
            ),
        ),
    ]
