# Handoff guide

How to connect Claude Code on your machine to the bot so you get Telegram notifications and
remote Q&A. Aimed at someone who is *not* the bot's admin — they got told "use the bot at
`@<botname>`" and need to plug it in

## Prerequisites

- The bot is running somewhere reachable (LAN IP, VPN, or public host). Ask the admin for the
  base URL — for example `http://192.168.1.10:3000` for a LAN bot, or
  `https://ccb.example.com` for a public one
- You have Python 3.11+ on your machine — `python --version` should print 3.11 or higher
- You have a local clone of this repository (the hook scripts live in `skill/scripts/`)

## Step 1 — Register in Telegram

1. Open the bot in Telegram (the admin will share its username, e.g.
   `@vgartg_claude_communication_bot`)
2. Send `/start`. The bot replies with two things:
   - your personal API token (a ~32-character string)
   - a JSON snippet ready to paste into `~/.claude/settings.json`

Keep the token secret. If you ever leak it, run `/revoke` in the bot and you'll get a fresh one

## Step 2 — Merge the snippet into your Claude Code settings

The bot's `/start` reply contains placeholders like `<absolute path to notify_stop.py>` — you
need to fill those in with the real paths on your machine. Example on Windows where the repo
lives at `C:\code\Claude-Communication-Bot`:

```json
{
  "env": {
    "CCB_BASE_URL": "http://192.168.1.10:3000",
    "CCB_API_TOKEN": "your-token-from-bot-here",
    "CCB_ASK_HOOK_TIMEOUT": "120"
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": [
              "C:\\code\\Claude-Communication-Bot\\skill\\scripts\\notify_stop.py",
              "--kind", "finished"
            ],
            "timeout": 5,
            "async": true
          }
        ]
      }
    ],
    "StopFailure": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": [
              "C:\\code\\Claude-Communication-Bot\\skill\\scripts\\notify_stop.py",
              "--kind", "error"
            ],
            "timeout": 5,
            "async": true
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": [
              "C:\\code\\Claude-Communication-Bot\\skill\\scripts\\ask_user_question_hook.py"
            ],
            "timeout": 130
          }
        ]
      }
    ]
  }
}
```

On macOS / Linux, use forward slashes (`/Users/you/code/...`) and no escaping is needed

**If your `~/.claude/settings.json` already has other entries**, merge — don't replace. Add the
`env` keys to your existing `env` block, and add the `Stop` / `StopFailure` / `PreToolUse` arrays
to your existing `hooks` block

## Step 3 — Reload Claude Code

Run `/hooks` once in any open Claude Code session, or restart the CLI. The settings watcher
sometimes misses freshly-added `hooks` sections in a running session — `/hooks` forces a reload

## Step 4 — Verify

1. Open a Claude Code session and finish any turn (just say "ok thanks"). You should see a
   **🔔 Agent finished** message in Telegram within 1-2 seconds. If you don't, see
   *Troubleshooting* below
2. Ask the agent to pose a clarifying question. The terminal UI shouldn't appear — instead the
   question lands in Telegram with inline-keyboard buttons. Tap one and the agent picks it up

## Troubleshooting

**No notification at all when a turn ends**
- Run `/hooks` in Claude Code — confirm the Stop hook is listed
- Run the hook script manually with the same env vars to see why it fails:
  ```bash
  CCB_BASE_URL=http://192.168.1.10:3000 CCB_API_TOKEN=your-token \
    echo '{}' | python /path/to/notify_stop.py --kind finished
  ```
- Hit `/api/health` from your machine: `curl http://192.168.1.10:3000/api/health` — should return
  `{"status":"ok",...}`. If it doesn't, your machine can't reach the bot (firewall, wrong URL)

**HTTP 401 from `/api/notify`**
- Your token is wrong or revoked. Run `/token` in the bot to see the current one, or `/revoke`
  to issue a fresh one. Then update `CCB_API_TOKEN` and reload `/hooks`

**The agent asks in the terminal, not in Telegram**
- This is the intentional fallback when the bot is offline or you didn't answer within
  `CCB_ASK_HOOK_TIMEOUT` seconds (default 120). Raise the env var if you need more time
- Multi-question or `multiSelect: true` AskUserQuestion calls always fall back to the terminal —
  Telegram inline-keyboards don't render them cleanly

**I want to stop the integration temporarily**
- Run `/cancel` in the bot to abort any pending questions
- Comment out (or remove) the hooks block in `~/.claude/settings.json` and `/hooks` reload

## Sharing the bot with another teammate

Just point them at this file and the bot's Telegram username. There's no admin action required —
`/start` registers a new user automatically. To see who's connected, the admin can send `/users`
to the bot (admin-only command)
