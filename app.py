"""
Stream Terminal Live Caption Engine
Hungarian (hu-HU) → English (en) real-time AI captions via Azure Speech Translation.

Architecture:
  Audio input (mic/line-in) → Azure Speech SDK → WebSocket → Browser (fullscreen captions)

Usage:
  1. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION env vars
  2. pip install -r requirements.txt
  3. python app.py
  4. Open http://localhost:5000 in Chrome, go fullscreen, HDMI to TV

Event-day audio chain:
  Sound mixer line-out → USB audio interface → Laptop (default input device)
"""

import os
import sys
import threading
import time
from datetime import datetime

# ─── Load .env file (if present) ────────────────────────────────────────────
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Azure Speech SDK
try:
    import azure.cognitiveservices.speech as speechsdk
    from azure.cognitiveservices.speech.translation import SpeechTranslationConfig
except ImportError:
    print("ERROR: azure-cognitiveservices-speech not installed.")
    print("Run: pip install azure-cognitiveservices-speech")
    sys.exit(1)

# ─── Config ─────────────────────────────────────────────────────────────────
AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "").strip()
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "westeurope").strip()
SOURCE_LANG = os.environ.get("SOURCE_LANG", "hu-HU").strip()
TARGET_LANG = os.environ.get("TARGET_LANG", "en").strip()
LISTEN_PORT = int(os.environ.get("PORT", 5000))

# Set MOCK_MODE=1 to test the caption UI without Azure credentials
MOCK_MODE = os.environ.get("MOCK_MODE", "").strip() in ("1", "true", "yes", "on")

if not AZURE_KEY and not MOCK_MODE:
    print("ERROR: Set AZURE_SPEECH_KEY environment variable.")
    print("       Or set MOCK_MODE=1 to test the UI without Azure.")
    print("Get key from: Azure Portal → Speech Services → Keys and Endpoint")
    sys.exit(1)

# ─── Flask + SocketIO ───────────────────────────────────────────────────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Audio device selection
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    sd = None
    HAS_SOUNDDEVICE = False

_SELECTED_DEVICE_NAME = None  # set by /api/select-device

# ─── Caption state ──────────────────────────────────────────────────────────
_latest_caption = {"text": "", "final": False, "timestamp": ""}
_caption_lock = threading.Lock()

# ─── Azure Speech Translation Worker ────────────────────────────────────────
def run_translation():
    """Continuously stream audio to Azure, push captions via WebSocket."""
    if MOCK_MODE:
        run_mock_translation()
        return

    speech_config = SpeechTranslationConfig(
        subscription=AZURE_KEY,
        region=AZURE_REGION,
    )
    speech_config.speech_recognition_language = SOURCE_LANG
    speech_config.add_target_language(TARGET_LANG)

    # Optional: request word-level timestamps, profanity filter, etc.
    # speech_config.request_word_level_timestamps()

    # Use default microphone (or whatever the OS default input device is).
    # On event day, set the USB audio interface from the mixer as default.
    global _SELECTED_DEVICE_NAME
    if _SELECTED_DEVICE_NAME:
        audio_config = speechsdk.audio.AudioConfig(device_name=_SELECTED_DEVICE_NAME)
        print(f"[Engine] Using selected audio device: {_SELECTED_DEVICE_NAME}")
    else:
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        print("[Engine] Using default microphone")

    try:
        translator = speechsdk.translation.TranslationRecognizer(
            translation_config=speech_config,
            audio_config=audio_config,
        )
    except RuntimeError as exc:
        err_msg = str(exc)
        if "SPXERR_MIC_NOT_AVAILABLE" in err_msg or "MIC_NOT_AVAILABLE" in err_msg:
            print("[Engine] ERROR: No microphone detected on this machine.")
            print("[Engine] This is expected on headless servers. Connect an audio")
            print("[Engine] input device (USB audio interface from mixer) to use Azure.")
            socketio.emit("status", {
                "message": "No microphone — connect audio input device",
                "level": "error"
            })
        else:
            print(f"[Engine] ERROR: {err_msg}")
            socketio.emit("status", {"message": f"Azure error: {err_msg}", "level": "error"})
        return

    def on_recognizing(evt):
        """Interim (partial) results — update live caption."""
        text = evt.result.translations.get(TARGET_LANG, "")
        if text:
            with _caption_lock:
                _latest_caption["text"] = text
                _latest_caption["final"] = False
                _latest_caption["timestamp"] = datetime.now().isoformat()
            socketio.emit("caption_update", _latest_caption)

    def on_recognized(evt):
        """Final confirmed results — commit to display."""
        text = evt.result.translations.get(TARGET_LANG, "")
        if text:
            with _caption_lock:
                _latest_caption["text"] = text
                _latest_caption["final"] = True
                _latest_caption["timestamp"] = datetime.now().isoformat()
            socketio.emit("caption_commit", _latest_caption)

    def on_canceled(evt):
        print(f"[Azure] Canceled: {evt}")
        socketio.emit("status", {"message": "Translation stopped or error", "level": "error"})

    def on_session_started(evt):
        print("[Azure] Session started")
        socketio.emit("status", {"message": "Translation active", "level": "ok"})

    def on_session_stopped(evt):
        print("[Azure] Session stopped")
        socketio.emit("status", {"message": "Translation stopped", "level": "warn"})

    translator.recognizing.connect(on_recognizing)
    translator.recognized.connect(on_recognized)
    translator.session_started.connect(on_session_started)
    translator.session_stopped.connect(on_session_stopped)
    translator.canceled.connect(on_canceled)

    print(f"[Engine] Starting Azure translation: {SOURCE_LANG} → {TARGET_LANG}")
    print(f"[Engine] Region: {AZURE_REGION} | Listening on default audio input")

    # Continuous recognition
    translator.start_continuous_recognition()

    # Keep thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        translator.stop_continuous_recognition()


