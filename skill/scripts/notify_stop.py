#!/usr/bin/env python3
"""Multi-purpose notification hook script.

Used by Claude Code Stop / StopFailure / SessionEnd / Notification hooks. Reads the event JSON
from stdin, POSTs a short message to /api/notify on the local bot, and exits 0 even on failure
so the user's workflow is never blocked by a downed bot.

Usage in a hook command:
    python notify_stop.py [--kind finished|error|crash|info] [--text "override"]

Defaults to kind=finished. The script extracts a useful body from the event payload (cwd or
session_id) so notifications carry context.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Claude Code feeds the hook JSON as UTF-8 on stdin. On Windows, the default text-mode
# encoding for sys.stdin is the OEM/ANSI codepage, which mangles non-ASCII bytes. Force UTF-8.
try:
    sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except (AttributeError, OSError):
    pass


def _read_event() -> dict[str, object]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _default_text(kind: str, event: dict[str, object]) -> str:
    cwd = event.get("cwd")
    suffix = f" in {cwd}" if cwd else ""
    return {
        "finished": f"Agent finished a turn{suffix}.",
        "error":    f"Agent encountered an error{suffix}.",
        "crash":    f"Agent crashed{suffix}.",
        "info":     f"Notice from agent{suffix}.",
    }.get(kind, f"Notice{suffix}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify the Telegram bot of a Claude Code event.")
    parser.add_argument("--kind", choices=["finished", "error", "crash", "info"], default="finished")
    parser.add_argument("--text", default=None, help="Override the notification body.")
    args = parser.parse_args()

    base = os.environ.get("CCB_BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    token = os.environ.get("CCB_API_TOKEN", "")
    if not token:
        print("[notify] CCB_API_TOKEN not set — skipping", file=sys.stderr)
        return 0

    event = _read_event()
    session_id = event.get("session_id") or event.get("sessionId")
    text = args.text or _default_text(args.kind, event)

    payload = json.dumps({
        "text": text,
        "session_id": session_id,
        "kind": args.kind,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/notify",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[notify] bot unreachable: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
