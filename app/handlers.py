"""Telegram command and message handlers."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from .agents import Agent, AgentRegistry
from .config import Settings
from .runner import Runner
from .storage import Store

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096


def build_router(settings: Settings, registry: AgentRegistry, store: Store,
                 runner: Runner) -> Router:
    router = Router()
    allow = F.from_user.id == settings.allowed_user_id
    busy: dict[int, asyncio.Task] = {}

    async def current_agent_id(user_id: int) -> str:
        agent_id = await store.get_active_agent(user_id)
        if agent_id and registry.get(agent_id):
            return agent_id
        await store.set_active_agent(user_id, registry.default_id)
        return registry.default_id

    @router.message(Command("start", "help"), allow)
    async def start(message: Message) -> None:
        agent = registry.get(await current_agent_id(message.from_user.id))
        await message.answer(
            f"Connected. Active agent: {agent.name}.\n\n"
            "Just send a task and I'll work on it. Commands:\n"
            "/agents - list available agents\n"
            "/use <id> - switch agent\n"
            "/new - start a fresh thread for the current agent\n"
            "/stop - cancel the running task\n"
            "/whoami - show the active agent"
        )

    @router.message(Command("agents"), allow)
    async def agents_cmd(message: Message) -> None:
        active = await current_agent_id(message.from_user.id)
        lines = [
            f"- {a.id}: {a.name}" + (" (active)" if a.id == active else "")
            for a in registry.all()
        ]
        await message.answer("Available agents:\n" + "\n".join(lines))

    @router.message(Command("use"), allow)
    async def use_cmd(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /use <agent-id>. See /agents.")
            return
        agent_id = parts[1].strip()
        if not registry.get(agent_id):
            await message.answer(f"Unknown agent '{agent_id}'. See /agents.")
            return
        await store.set_active_agent(message.from_user.id, agent_id)
        await message.answer(f"Switched to {registry.get(agent_id).name}.")

    @router.message(Command("new"), allow)
    async def new_cmd(message: Message) -> None:
        agent_id = await current_agent_id(message.from_user.id)
        await store.clear_session(message.from_user.id, agent_id)
        await message.answer("Started a fresh thread.")

    @router.message(Command("whoami"), allow)
    async def whoami_cmd(message: Message) -> None:
        agent = registry.get(await current_agent_id(message.from_user.id))
        await message.answer(f"Active agent: {agent.name} ({agent.id}).")

    @router.message(Command("stop"), allow)
    async def stop_cmd(message: Message) -> None:
        task = busy.get(message.from_user.id)
        if task and not task.done():
            task.cancel()
            await message.answer("Stopping the current task.")
        else:
            await message.answer("Nothing is running.")

    @router.message(allow, F.text)
    async def chat(message: Message, bot: Bot) -> None:
        user_id = message.from_user.id
        if user_id in busy and not busy[user_id].done():
            await message.answer("Still working on the previous task. Send /stop to cancel it.")
            return
        task = asyncio.create_task(_handle_task(message, bot))
        busy[user_id] = task

    async def _handle_task(message: Message, bot: Bot) -> None:
        user_id = message.from_user.id
        agent_id = await current_agent_id(user_id)
        agent = registry.get(agent_id)
        resume = await store.get_session(user_id, agent_id)

        workdir = Path(agent.workdir).expanduser() if agent.workdir else settings.workdir

        typing = asyncio.create_task(_keep_typing(bot, message.chat.id))
        produced_text = False
        try:
            async for event in runner.run(message.text, agent.system or None, resume, workdir):
                if event.kind == "session" and event.session_id:
                    await store.set_session(user_id, agent_id, event.session_id)
                elif event.kind == "text":
                    produced_text = True
                    await _send(message, event.text)
                elif event.kind == "tool" and settings.show_tools:
                    await _send(message, f"⚙️ {event.text}")
                elif event.kind == "result":
                    if not produced_text and event.text:
                        await _send(message, event.text)
                elif event.kind == "error":
                    await _send(message, f"⚠️ {event.text}")
        except asyncio.CancelledError:
            await message.answer("Task cancelled.")
            raise
        finally:
            typing.cancel()

    @router.message()
    async def ignore_others(message: Message) -> None:
        logger.info("Ignored message from %s",
                    message.from_user.id if message.from_user else "?")

    return router


async def _send(message: Message, text: str) -> None:
    for chunk in _split(text):
        await message.answer(chunk)


async def _keep_typing(bot: Bot, chat_id: int) -> None:
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


def _split(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return chunks
