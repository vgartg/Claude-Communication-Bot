"""API integration tests for the multi-tenant flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claude_comm_bot.api import build_app
from claude_comm_bot.state import store
from claude_comm_bot.store import get_registry, init_registry


@dataclass
class StubMessage:
    message_id: int


@dataclass
class StubBot:
    sent: list[tuple[int, str]] = field(default_factory=list)
    next_message_id: int = 1

    async def send_message(self, chat_id: int, text: str, **_: object) -> StubMessage:
        self.sent.append((chat_id, text))
        msg = StubMessage(message_id=self.next_message_id)
        self.next_message_id += 1
        return msg


@pytest.fixture(autouse=True)
def _clean_store():
    store.cancel_all()
    yield
    store.cancel_all()


@pytest.fixture()
def client():
    bot = StubBot()
    app = build_app(bot)  # type: ignore[arg-type]
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_routes_catalog(client: TestClient) -> None:
    r = client.get("/api/routes")
    assert r.status_code == 200
    ids = {entry["id"] for entry in r.json()}
    assert {"health", "routes", "whoami", "notify", "ask", "pending"} <= ids


def test_notify_requires_token(client: TestClient) -> None:
    r = client.post("/api/notify", json={"text": "hi"})
    assert r.status_code == 401


def test_notify_rejects_unknown_token(client: TestClient) -> None:
    r = client.post(
        "/api/notify",
        json={"text": "hi"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401
    assert "Unknown" in r.json()["detail"]


@pytest.mark.asyncio
async def test_token_routes_to_owners_chat(client: TestClient) -> None:
    reg = get_registry()
    alice = await reg.register(1001, "alice", "Alice")
    bob = await reg.register(2002, "bob", "Bob")

    r = client.post(
        "/api/notify",
        json={"text": "ping from alice", "kind": "info"},
        headers={"Authorization": f"Bearer {alice.api_token}"},
    )
    assert r.status_code == 202
    bot: StubBot = client.app.state.bot  # type: ignore[assignment]
    assert bot.sent[-1][0] == 1001

    r = client.post(
        "/api/notify",
        json={"text": "ping from bob"},
        headers={"Authorization": f"Bearer {bob.api_token}"},
    )
    assert r.status_code == 202
    assert bot.sent[-1][0] == 2002


@pytest.mark.asyncio
async def test_whoami(client: TestClient) -> None:
    reg = get_registry()
    alice = await reg.register(1001, "alice", "Alice Liddell")
    r = client.get("/api/whoami", headers={"Authorization": f"Bearer {alice.api_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["chat_id"] == 1001
    assert body["telegram_username"] == "alice"
    assert body["telegram_full_name"] == "Alice Liddell"


@pytest.mark.asyncio
async def test_pending_is_per_user(client: TestClient) -> None:
    reg = get_registry()
    alice = await reg.register(1001, "alice", "Alice")
    bob = await reg.register(2002, "bob", "Bob")

    store.create(chat_id=1001, question="alice question", options=[], session_id="s1")
    store.create(chat_id=2002, question="bob question", options=[], session_id="s2")

    r_alice = client.get("/api/pending", headers={"Authorization": f"Bearer {alice.api_token}"})
    items = r_alice.json()["items"]
    assert len(items) == 1
    assert items[0]["question"] == "alice question"

    r_bob = client.get("/api/pending", headers={"Authorization": f"Bearer {bob.api_token}"})
    items_bob = r_bob.json()["items"]
    assert len(items_bob) == 1
    assert items_bob[0]["question"] == "bob question"


@pytest.mark.asyncio
async def test_registry_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "users.json"
    reg1 = init_registry(path)
    u = await reg1.register(7777, "carol", "Carol")
    token = u.api_token

    reg2 = init_registry(path)
    found = reg2.by_token(token)
    assert found is not None
    assert found.chat_id == 7777


@pytest.mark.asyncio
async def test_rotate_invalidates_old_token() -> None:
    reg = get_registry()
    u = await reg.register(8888, "dave", "Dave")
    old = u.api_token
    new = await reg.rotate(8888)
    assert new is not None
    assert new.api_token != old
    assert reg.by_token(old) is None
    assert reg.by_token(new.api_token).chat_id == 8888
