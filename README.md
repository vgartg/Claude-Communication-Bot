# Communication Bot

A private Telegram bot that turns a chat into a remote control for an agent CLI
running on your own server. Send a task from anywhere; the agent works on the
host with full tool access, streams its progress back to the chat, asks
clarifying questions when needed, and reports the result. The bot only talks to
a single whitelisted account and keeps a separate, persistent thread per agent.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0)
![License](https://img.shields.io/badge/license-MIT-green)

## How it works

The bot runs the configured agent CLI in headless streaming mode for each task,
forwards its output (assistant messages, tool activity and the final result) to
the chat, and stores the returned session id so the next message continues the
same thread. Because it uses long polling, no public domain, open port or
webhook is required.

## Features

- **Remote control** — drive an agent from your phone; it runs tasks on the host.
- **Live progress** — tool activity and replies are streamed back as they happen.
- **Multiple agents** — define personas in `agents.yaml`, each with its own
  working directory and thread; switch with `/use`.
- **Persistent threads** — session ids are stored in SQLite and survive restarts.
- **Single-user access** — only the configured Telegram user id is served.
- **Auto-deploy** — every push to `main` ships to the server over SSH.

## Commands

| Command       | Description                              |
| ------------- | ---------------------------------------- |
| `/start`      | Connect and show the active agent        |
| `/agents`     | List available agents                    |
| `/use <id>`   | Switch to another agent                  |
| `/new`        | Start a fresh thread for the agent       |
| `/stop`       | Cancel the running task                  |
| `/whoami`     | Show the active agent                    |

Anything that is not a command is treated as a task for the active agent.

## Configuration

Copy `.env.example` to `.env` and fill it in:

| Variable                | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `BOT_TOKEN`             | Telegram bot token from @BotFather                           |
| `ALLOWED_USER_ID`       | Numeric Telegram user id allowed to use the bot              |
| `AGENT_CMD`             | Command that launches the agent CLI (absolute path advised)  |
| `AGENT_WORKDIR`         | Default directory the agent works in                         |
| `AGENT_PERMISSION_MODE` | Non-interactive permission mode for unattended runs          |
| `AGENT_TIMEOUT`         | Maximum seconds a single task may run                        |
| `SHOW_TOOLS`            | Stream tool activity (`1`) or only final replies (`0`)       |

Agents live in `agents.yaml`. Each entry has an `id`, `name`, an optional
`system` instruction and an optional `workdir`.

> The agent CLI named by `AGENT_CMD` must be installed and authenticated on the
> host for the user that runs the service. Run the bot under a dedicated
> non-root user.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit it
python -m app.main
```

## Deploy

Provision the server once (as root):

```bash
REPO_URL=https://github.com/vgartg/Claude-Communication-Bot.git \
  bash <(curl -fsSL https://raw.githubusercontent.com/vgartg/Claude-Communication-Bot/main/deploy/setup.sh)
```

Install and authenticate the agent CLI for the `agent` user, fill in
`/opt/agentbot/.env`, then `systemctl restart agentbot`.

After that, pushes to `main` deploy automatically. The workflow in
`.github/workflows/deploy.yml` connects over SSH and runs `deploy/deploy.sh`,
which pulls the latest revision, installs dependencies and restarts the service.
It relies on these repository secrets:

| Secret           | Description                          |
| ---------------- | ------------------------------------ |
| `SERVER_HOST`    | Server address                       |
| `SERVER_USER`    | SSH user                             |
| `SERVER_SSH_KEY` | Private key authorized on the server |

Runtime secrets (`BOT_TOKEN`, agent credentials, …) stay only in the server's
`.env` and the service user's home; nothing sensitive is stored in the
repository.

## Project layout

```
app/
  main.py       entry point, long-polling loop
  config.py     environment configuration
  agents.py     agent registry loaded from agents.yaml
  runner.py     headless agent CLI driver (streaming)
  storage.py    SQLite state and session store
  handlers.py   Telegram command and message handlers
deploy/
  setup.sh      one-time server provisioning
  deploy.sh     pull and restart (used by CI)
  agentbot.service  systemd unit
agents.yaml     agent definitions
```

## License

MIT
