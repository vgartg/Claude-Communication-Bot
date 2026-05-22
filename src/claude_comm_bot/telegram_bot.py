"""Telegram bot — multi-tenant.

Anyone may /start the bot; that registers them and returns a personal API token. After that all
replies are routed to the right pending ask via (chat_id, message_id). Replies in chats that
aren't registered are silently ignored (no info leak).
"""

from __future__ import annotations

import contextlib
import logging
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .config import get_settings
from .state import PendingAsk, store
from .store import User, get_registry

log = logging.getLogger(__name__)

CALLBACK_PREFIX = "ccb:"


def build_bot() -> tuple[Bot, Dispatcher]:
    settings = get_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    _register_handlers(dp)
    return bot, dp


def _setup_snippet(user: User, base_url_hint: str) -> str:
    """Render the JSON snippet the user copies into ~/.claude/settings.json."""
    return (
        "{\n"
        '  "env": {\n'
        f'    "CCB_BASE_URL": "{base_url_hint}",\n'
        f'    "CCB_API_TOKEN": "{user.api_token}"\n'
        "  },\n"
        '  "hooks": {\n'
        '    "Stop": [\n'
        '      {\n'
        '        "hooks": [\n'
        '          {\n'
        '            "type": "command",\n'
        '            "command": "python",\n'
        '            "args": ["<absolute path to notify_stop.py>"],\n'
        '            "timeout": 5,\n'
        '            "async": true\n'
        "          }\n"
        "        ]\n"
        "      }\n"
        "    ],\n"
        '    "PreToolUse": [\n'
        '      {\n'
        '        "matcher": "AskUserQuestion",\n'
        '        "hooks": [\n'
        '          {\n'
        '            "type": "command",\n'
        '            "command": "python",\n'
        '            "args": ["<absolute path to ask_user_question_hook.py>"],\n'
        '            "timeout": 120\n'
        "          }\n"
        "        ]\n"
        "      }\n"
        "    ]\n"
        "  }\n"
        "}"
    )