def run_mock_translation():
    """Simulate Azure captions for UI testing without credentials."""
    print("[Engine] MOCK MODE — simulating Hungarian → English captions")
    print("[Engine] No Azure credentials needed. UI testing only.\n")
    socketio.emit("status", {"message": "MOCK MODE — simulated captions", "level": "warn"})

    # Simulated English captions that would come from Hungarian speech
    mock_phrases = [
        "Welcome everyone to today's conference",
        "We are going to discuss streaming technology",
        "Our platform enables real-time video delivery",
        "This is a demonstration of AI-powered translation",
        "The future of live events is here",
        "Thank you all for attending today",
        "Please feel free to ask questions",
        "We are now opening the floor for discussion",
        "This technology supports many languages",
        "Stream Terminal makes it possible",
    ]

    idx = 0
    while True:
        phrase = mock_phrases[idx % len(mock_phrases)]
        # Simulate interim (partial) text
        words = phrase.split()
        for i in range(1, len(words) + 1):
            partial = " ".join(words[:i])
            with _caption_lock:
                _latest_caption["text"] = partial
                _latest_caption["final"] = False
                _latest_caption["timestamp"] = datetime.now().isoformat()
            socketio.emit("caption_update", _latest_caption)
            time.sleep(0.25)

        # Emit final
        with _caption_lock:
            _latest_caption["text"] = phrase
            _latest_caption["final"] = True
            _latest_caption["timestamp"] = datetime.now().isoformat()
        socketio.emit("caption_commit", _latest_caption)

        time.sleep(2.5)
        idx += 1

# ─── HTTP Routes ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("captions.html")

@app.route("/setup")
def setup_page():
    return render_template("setup.html")

@app.route("/health")
def health():
    return {
        "status": "ok",
        "source": SOURCE_LANG,
        "target": TARGET_LANG,
        "region": AZURE_REGION,
        "mock": MOCK_MODE
    }

@app.route("/api/audio-devices")
def list_audio_devices():
    """List all available audio input devices for the UI selector."""
    if not HAS_SOUNDDEVICE:
        return {"available": False, "devices": [], "error": "sounddevice not installed"}
    try:
        devices = []
        for d in sd.query_devices():
            if d["max_input_channels"] > 0:
                devices.append({
                    "index": d["index"],
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                    "selected": d["name"] == _SELECTED_DEVICE_NAME
                })
        return {"available": True, "devices": devices, "selected": _SELECTED_DEVICE_NAME}
    except Exception as exc:
        return {"available": False, "devices": [], "error": str(exc)}

@app.route("/api/select-device", methods=["POST"])
def select_device():
    """Select an audio input device by name. Requires app restart to take effect."""
    global _SELECTED_DEVICE_NAME
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return {"success": False, "error": "Missing 'name' field"}, 400
    _SELECTED_DEVICE_NAME = name
    return {"success": True, "selected": name, "note": "Restart app to activate the selected device"}

@app.route("/api/clear-device", methods=["POST"])
def clear_device():
    """Clear device selection and revert to default microphone."""
    global _SELECTED_DEVICE_NAME
    _SELECTED_DEVICE_NAME = None
    return {"success": True, "selected": None, "note": "Restart app to revert to default microphone"}

# ─── WebSocket Events ───────────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    print("[Client] Connected")
    emit("status", {"message": "Connected to caption server", "level": "ok"})
    # Send latest known caption immediately so screen isn't blank
    with _caption_lock:
        emit("caption_commit", _latest_caption)

@socketio.on("disconnect")
def on_disconnect():
    print("[Client] Disconnected")

# ─── Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start Azure translation in a background thread
    t = threading.Thread(target=run_translation, daemon=True)
    t.start()

    # Give Azure a moment to initialize before serving HTTP
    time.sleep(1)

    print(f"[Server] Caption display: http://localhost:{LISTEN_PORT}/")
    print(f"[Server] Health check:    http://localhost:{LISTEN_PORT}/health")
    print("[Server] Press Ctrl+C to stop\n")

    # Run Flask — threaded so WebSocket + HTTP coexist
    socketio.run(app, host="0.0.0.0", port=LISTEN_PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
