# Generated by Django 5.2 on 2025-05-15 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_remove_video_subtitles_file_video_audio_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='subtitles',
            field=models.TextField(blank=True, null=True),
        ),
    ]
