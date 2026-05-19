#!/usr/bin/env python3
"""PreToolUse hook on AskUserQuestion — route the question to Telegram.

Claude Code passes the tool call JSON on stdin. We:
  1. Extract the first question + its options (labels).
  2. POST /api/ask and wait for a reply (configurable timeout).
  3. On success: emit hook JSON that DENIES the tool call but injects the user's answer
     as additionalContext, so Claude sees "answered: X" and continues without rendering
     the terminal UI.
  4. On timeout/error: emit no JSON → exit 0 → tool proceeds to its normal terminal UI
     (graceful fallback so the agent is never blocked by a downed bot).

Multi-question or multiSelect AskUserQuestion calls fall back to the terminal — Telegram
inline-keyboards are awkward for multi-pick and we keep things simple.

Env:
  CCB_BASE_URL          default http://127.0.0.1:3000
  CCB_API_TOKEN         required — your personal token from /start
  CCB_ASK_HOOK_TIMEOUT  seconds to wait in Telegram before falling back (default 120)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Claude Code feeds the hook JSON as UTF-8 on stdin. On Windows, the default text-mode
# encoding for sys.stdin is the OEM/ANSI codepage (cp1251 etc.), which mangles non-ASCII.
# Force UTF-8 on both stdin and stdout so the question text and hook reply survive intact.
try:
    sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except (AttributeError, OSError):
    pass


def _fallback() -> int:
    """Exit cleanly with no JSON → Claude Code shows the normal terminal UI."""
    return 0


def _emit_answer(answer: str, ask_id_hint: str) -> int:
    """Deny the tool call, feed the answer back via additionalContext."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Answered out-of-band via Telegram (ask {ask_id_hint}): {answer}"
            ),
            "additionalContext": (
                "The user answered the AskUserQuestion via the Telegram bot.\n"
                f"Their answer: {answer}\n"
                "Treat this as their response and continue — do not ask the same question again."
            ),
        },
        "suppressOutput": True,
    }
    sys.stdout.write(json.dumps(payload))
    return 0


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return _fallback()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback()

    if event.get("tool_name") != "AskUserQuestion":
        return _fallback()

    questions = (event.get("tool_input") or {}).get("questions") or []
    if len(questions) != 1:
        # Multi-question prompts go to terminal — UX in Telegram would be poor
        return _fallback()

    q = questions[0]
    if q.get("multiSelect"):
        return _fallback()

    question_text = str(q.get("question") or "").strip()
    if not question_text:
        return _fallback()

    options_in = q.get("options") or []
    option_labels = [str(o.get("label") or "").strip() for o in options_in if o.get("label")]
    # Always allow free-form too: hint it in the question body
    body = question_text
    descriptions = [
        f"• {o.get('label')}: {o.get('description')}"
        for o in options_in
        if o.get("description")
    ]
    if descriptions:
        body += "\n\n" + "\n".join(descriptions)

    base = os.environ.get("CCB_BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    token = os.environ.get("CCB_API_TOKEN", "")
    if not token:
        print("[ask_hook] CCB_API_TOKEN not set — falling back to terminal", file=sys.stderr)
        return _fallback()

    timeout = int(os.environ.get("CCB_ASK_HOOK_TIMEOUT", "120"))
    session_id = event.get("session_id") or event.get("sessionId")

    payload = {
        "question": body[:3500],
        "options": option_labels[:8] if option_labels else None,
        "session_id": session_id,
        "timeout": timeout,
    }
    # Strip nulls for cleanliness
    payload = {k: v for k, v in payload.items() if v is not None}

    req = urllib.request.Request(
        f"{base}/api/ask",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        # urlopen timeout slightly above payload timeout so the server has room to reply
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 504:
            # User didn't answer in time — show terminal UI
            print("[ask_hook] Telegram timeout — falling back to terminal", file=sys.stderr)
            return _fallback()
        print(f"[ask_hook] HTTP {exc.code} — falling back to terminal", file=sys.stderr)
        return _fallback()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[ask_hook] bot unreachable: {exc} — falling back to terminal", file=sys.stderr)
        return _fallback()

    answer = str(data.get("answer") or "").strip()
    if not answer:
        return _fallback()

    return _emit_answer(answer, ask_id_hint=str(data.get("via", "tg")))


if __name__ == "__main__":
    raise SystemExit(main())
