#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# daily-intel Oracle Cloud Always Free — automated VM setup script
# Run this ONCE after SSH-ing into your Oracle VM.
# Usage: bash oracle_setup.sh
# ─────────────────────────────────────────────────────────────────
set -e

echo "=== daily-intel Oracle Cloud Setup ==="

# 1. System dependencies
sudo apt-get update -q
sudo apt-get install -y python3.11 python3.11-venv python3-pip git curl unzip

# 2. Clone repo (replace with your GitHub URL after pushing)
REPO_URL="https://github.com/jeffwatson/daily-intel.git"
INSTALL_DIR="$HOME/daily-intel"

if [ -d "$INSTALL_DIR" ]; then
  echo "Repo already exists at $INSTALL_DIR — pulling latest..."
  cd "$INSTALL_DIR" && git pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# 3. Python virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. Create .env from example (you fill in secrets)
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
  echo ""
  echo "⚠️  .env created. Fill in your secrets:"
  echo "   nano $INSTALL_DIR/.env"
  echo ""
fi

# 5. Create logs directory
mkdir -p "$INSTALL_DIR/logs"

# 6. Install systemd service
sudo tee /etc/systemd/system/daily-intel.service > /dev/null <<EOF
[Unit]
Description=daily-intel Intelligence Digest Scheduler
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=on-failure
RestartSec=30
StandardOutput=append:$INSTALL_DIR/logs/scheduler.log
StandardError=append:$INSTALL_DIR/logs/scheduler.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable daily-intel

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in your secrets:  nano $INSTALL_DIR/.env"
echo "  2. Test a dry run:        cd $INSTALL_DIR && source venv/bin/activate && python main.py --now daily --dry"
echo "  3. Send a real digest:    python main.py --now daily"
echo "  4. Start the scheduler:   sudo systemctl start daily-intel"
echo "  5. Check logs:            tail -f $INSTALL_DIR/logs/scheduler.log"
echo "  6. Check status:          sudo systemctl status daily-intel"
