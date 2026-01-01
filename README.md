HM_spycam is a microservice in the HomeManager ecosystem that monitors an environment using a Raspberry Pi camera (PiCamera2). It detects motion, records short videos when motion is found, and publishes notifications to the HM_notifier service via MQTT.

Features ✅
Serve still images via HTTP (/pic) as Base64 in JSON
Start/stop motion monitoring (/start, /stop)
Configure detection threshold at runtime (/tresh)
Expose current parameters (/parameters) and reload camera config (/reload)
Integrates with HM_notifier via MQTT to send alerts (video path)
Requirements & Notes ⚙️
Raspberry Pi with libcamera and Picamera2 support
Python 3.9+ (the included install.sh sets up a venv)
System packages: python3-picamera2, ffmpeg (see install.sh)
Configuration file: config.json (service, threshold, MQTT url, topic, port)
Install (recommended) ▶️
From the project root:

This script:

installs system dependencies,
creates a Python virtualenv and installs Python dependencies from requirements.txt,
creates log files and registers logrotate.
After install, update service environment variables (if needed) in the systemd service file.

Configuration — config.json 🔧
Example:

port — HTTP port for the service
service — service code used by orchestrator and notifier
threshold — motion detection threshold (numeric)
url — MQTT broker URL (e.g. mqtt://localhost:1883)
topic — MQTT topic for notifications
Running the service 🏃‍♂️
Development:
Systemd (recommended):
Edit HM_spycam.service and optionally set environment variables:
Enable & start:
Logs: HM_spycam.log (rotated via logrotate.conf).

HTTP API — Endpoints & examples 🧭
All responses use MsgResponse wrapper.

GET /pic
Returns JSON with img_base64 (Base64-encoded JPEG). Save example:

GET /parameters — current camera parameters

POST /start — start motion detection

POST/GET /stop — stop detection/recording

POST /tresh — set threshold:

POST /reload — reload camera config
Integration with HM_notifier 🔗
When the camera records a video after motion detection, the service publishes a notification (video info) to the configured MQTT url and topic. HM_notifier handles the published message. Repo: https://github.com/sato96/HM_notifier

Ensure:

config.json has correct url and topic
service matches orchestrator/notifier configuration
Troubleshooting & tips 💡
If Picamera2 imports fail, install Pi camera system packages (sudo apt install python3-picamera2 libcamera-* ffmpeg)
Follow logs: journalctl -u [HM_spycam.service](http://_vscodecontentref_/18) -f (systemd)
/pic returns Base64-encoded JPEG; if you want lower bandwidth, consider returning raw image bytes with proper mimetype
License & notes ⚖️
Part of the HomeManager ecosystem. See repository for licensing details.