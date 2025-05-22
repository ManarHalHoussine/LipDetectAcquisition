window.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('webcam');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const indicator = document.getElementById('recordingIndicator');
    const timer = document.getElementById('recordingTime');
    const videosList = document.getElementById('videosList');
    const loader = document.getElementById('loader');
    const notification = document.getElementById('notification');
    const overlayCanvas = document.getElementById('overlayCanvas');
    const overlayCtx = overlayCanvas.getContext('2d');

    let mediaRecorder, recordedChunks = [], stream, timerInterval, startTime;

    async function startWebcam() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
                audio: true
            });
            video.srcObject = stream;

            video.addEventListener('loadedmetadata', () => {
                overlayCanvas.width = video.videoWidth;
                overlayCanvas.height = video.videoHeight;
            });

            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => e.data.size > 0 && recordedChunks.push(e.data);
            mediaRecorder.onstop = handleStop;

            startBtn.onclick = () => {
                mediaRecorder.start();
                startBtn.disabled = true;
                stopBtn.disabled = false;
                indicator.style.display = 'flex';
                startTime = Date.now();
                timerInterval = setInterval(updateTimer, 1000);
            };

            stopBtn.onclick = () => {
                mediaRecorder.stop();
                startBtn.disabled = false;
                stopBtn.disabled = true;
                indicator.style.display = 'none';
                clearInterval(timerInterval);
                timer.textContent = "00:00";
            };

            setupFaceMesh();

        } catch (err) {
            alert('Impossible d’accéder à la webcam.');
            console.error(err);
        }
    }

    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const seconds = String(elapsed % 60).padStart(2, '0');
        timer.textContent = `${minutes}:${seconds}`;
    }

    function handleStop() {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const preview = document.createElement('video');
        preview.src = url;
        preview.controls = true;
        preview.width = 320;
        preview.height = 240;
        videosList.appendChild(preview);
        uploadAndDetect(blob);
        recordedChunks = [];
    }

    function showLoader(message) {
        loader.style.display = 'block';
        notification.innerText = message;
        notification.style.display = 'block';
    }

    function hideLoader() {
        loader.style.display = 'none';
        notification.style.display = 'none';
    }

    function uploadAndDetect(blob) {
        const formData = new FormData();
        formData.append('video', blob);

        showLoader("📤 Envoi de la vidéo...");

        fetch('/upload/', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            console.log("✅ Upload réussi :", data);
            showLoader("🛠️ Détection en cours...");
            return detectLips(data.temp_path);
        })
        .then(resp => resp.json())
        .then(result => {
            console.log("✅ Résultat détection :", result);
            if (result.success && result.data) {
                const { prediction, confidence } = result.data;
                notification.innerHTML = `🗣️ Mot détecté : <b>${prediction}</b> (confiance : ${Math.round(confidence * 100)}%)`;
                notification.style.display = 'block';
            } else {
                notification.innerText = "⚠️ Aucun résultat détecté.";
                notification.style.display = 'block';
                console.warn("Réponse vide ou incomplète :", result);
            }
        })
        .catch(err => {
            console.error("❌ Erreur :", err);
            alert(err.message || "Erreur pendant le processus.");
        })
        .finally(() => hideLoader());
    }

    function detectLips(tempPath) {
        const formData = new FormData();
        formData.append('temp_path', tempPath);

        return fetch('/detect_lips/', {
            method: 'POST',
            body: formData
        });
    }

    function setupFaceMesh() {
        const faceMesh = new FaceMesh({
            locateFile: file => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
        });

        faceMesh.setOptions({
            maxNumFaces: 1,
            refineLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });

        faceMesh.onResults(onResults);

        const camera = new Camera(video, {
            onFrame: async () => {
                await faceMesh.send({ image: video });
            },
            width: 640,
            height: 480
        });

        camera.start();
    }

    function onResults(results) {
        overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            const landmarks = results.multiFaceLandmarks[0];
            const lipIndices = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183, 78];

            const lipPoints = lipIndices.map(i => landmarks[i]);
            const xCoords = lipPoints.map(p => p.x * overlayCanvas.width);
            const yCoords = lipPoints.map(p => p.y * overlayCanvas.height);

            const xMin = Math.min(...xCoords);
            const xMax = Math.max(...xCoords);
            const yMin = Math.min(...yCoords);
            const yMax = Math.max(...yCoords);

            overlayCtx.strokeStyle = 'red';
            overlayCtx.lineWidth = 2;
            overlayCtx.strokeRect(xMin, yMin, xMax - xMin, yMax - yMin);
        }
    }

    startWebcam();
});
