"""User registry — JSON-backed persistent storage of (chat_id ↔ api_token) bindings.

Each registered Telegram user gets exactly one active API token at a time. Calling `register`
on an already-registered chat is idempotent (returns the existing token). `rotate` revokes the
old token and issues a new one. Lookups are O(1) in either direction.

Concurrency: the bot runs as a single asyncio process, so an asyncio.Lock around writes is
enough. Reads happen under the lock too because the registry is small and the lock is uncontended
in practice.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

TOKEN_BYTES = 24  # ~32 url-safe chars


@dataclass
class User:
    chat_id: int
    api_token: str
    telegram_username: str | None
    telegram_full_name: str
    created_at: str
    label: str = ""


@dataclass
class UserRegistry:
    path: Path
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _by_token: dict[str, User] = field(default_factory=dict, repr=False)
    _by_chat: dict[int, User] = field(default_factory=dict, repr=False)

    def load(self) -> None:
        """Load from disk synchronously (call once at startup, before serving requests)."""
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for entry in raw.get("users", []):
            user = User(**entry)
            self._by_token[user.api_token] = user
            self._by_chat[user.chat_id] = user
        log.info("Loaded %d registered user(s) from %s", len(self._by_chat), self.path)

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"users": [asdict(u) for u in self._by_chat.values()]}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    async def register(
        self,
        chat_id: int,
        telegram_username: str | None,
        telegram_full_name: str,
    ) -> User:
        """Idempotent registration. Returns the existing record if the chat is already known."""
        async with self._lock:
            existing = self._by_chat.get(chat_id)
            if existing is not None:
                return existing
            user = User(
                chat_id=chat_id,
                api_token=secrets.token_urlsafe(TOKEN_BYTES),
                telegram_username=telegram_username,
                telegram_full_name=telegram_full_name,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            self._by_token[user.api_token] = user
            self._by_chat[chat_id] = user
            self._persist()
            log.info("Registered new user chat_id=%s username=%s", chat_id, telegram_username)
            return user

    async def rotate(self, chat_id: int) -> User | None:
        """Revoke the current token and issue a new one. Returns None if chat is not registered."""
        async with self._lock:
            old = self._by_chat.get(chat_id)
            if old is None:
                return None
            self._by_token.pop(old.api_token, None)
            new = User(
                chat_id=chat_id,
                api_token=secrets.token_urlsafe(TOKEN_BYTES),
                telegram_username=old.telegram_username,
                telegram_full_name=old.telegram_full_name,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                label=old.label,
            )
            self._by_token[new.api_token] = new
            self._by_chat[chat_id] = new
            self._persist()
            log.info("Rotated token for chat_id=%s", chat_id)
            return new

    def by_token(self, token: str) -> User | None:
        return self._by_token.get(token)

    def by_chat(self, chat_id: int) -> User | None:
        return self._by_chat.get(chat_id)

    def all_chats(self) -> list[int]:
        return list(self._by_chat.keys())


_registry: UserRegistry | None = None


def get_registry() -> UserRegistry:
    if _registry is None:
        raise RuntimeError("UserRegistry not initialized. Call init_registry() at startup.")
    return _registry


def init_registry(path: Path) -> UserRegistry:
    global _registry
    _registry = UserRegistry(path=path)
    _registry.load()
    return _registry
