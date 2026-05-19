import asyncio

import pytest

from claude_comm_bot.state import AskStore


@pytest.mark.asyncio
async def test_resolve_by_message_is_chat_scoped() -> None:
    store = AskStore()
    a = store.create(chat_id=1, question="qa", options=["A"], session_id=None)
    b = store.create(chat_id=2, question="qb", options=["B"], session_id=None)
    # Both end up with message_id 999 in their own chats — the compound key disambiguates.
    store.attach_message(a.ask_id, 999)
    store.attach_message(b.ask_id, 999)

    assert store.resolve_by_message(1, 999, "answer-a") is True
    assert (await a.future) == ("answer-a", "text")
    assert store.resolve_by_message(2, 999, "answer-b") is True
    assert (await b.future) == ("answer-b", "text")


@pytest.mark.asyncio
async def test_resolve_by_button_doesnt_leak_across_chats() -> None:
    store = AskStore()
    a = store.create(1, "qa", ["X"], None)
    _ = store.create(2, "qb", ["Y"], None)
    # Resolving a by id works regardless of chat (ID is unique), but list_for_chat
    # must not include b in chat 1 and vice versa.
    assert {x.ask_id for x in store.list_for_chat(1)} == {a.ask_id}
    assert store.resolve_by_id(a.ask_id, "X", "button") is True
    assert (await a.future) == ("X", "button")


@pytest.mark.asyncio
async def test_oldest_fallback_scoped_to_chat() -> None:
    store = AskStore()
    a1 = store.create(1, "first chat 1", [], None)
    _ = store.create(2, "first chat 2", [], None)
    a2 = store.create(1, "second chat 1", [], None)

    assert store.resolve_oldest_for_chat(1, "ans-1") is True
    assert (await a1.future) == ("ans-1", "text")
    # a2 should still be pending in chat 1
    assert any(x.ask_id == a2.ask_id for x in store.list_for_chat(1))


@pytest.mark.asyncio
async def test_cancel_chat_only_cancels_that_chat() -> None:
    store = AskStore()
    a1 = store.create(1, "q", [], None)
    a2 = store.create(2, "q", [], None)
    n = store.cancel_chat(1)
    assert n == 1
    with pytest.raises(asyncio.CancelledError):
        await a1.future
    # a2 still pending
    assert any(x.ask_id == a2.ask_id for x in store.list_for_chat(2))
