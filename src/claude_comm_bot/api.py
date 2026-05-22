"""HTTP API — multi-tenant. Each request's bearer token resolves to a Telegram chat_id."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .models import AskRequest, AskResponse, HealthResponse, NotifyRequest, RouteCatalogEntry
from .state import store
from .store import User, get_registry
from .telegram_bot import deliver_question, send_notification

log = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api")

ROUTE_CATALOG: list[RouteCatalogEntry] = [
    RouteCatalogEntry(
        id="health", method="GET", path="/api/health",
        description="Liveness probe — returns version and total pending questions",
        auth=False,
    ),
    RouteCatalogEntry(
        id="routes", method="GET", path="/api/routes",
        description="This catalog — every public endpoint",
        auth=False,
    ),
    RouteCatalogEntry(
        id="whoami", method="GET", path="/api/whoami",
        description="Return the Telegram chat_id and username your token is bound to",
        auth=True,
    ),
    RouteCatalogEntry(
        id="notify", method="POST", path="/api/notify",
        description="Send a notification to YOUR Telegram chat (kind: finished|error|crash|info)",
        auth=True,
    ),
    RouteCatalogEntry(
        id="ask", method="POST", path="/api/ask",
        description="Send a question, block until you reply in Telegram, return the answer",
        auth=True,
    ),
    RouteCatalogEntry(
        id="pending", method="GET", path="/api/pending",
        description="List YOUR pending questions",
        auth=True,
    ),
]


def _require_user(authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    user = get_registry().by_token(token)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Unknown or revoked token. Send /start to the bot to register and copy a fresh one.",
        )
    return user


@api_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__, pending_asks=len(store.pending))


@api_router.get("/routes", response_model=list[RouteCatalogEntry])
async def routes() -> list[RouteCatalogEntry]:
    return ROUTE_CATALOG


@api_router.get("/whoami")
async def whoami(user: Annotated[User, Depends(_require_user)]) -> dict[str, object]:
    return {
        "chat_id": user.chat_id,
        "telegram_username": user.telegram_username,
        "telegram_full_name": user.telegram_full_name,
        "created_at": user.created_at,
    }


@api_router.get("/pending")
async def pending(
    user: Annotated[User, Depends(_require_user)],
) -> dict[str, list[dict[str, object]]]:
    return {
        "items": [
            {
                "ask_id": a.ask_id,
                "question": a.question,
                "options": a.options,
                "session_id": a.session_id,
            }
            for a in store.list_for_chat(user.chat_id)
        ]
    }


@api_router.post("/notify", status_code=status.HTTP_202_ACCEPTED)
async def notify(
    payload: NotifyRequest,
    request: Request,
    user: Annotated[User, Depends(_require_user)],
) -> dict[str, str]:
    bot: Bot = request.app.state.bot
    try:
        await send_notification(
            bot, user.chat_id, payload.text, payload.session_id,
            kind=payload.kind or "finished",
        )
    except TelegramAPIError as exc:
        log.warning("Telegram refused notify for chat=%s: %s", user.chat_id, exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Telegram refused message: {exc}. "
            "Open the bot in Telegram and press Start once from the registered account.",
        ) from None
    return {"status": "sent"}


@api_router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    request: Request,
    user: Annotated[User, Depends(_require_user)],
) -> AskResponse:
    settings = get_settings()
    bot: Bot = request.app.state.bot

    ask_obj = store.create(
        chat_id=user.chat_id,
        question=payload.question,
        options=payload.options or [],
        session_id=payload.session_id,
    )
    try:
        await deliver_question(bot, ask_obj)
    except TelegramAPIError as exc:
        store.pop(ask_obj.ask_id)
        log.warning("Telegram refused question for chat=%s: %s", user.chat_id, exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Telegram refused question: {exc}",
        ) from None
    except Exception:
        store.pop(ask_obj.ask_id)
        log.exception("Failed to deliver question to Telegram")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Failed to deliver question") from None

    timeout = payload.timeout if payload.timeout is not None else settings.ask_timeout
    try:
        if timeout and timeout > 0:
            answer, via = await asyncio.wait_for(ask_obj.future, timeout=timeout)
        else:
            answer, via = await ask_obj.future
    except TimeoutError:
        store.pop(ask_obj.ask_id)
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT, "Timed out waiting for reply"
        ) from None
    except asyncio.CancelledError:
        store.pop(ask_obj.ask_id)
        raise HTTPException(status.HTTP_409_CONFLICT, "Cancelled") from None

    return AskResponse(answer=answer, via=via)


def build_app(bot: Bot) -> FastAPI:
    app = FastAPI(title="Claude Communication Bot", version=__version__)
    app.state.bot = bot

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(dist / "index.html")

    return app
