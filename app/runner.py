"""Drives the local agent CLI in headless streaming mode.

The CLI is expected to support a JSON-lines streaming protocol over stdout:
each line is a JSON object describing one event (session metadata, assistant
messages, tool calls and a final result). This module turns that stream into a
sequence of high-level events the bot can forward to the chat.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Event:
    kind: str            # "session" | "text" | "tool" | "result" | "error"
    text: str = ""
    session_id: str = ""


def _summarize_tool(name: str, payload: dict) -> str:
    if not isinstance(payload, dict):
        return name
    for key in ("command", "file_path", "path", "pattern", "url", "query", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            snippet = value.strip().replace("\n", " ")
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
            return f"{name}: {snippet}"
    return name


class Runner:
    def __init__(self, cmd: str, default_workdir: Path, permission_mode: str, timeout: float):
        self._cmd = cmd
        self._default_workdir = default_workdir
        self._permission_mode = permission_mode
        self._timeout = timeout

    def _build_args(self, prompt: str, system: str | None, resume: str | None) -> list[str]:
        args = [
            self._cmd,
            "-p", prompt,
            "--output-format", "stream-json",
            "--verbose",
            "--permission-mode", self._permission_mode,
        ]
        if system:
            args += ["--append-system-prompt", system]
        if resume:
            args += ["--resume", resume]
        return args

    async def run(self, prompt: str, system: str | None, resume: str | None,
                  workdir: Path | None = None):
        """Yield Event objects as the agent works."""
        workdir = workdir or self._default_workdir
        workdir.mkdir(parents=True, exist_ok=True)
        args = self._build_args(prompt, system, resume)
        env = dict(os.environ)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(workdir),
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            async for event in self._read_stream(proc):
                yield event
        except asyncio.TimeoutError:
            proc.kill()
            yield Event("error", text="The task timed out.")
            return

        return_code = await proc.wait()
        if return_code != 0:
            stderr = (await proc.stderr.read()).decode(errors="replace").strip()
            detail = stderr.splitlines()[-1] if stderr else f"exit code {return_code}"
            yield Event("error", text=f"The agent process failed ({detail}).")

    async def _read_stream(self, proc):
        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=self._timeout)
            except asyncio.TimeoutError:
                raise
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for parsed in self._parse(event):
                yield parsed

    def _parse(self, event: dict):
        etype = event.get("type")
        session_id = event.get("session_id", "")

        if etype == "system" and session_id:
            yield Event("session", session_id=session_id)
            return

        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                btype = block.get("type")
                if btype == "text":
                    text = (block.get("text") or "").strip()
                    if text:
                        yield Event("text", text=text)
                elif btype == "tool_use":
                    yield Event("tool", text=_summarize_tool(block.get("name", "tool"),
                                                              block.get("input", {})))
            return

        if etype == "result":
            if session_id:
                yield Event("session", session_id=session_id)
            if event.get("is_error"):
                yield Event("error", text=str(event.get("result") or "Unknown error."))
            else:
                yield Event("result", text=(event.get("result") or "").strip())
            return
