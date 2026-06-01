"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    bot_token: str
    allowed_user_id: int
    runner_cmd: str
    permission_mode: str
    workdir: Path
    timeout: float
    show_tools: bool
    db_path: Path
    agents_path: Path


def load_settings() -> Settings:
    workdir = Path(os.getenv("AGENT_WORKDIR", str(Path.home() / "workspace")))
    return Settings(
        bot_token=_require("BOT_TOKEN"),
        allowed_user_id=int(_require("ALLOWED_USER_ID")),
        runner_cmd=os.getenv("AGENT_CMD", "agent").strip(),
        permission_mode=os.getenv("AGENT_PERMISSION_MODE", "bypassPermissions").strip(),
        workdir=workdir,
        timeout=float(os.getenv("AGENT_TIMEOUT", "1800")),
        show_tools=os.getenv("SHOW_TOOLS", "1").strip() not in ("0", "false", "no", ""),
        db_path=Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "state.db"))),
        agents_path=Path(os.getenv("AGENTS_PATH", str(BASE_DIR / "agents.yaml"))),
    )
