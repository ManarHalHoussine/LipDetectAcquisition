import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import Video  # ⬅️ adapte le nom de ton app ici

class Command(BaseCommand):
    help = 'Exporte les vidéos/audio/transcriptions en CSV'

    def handle(self, *args, **kwargs):
        export_path = os.path.join(settings.BASE_DIR, 'dataset_export.csv')
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['video_url', 'audio_url', 'transcription_url', 'is_detected', 'uploaded_at'])

            for video in Video.objects.all():
                writer.writerow([
                    settings.MEDIA_URL + video.video_file.name if video.video_file else '',
                    settings.MEDIA_URL + video.audio_file.name if video.audio_file else '',
                    settings.MEDIA_URL + video.transcription.name if video.transcription else '',
                    video.is_detected,
                    video.uploaded_at
                ])

        self.stdout.write(self.style.SUCCESS(f'✅ Export CSV terminé: {export_path}'))
