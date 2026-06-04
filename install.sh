#!/bin/bash
set -e
echo "=== Instalando SST Vision ==="

apt-get update -qq && apt-get install -y -qq python3-pip python3-venv git libgl1 libglib2.0-0 libsm6 libxext6

cd /opt
[ -d sst-app ] && rm -rf sst-app
git clone -b claude/epp-review-corrections-aCTCa \
  https://github.com/sstpacheco-max/herramienta-de-posturas sst-app
cd sst-app/cv_backend

pip3 install -q -r requirements.txt

pkill -f "uvicorn main:app" 2>/dev/null || true

cat > /etc/systemd/system/sst-vision.service << 'EOF'
[Unit]
Description=SST Vision EPP
After=network.target

[Service]
WorkingDirectory=/opt/sst-app/cv_backend
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sst-vision
systemctl start sst-vision

echo ""
echo "✅ Instalación completa"
echo "🌐 App disponible en: http://$(curl -s ifconfig.me):8000"
