"""Per-user state and per-agent session ids, persisted in SQLite.

The agent CLI keeps its own conversation history; here we only remember which
agent is active and the session id needed to resume each agent's thread.
"""
from __future__ import annotations

from pathlib import Path

import aiosqlite


class Store:
    def __init__(self, path: Path):
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS state (
                user_id  INTEGER PRIMARY KEY,
                agent_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                user_id    INTEGER NOT NULL,
                agent_id   TEXT    NOT NULL,
                session_id TEXT    NOT NULL,
                PRIMARY KEY (user_id, agent_id)
            );
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()

    async def get_active_agent(self, user_id: int) -> str | None:
        async with self._db.execute(
            "SELECT agent_id FROM state WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def set_active_agent(self, user_id: int, agent_id: str) -> None:
        await self._db.execute(
            "INSERT INTO state (user_id, agent_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET agent_id = excluded.agent_id",
            (user_id, agent_id),
        )
        await self._db.commit()

    async def get_session(self, user_id: int, agent_id: str) -> str | None:
        async with self._db.execute(
            "SELECT session_id FROM sessions WHERE user_id = ? AND agent_id = ?",
            (user_id, agent_id),
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def set_session(self, user_id: int, agent_id: str, session_id: str) -> None:
        await self._db.execute(
            "INSERT INTO sessions (user_id, agent_id, session_id) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, agent_id) DO UPDATE SET session_id = excluded.session_id",
            (user_id, agent_id, session_id),
        )
        await self._db.commit()

    async def clear_session(self, user_id: int, agent_id: str) -> None:
        await self._db.execute(
            "DELETE FROM sessions WHERE user_id = ? AND agent_id = ?",
            (user_id, agent_id),
        )
        await self._db.commit()
