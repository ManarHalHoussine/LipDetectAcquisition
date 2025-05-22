import subprocess

from django.views.decorators.http import require_http_methods
from moviepy import VideoFileClip
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from django.core.files import File

from .forms import LoginForm, RegisterForm
from .models import Video

import os


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    form = LoginForm(request.POST or None)
    message = ''

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user_obj = User.objects.filter(email=email).first()

            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('welcome')
                else:
                    message = 'Email ou mot de passe incorrect.'
            else:
                message = "Aucun utilisateur avec cet email."

    return render(request, 'accounts/login.html', {'form': form, 'message': message})


GRID_VOCAB = {
    'fr': {
        'structure': 'Commande + Couleur + Préposition + Lettre + Chiffre + Adverbe',
        'commande': ['mettre', 'placer', 'déposer', 'poser'],
        'couleur': ['bleu', 'vert', 'rouge', 'blanc'],
        'préposition': ['à', 'près de', 'dans', 'avec'],
        'lettre': ['de A à Z (sans W)'],
        'chiffre': 'de 1 à 9',
        'adverbe': ['encore', 'maintenant', 's’il vous plaît', 'bientôt']
    },
    'en': {
        'structure': 'Command + Colour + Preposition + Letter + Digit + Adverb',
        'commande': ['bin', 'lay', 'place', 'set'],
        'couleur': ['blue', 'green', 'red', 'white'],
        'préposition': ['at', 'by', 'in', 'with'],
        'lettre': ['from A to Z (excluding W)'],
        'chiffre': ['from 1 to 9'],
        'adverbe': ['again', 'now', 'please', 'soon']
    },
    'es': {
        'structure': 'Comando + Color + Preposición + Letra + Número + Adverbio',
        'commande': ['poner', 'colocar', 'dejar', 'situar'],
        'couleur': ['azul', 'verde', 'rojo', 'blanco'],
        'préposition': ['en', 'junto a', 'dentro de', 'con'],
        'lettre': ['de la A a la Z (sin la W)'],
        'chiffre': ['del 1 al 9'],
        'adverbe': ['otra vez', 'ahora', 'por favor', 'pronto']
    },
    'ar': {
        'structure': 'أمر + لون + حرف جر + حرف + رقم + ظرف',
        'commande': ['ضع', 'رتب', 'انقل', 'جهز'],
        'couleur': ['أزرق', 'أخضر', 'أحمر', 'أبيض'],
        'préposition': ['في', 'عند', 'داخل', 'مع'],
        'lettre': 'من الألف إلى الياء] ',
        'chiffre': 'من ١ إلى ٩',
        'adverbe': ['مرة أخرى', 'الآن', 'من فضلك', 'قريباً']
    }
}


@login_required
def welcome_view(request):
    if request.method == 'POST':
        selected_lang = request.POST.get('langue')
        request.session['langue'] = selected_lang
        return redirect('home')

    return render(request, 'accounts/welcome.html')


from django.shortcuts import redirect

def root_redirect_view(request):
    return redirect('login')


# ============================
#  Interface principale
# ============================

@login_required
def home(request):
    langue = request.session.get('langue', 'fr')
    vocabulaire = GRID_VOCAB.get(langue)

    # Récupère les vidéos détectées de l'utilisateur connecté uniquement
    detected_videos = Video.objects.filter(is_detected=True).order_by('-uploaded_at')

    return render(request, 'accounts/home.html', {
        'vocabulaire': vocabulaire,
        'langue': langue,
        'detected_videos': detected_videos,
    })
# ============================
#  Upload & Détection des lèvres
# ============================

@csrf_exempt
def upload_video(request):

    if request.method == 'POST' and request.FILES.get('video'):
        video_file = request.FILES['video']
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_videos')
        os.makedirs(temp_dir, exist_ok=True)

        print("✔️ Fichier reçu :", request.FILES)

        # On force le nom du fichier pour être 'video.webm'
        filename = 'video.webm'
        save_path = os.path.join(temp_dir, filename)

        with open(save_path, 'wb+') as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'message': 'Vidéo temporairement uploadée.',
            'filename': filename,
            'temp_path': f'temp_videos/{filename}'
        })

    return JsonResponse({'error': 'Aucun fichier vidéo envoyé.'}, status=400)


