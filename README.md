# Claude Communication Bot

[![CI](https://github.com/vgartg/Claude-Communication-Bot/actions/workflows/ci.yml/badge.svg)](https://github.com/vgartg/Claude-Communication-Bot/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![aiogram 3](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A pet project I built to keep myself in the loop when a long coding agent run is going on in the
background — the bot pings my phone the moment the agent finishes a turn, and any clarifying
question shows up in the chat as an inline-keyboard prompt I can answer with one tap. Multi-tenant
since v0.2: one bot can serve a whole team, each user gets their own personal API token bound to
their Telegram chat

## What it does

A tiny FastAPI service wraps an aiogram Telegram bot. Three integration points to whatever
coding agent wants to talk through it:

- **`POST /api/notify`** — fire-and-forget messages, kind tag (`finished` / `error` / `crash` /
  `info`) changes the header emoji
- **`POST /api/ask`** — send a question (optionally with answer choices), block until the user
  replies in Telegram, return the answer. Tap-a-button, reply-to-message, or plain-text reply
  while a question is queued all work
- **PreToolUse hook on `AskUserQuestion`** — the script `skill/scripts/ask_user_question_hook.py`
  intercepts the tool call, routes it through `/api/ask`, and feeds the answer back to the agent
  via `additionalContext` + `permissionDecision: deny`. The terminal UI only appears as a
  graceful fallback if the bot is offline or the user doesn't answer in time

A small Vite + TypeScript + Tailwind dashboard lives on port `:8080` for inspecting live state:
service health, pending questions, available routes, and a manual notify form

## Architecture

```
.
├── src/claude_comm_bot/    # core: telegram bot, state, HTTP API, user registry
├── web/                    # Vite + TypeScript + Tailwind dashboard
├── skill/                  # client-side glue: hook scripts + ad-hoc CLI
├── bin/                    # bash + cmd launchers (server, demo)
├── tests/                  # pytest backend suite
├── data/                   # runtime: users.json (gitignored)
└── .github/workflows/      # single CI workflow for both halves
```

The aiogram polling loop and the uvicorn ASGI server share one asyncio loop, so a `/api/ask`
HTTP request can `await` a `Future` that is fulfilled the moment a Telegram callback or text
message arrives — no queues, no pollers, no extra processes

## Quickstart (run the bot)

You only need **Python 3.11+** and **Node 20+** locally — the `bin/server` script bootstraps a
venv and installs dependencies on first run

```bash
cp .env.example .env        # fill in CCB_BOT_TOKEN (from @BotFather)
./bin/server                # bash, macOS/Linux/WSL
bin\server.cmd              # Windows
```

The bot listens on `http://127.0.0.1:3000`. To run the dashboard:

```bash
cd web
npm install
npm run dev                 # served on :8080, proxies /api/* to :3000
```

## Onboarding a user (yours or a teammate's)

This is what every person who wants notifications has to do **once**:

1. **Find the bot in Telegram** and send `/start`. The bot replies with a personal API token and
   a JSON snippet ready to copy
2. **Merge that snippet into `~/.claude/settings.json`** on your machine. Replace the two
   `<absolute path …>` placeholders with the real locations of the hook scripts inside your
   clone of this repo. See [HANDOFF.md](HANDOFF.md) for the full step-by-step
3. **Reload Claude Code:** run `/hooks` once in any session (or restart). The watcher doesn't
   always pick up newly-added `hooks` sections in a running session
4. **Test:** finish any turn — you should see "🔔 Agent finished" in Telegram within a second

If your token leaks, send `/revoke` to the bot — it issues a fresh token and the old one stops
working immediately

## HTTP API

| Method | Path             | Auth   | What it does                                                                 |
| ------ | ---------------- | ------ | ---------------------------------------------------------------------------- |
| GET    | `/api/health`    | none   | liveness probe with version and total pending-asks count                     |
| GET    | `/api/routes`    | none   | route catalog — same content as this table, served as JSON                   |
| GET    | `/api/whoami`    | Bearer | return the Telegram chat your token is bound to (handy after onboarding)     |
| GET    | `/api/pending`   | Bearer | list YOUR pending questions (scoped by token → chat)                         |
| POST   | `/api/notify`    | Bearer | enqueue a message to YOUR chat (kind = `finished`/`error`/`crash`/`info`)    |
| POST   | `/api/ask`       | Bearer | send a question with optional choices, block until you answer                |

Bot commands (Telegram side):

| Command    | What it does                                                              |
| ---------- | ------------------------------------------------------------------------- |
| `/start`   | register, print your personal token + setup snippet                       |
| `/token`   | re-show your current token (don't share it)                               |
| `/revoke`  | rotate the token; old one stops working immediately                       |
| `/pending` | list questions currently waiting for your answer                          |
| `/cancel`  | cancel all your pending questions                                         |
| `/users`   | admin-only — list every registered user                                   |

## Tooling

| Concern          | Tool                                  |
| ---------------- | ------------------------------------- |
| HTTP framework   | FastAPI + Uvicorn                     |
| Telegram client  | aiogram 3                             |
| Settings         | pydantic-settings (`.env` driven)     |
| Persistence      | plain JSON file under `data/`         |
| Backend tests    | pytest + pytest-asyncio + httpx       |
| Backend lint     | ruff                                  |
| Frontend stack   | Vite, vanilla TypeScript, Tailwind 3  |
| Frontend tests   | vitest + jsdom                        |
| Frontend lint    | ESLint + Prettier                     |
| CI               | GitHub Actions, Python × Node matrix  |

## Roadmap

- Phase 2: kick off new turns *from* Telegram (Remote Control / SendMessage integration)
- Per-session ask history viewable from the dashboard
- Optional webhook mode for the Telegram side (current build uses long polling)
- A second transport (Slack DMs) sitting behind the same `/api/notify` and `/api/ask` contracts
- Encrypted at-rest persistence so pending asks survive a restart

## License

Released under the MIT License — see [LICENSE](LICENSE)
