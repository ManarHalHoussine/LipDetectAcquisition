# Generated by Django 5.2 on 2025-05-15 09:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_video_subtitles'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='video',
            name='subtitles',
        ),
        migrations.AddField(
            model_name='video',
            name='subtitles_file',
            field=models.FileField(blank=True, null=True, upload_to='subtitles/'),
        ),
    ]