from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


@csrf_exempt
@login_required
def detect_lips(request):
    import uuid
    import cv2
    import mediapipe as mp
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    try:
        temp_path = request.POST.get('temp_path')
        if not temp_path:
            return JsonResponse({'error': 'Chemin temporaire non fourni.'}, status=400)

        input_path = os.path.join(settings.MEDIA_ROOT, temp_path)
        if not os.path.exists(input_path):
            return JsonResponse({'error': 'Fichier vidéo temporaire introuvable.'}, status=404)

        output_folder = os.path.join(settings.MEDIA_ROOT, 'videos')
        os.makedirs(output_folder, exist_ok=True)

        output_filename = f'lips_cropped_{uuid.uuid4().hex[:8]}.webm'
        output_path = os.path.join(output_folder, output_filename)

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return JsonResponse({'error': 'Impossible d’ouvrir la vidéo.'}, status=500)

        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False)

        fps = cap.get(cv2.CAP_PROP_FPS)
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        LIPS_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
                        291, 308, 324, 318, 402, 317, 14, 87, 178, 88,
                        95, 185, 40, 39, 37, 0, 267, 269, 270, 409,
                        415, 310, 311, 312, 13, 82, 81, 42, 183, 78]

        lips_detected_total = 0
        frame_count = 0

        cropped_frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)

            if result.multi_face_landmarks:
                for face_landmark in result.multi_face_landmarks:
                    xs, ys = [], []
                    points = []

                    for idx in LIPS_INDICES:
                        pt = face_landmark.landmark[idx]
                        x = int(pt.x * video_width)
                        y = int(pt.y * video_height)
                        xs.append(x)
                        ys.append(y)
                        points.append((x, y))

                    # Définir la zone à recadrer
                    #  Étendre davantage la zone autour de la bouche
                    extra_margin_x = 70  # Largeur supplémentaire (gauche/droite)
                    extra_margin_y = 75  # Hauteur supplémentaire (haut/bas)

                    x_center = (min(xs) + max(xs)) // 2
                    y_center = (min(ys) + max(ys)) // 2

                    x_min = max(x_center - extra_margin_x, 0)
                    x_max = min(x_center + extra_margin_x, video_width)
                    y_min = max(y_center - extra_margin_y, 0)
                    y_max = min(y_center + extra_margin_y, video_height)

                    # Recadrer autour de la bouche
                    cropped_frame = frame[y_min:y_max, x_min:x_max]

                    # Redessiner les landmarks dans le frame recadré
                    for x, y in points:
                        # Adapter les coordonnées au crop
                        x_rel = x - x_min
                        y_rel = y - y_min
                        cv2.circle(cropped_frame, (x_rel, y_rel), 2, (0, 255, 0), -1)

                    #  Redimension facultatif
                    cropped_frame = cv2.resize(cropped_frame, (224, 224))

                    cropped_frames.append(cropped_frame)
                    lips_detected_total += 1
                    break

            frame_count += 1

        cap.release()

        # Enregistrement de la vidéo recadrée
        if not cropped_frames:
            return JsonResponse({'error': 'Aucune bouche détectée.'}, status=400)

        fixed_width, fixed_height = 224, 224
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'VP80'), fps, (fixed_width, fixed_height))
        for cropped in cropped_frames:
            out.write(cropped)
        out.release()

        # Fusionner l’audio original
        final_output_path = output_path.replace('.webm', '_with_audio.webm')
        subprocess.run([
            'ffmpeg', '-y',
            '-i', output_path,
            '-i', input_path,
            '-c', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            final_output_path
        ], check=True)

        # Transcription
        clip = VideoFileClip(final_output_path)
        audio_path = final_output_path.replace('.webm', '.wav')
        clip.audio.write_audiofile(audio_path, codec='pcm_s16le')
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        simple_transcription = result["text"].strip()

        # ✅ Génération GRID
        grid_lines = []

        first_word = result["segments"][0]["words"][0]
        start_ms = int(first_word["start"] * 1000)
        if start_ms > 10:
            grid_lines.append(f"0 {start_ms} sil")
        else:
            grid_lines.append(f"0 {start_ms + 10} sil")

        for segment in result["segments"]:
            for word in segment["words"]:
                content = word["word"].strip().lower()
                if not content:
                    continue
                start = int(word["start"] * 1000)
                end = int(word["end"] * 1000)
                grid_lines.append(f"{start} {end} {content}")

        last_word = result["segments"][-1]["words"][-1]
        final_end_ms = int(last_word["end"] * 1000)
        audio_duration_ms = int(clip.duration * 1000)
        if final_end_ms < audio_duration_ms:
            grid_lines.append(f"{final_end_ms} {audio_duration_ms} sil")
        else:
            grid_lines.append(f"{final_end_ms} {final_end_ms + 500} sil")

        grid_path = final_output_path.replace('.webm', '_grid.txt')
        with open(grid_path, 'w') as f:
            for i, line in enumerate(grid_lines):
                if i < len(grid_lines) - 1:
                    f.write(line + "|\n")
                else:
                    f.write(line + "\n")

        # ✅ Génération VTT
        vtt_path = final_output_path.replace('.webm', '+align.vtt')

        # Utilisation d'un encodage UTF-8
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")  # Ajout de l'en-tête WEBVTT

            def format_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                ms = int((seconds - int(seconds)) * 1000)
                return f"{h:02}:{m:02}:{s:02}.{ms:03}"

            # Ajout des segments de sous-titres
            for segment in result["segments"]:
                for word in segment.get("words", []):
                    word_text = word["word"].strip()
                    if not word_text:
                        continue

                    start = word["start"]
                    end = word["end"]

                    if start < 0 or end <= start:
                        continue

                    # Ajouter chaque sous-titre avec son temps
                    f.write(f"{format_time(start)} --> {format_time(end)}\n")
                    f.write(f"{word_text}\n\n")

            f.write("END\n")  # Ajouter la fin (END) sans timestamp

        # Sauvegarde DB
        with open(final_output_path, 'rb') as video_file, \
                open(grid_path, 'rb') as transcript_file, \
                open(vtt_path, 'rb') as vtt_file,\
                open(audio_path, 'rb') as audio_file:

            detected_video = Video.objects.create(
                video_file=File(video_file, name=os.path.basename(final_output_path)),
                is_detected=True
            )
            detected_video.transcription.save(os.path.basename(grid_path), File(transcript_file))
            detected_video.audio_file.save(os.path.basename(audio_path), File(audio_file))
            detected_video.subtitles_file.save(os.path.basename(vtt_path), File(vtt_file))
            detected_video.save()

        return JsonResponse({
            'message': f'Détection des lèvres et recadrage terminés ({frame_count} frames).',
            'lèvres_detectées': lips_detected_total,
            'output_video': detected_video.video_file.url,
            'video_id': detected_video.id,
            'sous_titres': simple_transcription
        })

    except Exception as e:
        import traceback
        print("❌ Erreur complète :", traceback.format_exc())
        return JsonResponse({'error': 'Erreur lors de la détection des lèvres.'}, status=500)


