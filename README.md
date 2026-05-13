# Stream Terminal — Live Captions

Real-time AI speech-to-text + translation (Hungarian → English) via Azure Speech Services, with a fullscreen browser caption display for physical events.

## Architecture

```
Sound mixer line-out → USB audio interface → Laptop (default mic)
                                    ↓
                        Azure Speech Translation (STT + MT)
                                    ↓
                         WebSocket → Browser (fullscreen)
                                    ↓
                              HDMI out → TV / projector
```

## Quick Start

1. **Clone & enter the repo**

   ```bash
   git clone https://github.com/stokesbot/stream-terminal-live-caption.git
   cd stream-terminal-live-caption
   ```

2. **Create virtual environment** (Ubuntu / Debian blocks system pip)

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Azure credentials**

   Copy `.env.example` to `.env` and fill in your Azure Speech key:

   ```bash
   cp .env.example .env
   nano .env
   ```

4. **Run**

   ```bash
   # Live Azure mode (needs mic + internet + Azure key)
   python app.py

   # OR — mock mode for UI testing without Azure
   MOCK_MODE=1 python app.py
   ```

5. **Open browser**

   - **Caption display**: `http://localhost:5000/` — click to auto-fullscreen, press **F** to toggle
   - **Setup / audio device selector**: `http://localhost:5000/setup`
   - **Health check**: `http://localhost:5000/health`

## Pages

| Page | Route | Description |
|---|---|---|
| Caption Display | `/` | Fullscreen black page with large white captions. Two-line layout: previous (dimmed) + current (bright). Interim results shown in yellow. |
| Setup | `/setup` | Audio input device selector, system status, quick links. Dark theme matching the caption display. |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | JSON status (`source`, `target`, `region`, `mock`) |
| `/api/audio-devices` | GET | List all detected audio input devices |
| `/api/select-device` | POST | Select a device by name. Body: `{"name": "Device Name"}`. Restart app to activate. |
| `/api/clear-device` | POST | Revert to default microphone. Restart app to activate. |

## Event-Day Audio Chain

1. Connect **mixer line-out** → **USB audio interface** → **laptop**
2. Open `http://localhost:5000/setup`
3. Click **Refresh List** — your USB interface should appear
4. Click **Select** on the right device
5. **Restart the app**
6. Open `http://localhost:5000/` → click for fullscreen → HDMI to TV
7. Do a 30-second Hungarian speech test. English captions should appear within ~1 second.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AZURE_SPEECH_KEY` | Yes (unless MOCK_MODE) | — | Azure Speech Services Key 1 |
| `AZURE_SPEECH_REGION` | No | `westeurope` | Azure region (closest to venue) |
| `SOURCE_LANG` | No | `hu-HU` | Source language code |
| `TARGET_LANG` | No | `en` | Target language code |
| `MOCK_MODE` | No | — | Set to `1` for simulated captions (no Azure needed) |
| `PORT` | No | `5000` | HTTP server port |

## Tech Stack

- **Python 3.10+**
- **Flask + Flask-SocketIO** — HTTP + WebSocket server
- **Azure Speech SDK** — Speech Translation (STT + MT in one call)
- **sounddevice** — Cross-platform audio device enumeration
- **libportaudio2** — System dependency for `sounddevice` (install via `apt`)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `externally-managed-environment` | Use a virtual environment (see Quick Start step 2) |
| `SPXERR_MIC_NOT_AVAILABLE` | Connect a USB audio interface or microphone, then refresh `/setup` |
| No captions appear | Check that the USB interface is the default recording device in OS sound settings |
| Captions too small | Adjust `.caption-line.current { font-size: 4.2vw; }` in `templates/captions.html` |
| High latency (>2s) | Pick a closer Azure region; use wired Ethernet instead of WiFi |

## License

MIT

## Credits

Built by [Stream Terminal](https://streamterminal.com) / [Geri Bofika](https://github.com/stokesbot)
