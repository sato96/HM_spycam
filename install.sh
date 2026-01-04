#!/bin/bash
set -e

echo "[*] Updating packages and installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-picamera2 \
    libcap-dev \
    git \
    logrotate

echo "[*] Creating virtualenv..."
python3 -m venv venv --system-site-packages

echo "[*] Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "[*] Creating log files..."
mkdir logs
touch logs/HM_spycam.log
mkdir video
touch video/video.mp4


echo "[*] Installing logrotate configuration..."
sudo cp logrotate.conf /etc/logrotate.d/HM_spycam
sudo chown root:root /etc/logrotate.d/HM_spycam
sudo chmod 644 /etc/logrotate.d/HM_spycam

echo "[*] Installation complete!"
echo "[!] Remember to set env variables in the service file"
