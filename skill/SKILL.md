---
name: telegram-bridge
description: |
  Mirror your Claude Code session into Telegram — get a notification on Stop, route any
  AskUserQuestion to Telegram with inline-keyboard options, receive replies back as if you'd
  answered locally. Multi-tenant: each user has a personal API token bound to their Telegram
  chat_id.
---

# Telegram bridge for Claude Code

This skill plugs Claude Code into the **claude-comm-bot** HTTP API. The bot must be running
(see top-level README), and you must have registered with the bot by sending `/start` once —
that gives you a personal `CCB_API_TOKEN` bound to your Telegram chat.

## Three integration points (configured via hooks)

### 1. Stop / StopFailure / SessionEnd — notifications

Three hooks that all call the same `notify_stop.py` script with different `--kind` flags:

| Event       | `--kind`   | What you see in Telegram                  |
| ----------- | ---------- | ----------------------------------------- |
| Stop        | `finished` | 🔔 Agent finished a turn in <cwd>         |
| StopFailure | `error`    | ⚠️ Agent encountered an error in <cwd>    |
| SessionEnd  | `info`     | ℹ️ Session ended                          |

All three are `async: true` so they never block your terminal.

### 2. PreToolUse on AskUserQuestion — route questions to Telegram

`ask_user_question_hook.py` intercepts the tool call before the terminal UI appears, posts the
question to `/api/ask`, waits up to `CCB_ASK_HOOK_TIMEOUT` seconds (default 120), and feeds
the user's answer back into Claude via `additionalContext` + `permissionDecision: deny`.

If the bot is offline OR the user doesn't answer in time, the hook exits 0 with no JSON output,
which means **Claude Code falls back to the regular terminal UI** — your workflow is never
blocked by a downed bot.

Single-question, single-select prompts are routed. Multi-question or `multiSelect: true` prompts
fall back to the terminal because Telegram inline-keyboards don't render them cleanly.

### 3. ad-hoc CLI (optional) — `ask_tg.py`

A standalone CLI you can call directly from a shell or a project rule (e.g. CLAUDE.md): same
`/api/ask` POST, but you craft the question yourself instead of going through `AskUserQuestion`.

## Installing

1. **Register** — open the bot in Telegram, send `/start`. The bot replies with your personal
   token and a JSON snippet ready to paste.
2. **Merge** the snippet into `~/.claude/settings.json` (or `.claude/settings.json` per project).
   Replace the two file paths with the absolute locations of the hook scripts inside your local
   clone of the repo.
3. **Reload** Claude Code: run `/hooks` once in the terminal, or restart. (The settings watcher
   doesn't always pick up newly-added `hooks` sections in a running session.)
4. **Smoke test** — finish a turn. You should see "🔔 Agent finished" in Telegram within a
   second.

## Troubleshooting

- `/api/health` returns version + pending count when the bot is up
- `/api/whoami` (with your bearer token) returns your registered chat info — handy to verify a
  freshly-pasted token works
- Send `/pending` to the bot to see questions waiting for your answer
- Send `/cancel` to abort all your pending questions (e.g. if the agent's HTTP client is stuck)
- Send `/revoke` to rotate your token (the old one immediately stops working)
