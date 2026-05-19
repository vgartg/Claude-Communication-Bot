#!/usr/bin/env python3
"""Ask a question through Telegram and block until the user replies.

Usage:
    python ask_tg.py "Your question?" [--option A --option B ...] [--timeout 600] [--session SID]

Exits:
    0 — answer printed to stdout (single line, stripped of trailing newline)
    2 — bot unreachable or auth failed
    3 — timed out
    4 — cancelled (e.g. user sent /cancel)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="Ask a question via Telegram and wait for the reply.")
    p.add_argument("question", help="The question text to send to the user.")
    p.add_argument(
        "--option",
        action="append",
        default=[],
        help="Optional answer choice (repeatable, max 8). Renders as an inline-keyboard button.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Seconds to wait. Omit or 0 → wait forever (server-side timeout still applies).",
    )
    p.add_argument("--session", default=os.environ.get("CLAUDE_SESSION_ID"))
    args = p.parse_args()

    base = os.environ.get("CCB_BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    token = os.environ.get("CCB_API_TOKEN", "")

    body: dict[str, object] = {"question": args.question}
    if args.option:
        body["options"] = args.option[:8]
    if args.session:
        body["session_id"] = args.session
    if args.timeout is not None:
        body["timeout"] = args.timeout

    req = urllib.request.Request(
        f"{base}/api/ask",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    # Long timeout for the urlopen call — the server will hold the connection open until
    # the user replies. None means "wait forever".
    http_timeout = args.timeout if args.timeout and args.timeout > 0 else None
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        if exc.code == 504:
            print(f"[ask_tg] timed out: {msg}", file=sys.stderr)
            return 3
        if exc.code == 409:
            print(f"[ask_tg] cancelled: {msg}", file=sys.stderr)
            return 4
        print(f"[ask_tg] HTTP {exc.code}: {msg}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[ask_tg] bot unreachable: {exc}", file=sys.stderr)
        return 2

    answer = str(data.get("answer", "")).rstrip("\n")
    sys.stdout.write(answer + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
