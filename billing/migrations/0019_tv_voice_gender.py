from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0018_tv_ready_sound_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='tv_voice_gender',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('auto', 'Auto (system default)'),
                    ('male', 'Male'),
                    ('female', 'Female'),
                ],
                default='auto',
                help_text='Voice style for Token TV announcements (male/female pitch).',
            ),
        ),
    ]

