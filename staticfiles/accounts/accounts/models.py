

from django.db import models


class Video(models.Model):

    video_file = models.FileField(upload_to='videos/')
    audio_file = models.FileField(upload_to='audios/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_detected = models.BooleanField(default=False)
    transcription = models.FileField(upload_to='transcriptions/', null=True, blank=True)
    subtitles_file = models.FileField(upload_to='subtitles/', null=True, blank=True)

    def __str__(self):
        return self.video_file.name
