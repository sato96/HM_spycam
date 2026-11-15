# HM_spycam 📷

HM_spycam is a microservice of the **HomeManager** ecosystem that monitors an environment with a Raspberry Pi camera (Picamera2). It detects motion, records a short video when motion is found, and publishes a notification to the [HM_notifier](https://github.com/sato96/HM_notifier) service via MQTT.

## Features ✅

- Serve still images via HTTP (`/pic`) as Base64 in JSON
- Start/stop motion monitoring (`/start`, `/stop`)
- Tune detection parameters at runtime (`/tresh`) and read them back (`/parameters`)
- Reload `config.json` without restarting (`/reload`)
- Robust motion detection: immune to global brightness changes (auto-exposure, sunlight), with optional ignored regions
- MQTT alerts to HM_notifier when a video has been recorded

## Requirements ⚙️

- Raspberry Pi with libcamera and Picamera2 support
- Python 3.9+ (`install.sh` creates a venv with system site packages)
- System packages: `python3-picamera2`, `libcap-dev`, `logrotate` (installed by `install.sh`) and `ffmpeg` (used by Picamera2 to write the mp4; install it if missing: `sudo apt install ffmpeg`)
- A configuration file: `config/config.json`

## Install ▶️

From the project root:

```bash
chmod +x install.sh
./install.sh
```

The script:

1. installs system dependencies,
2. creates a Python virtualenv and installs `requirements.txt`,
3. creates the `logs/` and `video/` folders,
4. registers the logrotate configuration.

Then create your configuration from the template:

```bash
cp config/config_template.json config/config.json
nano config/config.json
```

## Configuration — `config/config.json` 🔧

```json
{
    "port": 5004,
    "service": "cameraModule",
    "url": "mqtt://<yourMQTTBroker>:1883",
    "topic": "/yourTopic",
    "status": "on",
    "flipImg": true,
    "colorScheme": "BW",
    "timeSleep": 0.1,

    "threshold": 25,
    "areaPct": 1.5,
    "minFrames": 2,
    "ignoreRegions": []
}
```

| Key | Description |
|---|---|
| `port` | HTTP port of the service (default `5004`, can be overridden with the `PORT` environment variable) |
| `service` | Service code used by orchestrator and notifier |
| `url` | MQTT broker URL (e.g. `mqtt://localhost:1883`) |
| `topic` | MQTT topic for notifications |
| `status` | `on` / `off`: whether monitoring is active. Written automatically by `/start` (`on`) and `/stop` (`off`); if `on` at startup the service resumes monitoring by itself (see below). Defaults to `off` if missing |
| `flipImg` | Vertically flip the image (camera mounted upside down) |
| `colorScheme` | `RGB` or `BW` for the images returned by `/pic` |
| `timeSleep` | Seconds between two analysed frames (default `0.1`) |
| `threshold` | Per-pixel brightness difference (0–255) above which a pixel counts as "changed" |
| `areaPct` | Minimum % of changed pixels (inside the monitored area) to count as motion |
| `minFrames` | Consecutive frames above `areaPct` required to start recording |
| `ignoreRegions` | List of rectangles `[x0, y0, x1, y1]` to exclude from detection (see below) |

### Automatic resume after a crash or reboot 🔁

`status` is persisted in `config.json` and acts as the "desired state" of the monitoring:

- `POST /start` writes `"status": "on"`, `POST /stop` writes `"status": "off"`.
- When the service starts, if `status` is `on` it begins monitoring immediately, without waiting for a `/start` call.
- If the process dies unexpectedly (crash, power loss, reboot) `status` stays `on`, so with `Restart=always` in the systemd unit the house goes back under monitoring on its own.
- If `status` is `off` (or missing) the service starts idle: call `POST /start` to begin.

> The service rewrites `config.json` on `/start`, `/stop` and `/tresh`; the other keys are preserved.

### How motion detection works 🧠

For every analysed frame (320×240 luminance plane) the service:

1. averages it over 4×4 blocks (80×60) to suppress sensor noise;
2. subtracts the mean brightness, so global changes (auto-exposure, clouds, sunlight through a window) do not matter;
3. compares it with the previous frame and computes the **percentage of pixels** that changed by more than `threshold`;
4. starts recording only if that percentage exceeds `areaPct` for `minFrames` consecutive frames.

> ⚠️ **Upgrading from previous versions:** `threshold` used to be an MSE value (default `7`); it is now a per-pixel difference. Use a value around `25` and tune from there.

**Tuning tips**

- Too many false positives → raise `threshold` (e.g. 30–40), raise `areaPct`, or set `minFrames` to 3.
- Small or distant subjects not detected → lower `areaPct` to 0.5–1.
- A bright window or a screen keeps triggering → add it to `ignoreRegions`.

### Ignored regions

Coordinates refer to the 320×240 detection frame, which covers the whole field of view of the camera. If you measure a point on the full 1280×720 image returned by `/pic`, convert it with `x / 4` and `y / 3`. For example, to ignore a window in the right part of the image:

```json
"ignoreRegions": [[210, 0, 255, 125], [210, 135, 250, 185]]
```

Apply changes with `POST /reload` (or restart the service). Note that `/reload` re-reads `status` too.

## Running the service 🏃‍♂️

**Development**

```bash
./run.sh
```

**Systemd (recommended)**

Edit `HM_spycam.service` (paths and user, and optionally environment variables such as `PORT`), then:

```bash
sudo cp HM_spycam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now HM_spycam.service
```

Logs are written to `logs/HM_spycam.log` (rotated via `logrotate.conf`):

```bash
tail -f logs/HM_spycam.log
```

Recorded videos are saved in `video/` (`video/motion.mp4`).

## HTTP API — Endpoints & examples 🧭

All responses use the `MsgResponse` wrapper (`status: "ok" | "ko"`).

### `GET /pic`

Returns JSON with `img_base64` (Base64-encoded JPEG). Save it as a file:

```bash
curl -s http://<pi>:5004/pic | python3 -c "import sys,json,base64; open('pic.jpg','wb').write(base64.b64decode(json.load(sys.stdin)['img_base64']))"
```

### `GET /parameters`

Returns the whole content of `config.json` plus the software `version`, as a single JSON object. The same object is returned both in `data` (where structured data belongs) and in `response` (kept for the current hub):

```json
{
  "status": "ok",
  "data":     { "threshold": 25, "areaPct": 1.5, "status": "on", "url": "mqtt://...", "topic": "/...", "version": "0.2.0" },
  "response": { "threshold": 25, "areaPct": 1.5, "status": "on", "url": "mqtt://...", "topic": "/...", "version": "0.2.0" }
}
```

On error the HTTP status is `500`, `status` is `ko`, `data` is `{}` and `response` is the error message.

The version comes from `__version__` in `src/__init__.py` (not from `config.json`), so it always matches the code that is actually running. If the file contains a `version` key it is overridden by the real one. Keys missing from the file (e.g. optional parameters left at their defaults) are not listed.

> ⚠️ The whole file is returned as is: do not put credentials in `url` (or any other key), or `/parameters` will expose them.

### `POST /start`

Start motion detection.

### `POST` or `GET /stop`

Stop detection/recording.

### `POST /tresh`

Set the detection threshold at runtime (use `"default"` to restore the default value):

```bash
curl -X POST http://<pi>:5004/tresh -d '{"threshold": 30}'
```

### `POST /reload`

Reload `config.json` (including `areaPct`, `minFrames`, `ignoreRegions`).

## Integration with HM_notifier 🔗

When the camera records a video after a motion detection, the service publishes a notification (video info) to the configured MQTT `url` and `topic`. [HM_notifier](https://github.com/sato96/HM_notifier) handles the published message.

Make sure that:

- `config.json` has the correct `url` and `topic`;
- `service` matches the orchestrator/notifier configuration.

## Troubleshooting & tips 💡

- **Picamera2 import fails** → install the Pi camera system packages: `sudo apt install python3-picamera2 libcamera-* ffmpeg`
- **Monitoring does not resume after a restart** → check that `"status": "on"` is set in `config.json` (a manual `/stop` sets it to `off` on purpose)
- **Check the logs** → `tail -f logs/HM_spycam.log` (the systemd unit redirects output to this file, so `journalctl` will be empty)
- **False positives** → look at the recorded video: if the scene is static and the brightness drifts, raise `threshold`/`areaPct`, mask bright areas with `ignoreRegions`, or increase `minFrames`
- `/pic` returns a Base64 JPEG; for lower bandwidth, consider returning raw image bytes with the proper mimetype

## Versioning 🏷️

The project follows [Semantic Versioning](https://semver.org/). The single source of truth is `__version__` in `src/__init__.py`, and each release is tagged on git with the same number (no `v` prefix, e.g. `0.2.0`). Before tagging a release, bump `__version__` and commit it.

## License & notes ⚖️

Part of the HomeManager ecosystem. See the repository for licensing details.