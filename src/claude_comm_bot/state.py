"""In-memory store of pending /api/ask requests, scoped per Telegram chat.

Each pending ask is keyed by short UUID. To route Telegram replies back to the right ask we keep
a `(chat_id, message_id) -> ask_id` index — message_ids are only unique within a chat.

`resolve_oldest` is scoped to chat_id so a registered user can answer their own questions without
accidentally answering another user's pending ask.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PendingAsk:
    ask_id: str
    chat_id: int
    question: str
    options: list[str]
    future: asyncio.Future[tuple[str, Literal["button", "text"]]]
    message_id: int | None = None
    session_id: str | None = None


@dataclass
class AskStore:
    pending: dict[str, PendingAsk] = field(default_factory=dict)
    by_chat_msg: dict[tuple[int, int], str] = field(default_factory=dict)

    def create(self, chat_id: int, question: str, options: list[str], session_id: str | None) -> PendingAsk:
        loop = asyncio.get_running_loop()
        ask = PendingAsk(
            ask_id=uuid.uuid4().hex[:8],
            chat_id=chat_id,
            question=question,
            options=options,
            future=loop.create_future(),
            session_id=session_id,
        )
        self.pending[ask.ask_id] = ask
        return ask

    def attach_message(self, ask_id: str, message_id: int) -> None:
        ask = self.pending.get(ask_id)
        if ask is None:
            return
        ask.message_id = message_id
        self.by_chat_msg[(ask.chat_id, message_id)] = ask_id

    def pop(self, ask_id: str) -> PendingAsk | None:
        ask = self.pending.pop(ask_id, None)
        if ask and ask.message_id is not None:
            self.by_chat_msg.pop((ask.chat_id, ask.message_id), None)
        return ask

    def resolve_by_id(self, ask_id: str, answer: str, via: Literal["button", "text"]) -> bool:
        ask = self.pop(ask_id)
        if ask is None or ask.future.done():
            return False
        ask.future.set_result((answer, via))
        return True

    def resolve_by_message(self, chat_id: int, message_id: int, answer: str) -> bool:
        ask_id = self.by_chat_msg.get((chat_id, message_id))
        if ask_id is None:
            return False
        return self.resolve_by_id(ask_id, answer, via="text")

    def resolve_oldest_for_chat(self, chat_id: int, answer: str) -> bool:
        """Resolve the earliest pending ask in this chat."""
        for ask_id, ask in self.pending.items():
            if ask.chat_id == chat_id and not ask.future.done():
                return self.resolve_by_id(ask_id, answer, via="text")
        return False

    def list_for_chat(self, chat_id: int) -> list[PendingAsk]:
        return [a for a in self.pending.values() if a.chat_id == chat_id]

    def cancel_chat(self, chat_id: int) -> int:
        cancelled = 0
        for ask_id in [aid for aid, a in self.pending.items() if a.chat_id == chat_id]:
            ask = self.pop(ask_id)
            if ask and not ask.future.done():
                ask.future.cancel()
                cancelled += 1
        return cancelled

    def cancel_all(self) -> None:
        for ask in list(self.pending.values()):
            if not ask.future.done():
                ask.future.cancel()
        self.pending.clear()
        self.by_chat_msg.clear()


store = AskStore()