# ============================
#  Suppression vidéo
# ============================

@login_required
def delete_video(request, video_id):
    if request.method == 'POST':
        video = get_object_or_404(Video, id=video_id)
        video.video_file.delete(save=False)
        video.delete()
    return redirect('home')



@login_required
@require_http_methods(["GET", "POST"])
def edit_transcription(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    transcription_path = video.transcription.path if video.transcription else None
    transcription_lines = []

    if transcription_path and os.path.exists(transcription_path):
        with open(transcription_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    start, end = parts[0], parts[1]
                    word = " ".join(parts[2:]).replace('|', '')  # enlever le pipe
                    transcription_lines.append({'start': start, 'end': end, 'word': word})

    if request.method == "POST":
        updated_lines = []
        count = int(request.POST.get("line_count", 0))

        for i in range(count):
            start = request.POST.get(f"start_{i}")
            end = request.POST.get(f"end_{i}")
            word = request.POST.get(f"word_{i}", "").strip().lower()
            updated_lines.append(f"{start} {end} {word}")

        with open(transcription_path, 'w', encoding='utf-8') as f:
            for i, line in enumerate(updated_lines):
                if i < len(updated_lines) - 1:
                    f.write(line + "|\n")
                else:
                    f.write(line + "\n")

        return redirect('home')

    return render(request, 'accounts/edit_transcription.html', {
        'video': video,
        'transcription': transcription_lines
    })
