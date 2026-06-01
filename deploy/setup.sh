#!/usr/bin/env bash
# One-time server provisioning. Run as root.
#   REPO_URL=<git-url> bash deploy/setup.sh
#
# Prerequisite: the agent CLI referenced by AGENT_CMD must be installed and
# authenticated for the "agent" user before starting the service.
set -euo pipefail

APP_DIR=/opt/agentbot
RUN_USER=agent
REPO_URL=${REPO_URL:-https://github.com/vgartg/Claude-Communication-Bot.git}

apt-get update -y
apt-get install -y python3-venv python3-pip git curl

id "$RUN_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$RUN_USER"
sudo -u "$RUN_USER" mkdir -p "/home/$RUN_USER/workspace"

if [ ! -d "$APP_DIR/.git" ]; then
    git clone "$REPO_URL" "$APP_DIR"
fi
git config --global --add safe.directory "$APP_DIR" || true

cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
mkdir -p data

if [ ! -f "$APP_DIR/.env" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "Created $APP_DIR/.env - fill it in before starting the service."
fi

chown -R "$RUN_USER:$RUN_USER" "$APP_DIR"

install -m 644 deploy/agentbot.service /etc/systemd/system/agentbot.service
systemctl daemon-reload
systemctl enable agentbot

echo "Provisioning done. Edit $APP_DIR/.env, then: systemctl restart agentbot"
