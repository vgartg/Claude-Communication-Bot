#!/usr/bin/env bash
# Pull the latest revision and restart the service. Invoked by CI over SSH.
set -euo pipefail

APP_DIR=/opt/agentbot
RUN_USER=agent

git config --global --add safe.directory "$APP_DIR" || true
cd "$APP_DIR"

git fetch --all
git reset --hard origin/main
.venv/bin/pip install -r requirements.txt
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR"

systemctl restart agentbot
sleep 2
systemctl --no-pager status agentbot | head -n 6