def _register_handlers(dp: Dispatcher) -> None:
    settings = get_settings()
    base_url_hint = f"http://127.0.0.1:{settings.port}"

    def is_admin(message_or_cb: Message | CallbackQuery) -> bool:
        user = message_or_cb.from_user
        return user is not None and user.id in settings.admin_user_ids

    @dp.message(Command("start"))
    async def on_start(message: Message) -> None:
        if message.from_user is None:
            return
        reg = get_registry()
        user = await reg.register(
            chat_id=message.chat.id,
            telegram_username=message.from_user.username,
            telegram_full_name=message.from_user.full_name,
        )
        snippet = _setup_snippet(user, base_url_hint)
        await message.answer(
            "👋 <b>Welcome to Claude Communication Bot</b>\n\n"
            "I bridge your coding agent and this chat — you'll get pinged when the agent "
            "finishes a turn, and any question it asks will appear here. Reply (or tap a "
            "button) and your answer flows back to the agent.\n\n"
            "<b>Your personal API token</b> (keep it secret):\n"
            f"<code>{user.api_token}</code>\n\n"
            "<b>Setup on your machine:</b> merge the snippet below into "
            "<code>~/.claude/settings.json</code>, replace the two file paths with the "
            "absolute locations of the hook scripts from the repo, then run <code>/hooks</code> "
            "in Claude Code to reload (or restart it).\n\n"
            f"<pre>{escape(snippet)}</pre>\n\n"
            "Commands:\n"
            "• <code>/token</code> — show your token again\n"
            "• <code>/revoke</code> — rotate the token (old one stops working)\n"
            "• <code>/pending</code> — see questions waiting for your answer\n"
            "• <code>/cancel</code> — abort all pending questions in this chat"
        )

    @dp.message(Command("token"))
    async def on_token(message: Message) -> None:
        user = get_registry().by_chat(message.chat.id)
        if user is None:
            await message.answer("You're not registered yet — send /start first.")
            return
        await message.answer(
            f"Your API token:\n<code>{user.api_token}</code>\n\n"
            "Keep it secret. If it leaks, run /revoke to rotate it."
        )

    @dp.message(Command("revoke"))
    async def on_revoke(message: Message) -> None:
        reg = get_registry()
        if reg.by_chat(message.chat.id) is None:
            await message.answer("You're not registered yet — send /start first.")
            return
        new = await reg.rotate(message.chat.id)
        assert new is not None
        await message.answer(
            "🔄 Token rotated. The old token is now invalid.\n\n"
            f"New token:\n<code>{new.api_token}</code>\n\n"
            "Update <code>CCB_API_TOKEN</code> in <code>~/.claude/settings.json</code> on your "
            "machine, then run <code>/hooks</code> in Claude Code (or restart)."
        )

    @dp.message(Command("pending"))
    async def on_pending(message: Message) -> None:
        if get_registry().by_chat(message.chat.id) is None:
            return  # silent
        items = store.list_for_chat(message.chat.id)
        if not items:
            await message.answer("No pending questions. ✅")
            return
        lines = ["<b>Pending questions:</b>"]
        for ask in items:
            tag = f" <i>(session {ask.session_id})</i>" if ask.session_id else ""
            lines.append(f"• <code>{ask.ask_id}</code>{tag}: {escape(ask.question[:120])}")
        await message.answer("\n".join(lines))

    @dp.message(Command("cancel"))
    async def on_cancel(message: Message) -> None:
        if get_registry().by_chat(message.chat.id) is None:
            return  # silent
        n = store.cancel_chat(message.chat.id)
        await message.answer(f"Cancelled {n} pending question(s).")

    @dp.message(Command("users"))
    async def on_users(message: Message) -> None:
        if not is_admin(message):
            return  # silent — feature is hidden for non-admins
        chats = get_registry().all_chats()
        lines = [f"<b>Registered users:</b> {len(chats)}"]
        for cid in chats:
            u = get_registry().by_chat(cid)
            if u:
                tag = f"@{u.telegram_username}" if u.telegram_username else u.telegram_full_name
                lines.append(f"• <code>{cid}</code> — {escape(tag)} (since {u.created_at})")
        await message.answer("\n".join(lines))

    @dp.callback_query(F.data.startswith(CALLBACK_PREFIX))
    async def on_callback(cb: CallbackQuery) -> None:
        if get_registry().by_chat(cb.message.chat.id) is None if cb.message else True:
            await cb.answer("Not registered.", show_alert=True)
            return
        try:
            _, ask_id, idx_str = (cb.data or "").split(":", 2)
            idx = int(idx_str)
        except (ValueError, AttributeError):
            await cb.answer("Malformed callback.", show_alert=True)
            return

        ask = store.pending.get(ask_id)
        if ask is None or (cb.message and ask.chat_id != cb.message.chat.id):
            await cb.answer("This question is no longer waiting.", show_alert=True)
            if cb.message:
                with contextlib.suppress(Exception):
                    await cb.message.edit_reply_markup(reply_markup=None)
            return

        if idx < 0 or idx >= len(ask.options):
            await cb.answer("Unknown option.", show_alert=True)
            return

        answer = ask.options[idx]
        if store.resolve_by_id(ask_id, answer, via="button"):
            await cb.answer(f"Sent: {answer}")
            if cb.message:
                with contextlib.suppress(Exception):
                    await cb.message.edit_text(
                        f"{cb.message.html_text}\n\n<b>You answered:</b> {escape(answer)}",
                        reply_markup=None,
                    )
        else:
            await cb.answer("Already answered.", show_alert=True)

    @dp.message(F.text)
    async def on_text(message: Message) -> None:
        # Silent reject for unregistered chats
        if get_registry().by_chat(message.chat.id) is None:
            return

        text = (message.text or "").strip()
        if not text or text.startswith("/"):
            return  # ignore commands we don't recognize

        # Reply-to a question we tracked
        if message.reply_to_message:
            replied_id = message.reply_to_message.message_id
            if store.resolve_by_message(message.chat.id, replied_id, text):
                await message.reply("✅ Answer delivered to the agent.")
                return

        # Plain text → oldest pending in THIS chat
        if store.list_for_chat(message.chat.id) and store.resolve_oldest_for_chat(
            message.chat.id, text
        ):
            await message.reply("✅ Answer delivered (oldest pending).")
            return

        await message.answer(
            "Nothing is waiting for an answer right now. Type /pending to see open questions."
        )


async def send_notification(
    bot: Bot, chat_id: int, text: str, session_id: str | None = None, *,
    kind: str = "finished",
) -> None:
    kinds = {
        "finished": "🔔 <b>Agent finished</b>",
        "error":    "⚠️ <b>Agent error</b>",
        "crash":    "💥 <b>Agent crashed</b>",
        "info":     "ℹ️ <b>Notice</b>",  # noqa: RUF001
    }
    prefix = kinds.get(kind, kinds["info"])
    suffix = f"\n\n<i>session {escape(session_id)}</i>" if session_id else ""
    body = escape(text)
    await bot.send_message(chat_id, f"{prefix}\n\n{body}{suffix}")


async def deliver_question(bot: Bot, ask: PendingAsk) -> None:
    markup: InlineKeyboardMarkup | None = None
    if ask.options:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=opt[:64],
                        callback_data=f"{CALLBACK_PREFIX}{ask.ask_id}:{i}",
                    )
                ]
                for i, opt in enumerate(ask.options)
            ]
        )
    tag = f"\n\n<i>session {escape(ask.session_id)}</i>" if ask.session_id else ""
    sent = await bot.send_message(
        ask.chat_id,
        (
            f"❓ <b>Agent is asking</b> "
            f"<code>{ask.ask_id}</code>\n\n{escape(ask.question)}{tag}"
            + ("" if markup else "\n\n<i>Reply to this message to answer.</i>")
        ),
        reply_markup=markup,
    )
    store.attach_message(ask.ask_id, sent.message_id)
