from django.urls import path
from .views import (
    login_view, register_view, welcome_view,
    upload_video, detect_lips, home, delete_video,
    root_redirect_view, edit_transcription
)

urlpatterns = [
    # Redirection racine → /login/
    path('', root_redirect_view),


    # Authentification
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('welcome/', welcome_view, name='welcome'),

    # Page principale
    path('home/', home, name='home'),

    # Gestion vidéos
    path('upload/', upload_video, name='upload_video'),
    path('detect_lips/', detect_lips, name='detect_lips'),
    path('delete_video/<int:video_id>/', delete_video, name='delete_video'),
    path('edit-transcription/<int:video_id>/', edit_transcription, name='edit_transcription'),

]
