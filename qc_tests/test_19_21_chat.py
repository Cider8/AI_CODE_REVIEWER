"""#19–#21 chat (PDD §3.9, §4.1.2, §4.1.3, §6.12–§6.14; PR-CHAT-01…11)."""

from datetime import timedelta

import pytest
from bson import ObjectId

from app.utils.time import utc_now
from qc_helpers import (
    FakeGemini,
    FakeResponse,
    CHAT_MESSAGE_KEYS,
    CHAT_SESSION_KEYS,
    assert_422_shape,
    assert_error,
    assert_iso_naive,
    create_review,
    random_oid,
    start_chat,
)

LIMIT_MSG = "Daily chat limit of 20 messages reached"


async def ask(client, user, sid, content="Why is line 4 wrong?"):
    return await client.post(f"/api/chat/sessions/{sid}/messages", json={"content": content}, headers=user.headers)


async def chat_count(qc_db, user):
    doc = await qc_db.user_stats.find_one({"user_id": ObjectId(user.id)})
    return doc["daily_chat_count"]


async def set_quota(qc_db, user, count, days_ago=0):
    day = (utc_now() - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
    await qc_db.user_stats.update_one(
        {"user_id": ObjectId(user.id)},
        {"$set": {"daily_chat_count": count, "chat_count_date": day}},
    )


@pytest.fixture
async def chat(client, alice, fake_gemini):
    review = await create_review(client, alice)
    session = await start_chat(client, alice, review["_id"])
    fake_gemini.calls.clear()  # only count calls made by the test itself
    return review, session


# ── #19 POST /api/chat/reviews/{reviewId}/start ──────────────────────────
async def test_ep19_start_201_shape_full_quota_PR_CHAT_01_PR_CHAT_07(client, alice):
    review = await create_review(client, alice)
    r = await client.post(f"/api/chat/reviews/{review['_id']}/start", headers=alice.headers)
    assert r.status_code == 201, r.text
    s = r.json()
    assert set(s.keys()) == CHAT_SESSION_KEYS
    assert s["reviewId"] == review["_id"] and s["userId"] == alice.id
    assert s["remainingMessagesToday"] == 20
    assert_iso_naive(s["createdAt"])


async def test_ep19_start_twice_resumes_same_session_201_PR_CHAT_03_PDD_L9(client, qc_db, alice):
    review = await create_review(client, alice)
    a = await start_chat(client, alice, review["_id"])
    r = await client.post(f"/api/chat/reviews/{review['_id']}/start", headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["_id"] == a["_id"]
    assert await qc_db.chat_sessions.count_documents({"review_id": ObjectId(review["_id"])}) == 1


async def test_ep19_remaining_reflects_usage_PR_CHAT_07(client, qc_db, alice, chat):
    review, session = chat
    await ask(client, alice, session["_id"])
    await ask(client, alice, session["_id"])
    s = await start_chat(client, alice, review["_id"])
    assert s["remainingMessagesToday"] == 18


async def test_ep19_remaining_full_after_day_rollover_PR_CHAT_06_PDD_6_12(client, qc_db, alice, chat):
    review, _ = chat
    await set_quota(qc_db, alice, 20, days_ago=1)
    s = await start_chat(client, alice, review["_id"])
    assert s["remainingMessagesToday"] == 20


async def test_ep19_review_missing_or_other_users_404_PR_Q_02(client, alice, bob):
    review = await create_review(client, alice)
    assert_error(await client.post(f"/api/chat/reviews/{random_oid()}/start", headers=alice.headers), 404, "Review not found")
    assert_error(await client.post(f"/api/chat/reviews/{review['_id']}/start", headers=bob.headers), 404, "Review not found")


# ── #20 GET /api/chat/sessions/{sessionId}/messages ──────────────────────
async def test_ep20_empty_history_PR_CHAT_11(client, alice, chat):
    _, session = chat
    r = await client.get(f"/api/chat/sessions/{session['_id']}/messages", headers=alice.headers)
    assert r.status_code == 200 and r.json() == []


async def test_ep20_history_oldest_first_alternating_PR_CHAT_03(client, alice, chat, fake_gemini):
    _, session = chat
    fake_gemini.push("A1", "A2")
    await ask(client, alice, session["_id"], "Q1")
    await ask(client, alice, session["_id"], "Q2")
    r = await client.get(f"/api/chat/sessions/{session['_id']}/messages", headers=alice.headers)
    msgs = r.json()
    assert [(m["role"], m["content"]) for m in msgs] == [("user", "Q1"), ("model", "A1"), ("user", "Q2"), ("model", "A2")]
    for m in msgs:
        assert set(m.keys()) == CHAT_MESSAGE_KEYS and m["sessionId"] == session["_id"]
        assert_iso_naive(m["createdAt"])


async def test_ep20_session_missing_or_other_users_404_PR_Q_01(client, alice, bob, chat):
    _, session = chat
    assert_error(await client.get(f"/api/chat/sessions/{random_oid()}/messages", headers=alice.headers), 404, "Chat session not found")
    assert_error(await client.get(f"/api/chat/sessions/{session['_id']}/messages", headers=bob.headers), 404, "Chat session not found")


# ── #21 POST /api/chat/sessions/{sessionId}/messages ─────────────────────
async def test_ep21_ask_201_shape_and_quota_PR_CHAT_02_PR_CHAT_06(client, qc_db, alice, chat, fake_gemini):
    _, session = chat
    r = await ask(client, alice, session["_id"], "Why is line 4 an off-by-one?")
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == {"userMessage", "reply", "remainingMessagesToday"}
    assert set(body["userMessage"].keys()) == CHAT_MESSAGE_KEYS
    assert set(body["reply"].keys()) == CHAT_MESSAGE_KEYS
    assert body["userMessage"]["role"] == "user" and body["userMessage"]["content"] == "Why is line 4 an off-by-one?"
    assert body["reply"]["role"] == "model" and body["reply"]["content"] == FakeGemini.CHAT_ANSWER
    assert body["remainingMessagesToday"] == 19
    assert body["userMessage"]["createdAt"] <= body["reply"]["createdAt"]
    assert await chat_count(qc_db, alice) == 1


async def test_ep21_model_receives_context_and_question_PDD_4_1_2(client, alice, chat, fake_gemini):
    review, session = chat
    await ask(client, alice, session["_id"], "First?")
    contents = fake_gemini.calls[-1]
    assert contents[0]["role"] == "user" and review["originalCode"] in contents[0]["parts"][0]
    assert review["summary"] in contents[0]["parts"][0]
    assert contents[1] == {"role": "model", "parts": ["Understood. Ask me about this code."]}
    assert contents[-1] == {"role": "user", "parts": ["First?"]}
    assert len(contents) == 3


async def test_ep21_history_replay_capped_at_6_PR_CHAT_04_PDD_4_1_3(client, alice, chat, fake_gemini):
    _, session = chat
    for i in range(5):
        fake_gemini.push(f"A{i}")
        assert (await ask(client, alice, session["_id"], f"Q{i}")).status_code == 201
    await ask(client, alice, session["_id"], "Q5")
    contents = fake_gemini.calls[-1]
    assert len(contents) == 2 + 6 + 1
    replayed = [(c["role"], c["parts"][0]) for c in contents[2:-1]]
    assert replayed == [("user", "Q2"), ("model", "A2"), ("user", "Q3"), ("model", "A3"), ("user", "Q4"), ("model", "A4")]


@pytest.mark.parametrize("content", ["", "x" * 4001])
async def test_ep21_content_length_422_PR_CHAT_05(client, qc_db, alice, chat, fake_gemini, content):
    _, session = chat
    r = await ask(client, alice, session["_id"], content)
    assert_422_shape(r, "content")
    assert fake_gemini.calls == [] and await chat_count(qc_db, alice) == 0


async def test_ep21_content_4000_chars_ok_PR_CHAT_05(client, alice, chat):
    _, session = chat
    assert (await ask(client, alice, session["_id"], "y" * 4000)).status_code == 201


async def test_ep21_missing_content_422_PDD_2_4(client, alice, chat):
    _, session = chat
    r = await client.post(f"/api/chat/sessions/{session['_id']}/messages", json={}, headers=alice.headers)
    assert_422_shape(r, "content")


async def test_ep21_session_missing_or_other_users_404_PR_Q_01(client, qc_db, alice, bob, chat, fake_gemini):
    _, session = chat
    assert_error(await ask(client, alice, random_oid()), 404, "Chat session not found")
    assert_error(await ask(client, bob, session["_id"]), 404, "Chat session not found")
    assert fake_gemini.calls == []
    assert await chat_count(qc_db, bob) == 0


async def test_ep21_review_gone_404_PDD_3_9(client, qc_db, alice, chat, fake_gemini):
    review, session = chat
    # Orphaned session (review removed outside the cascade, §8 L4).
    await qc_db.reviews.delete_one({"_id": ObjectId(review["_id"])})
    assert_error(await ask(client, alice, session["_id"]), 404, "Review for this session no longer exists")
    assert fake_gemini.calls == [] and await chat_count(qc_db, alice) == 0


async def test_ep21_session_deleted_with_review_404_PR_CHAT_03(client, alice, chat):
    review, session = chat
    await client.delete(f"/api/reviews/{review['_id']}", headers=alice.headers)
    assert_error(await ask(client, alice, session["_id"]), 404, "Chat session not found")


async def test_ep21_daily_limit_429_PR_CHAT_06_PR_CHAT_08(client, qc_db, alice, chat, fake_gemini):
    _, session = chat
    await set_quota(qc_db, alice, 19)
    r = await ask(client, alice, session["_id"])
    assert r.status_code == 201 and r.json()["remainingMessagesToday"] == 0
    r = await ask(client, alice, session["_id"])
    assert_error(r, 429, LIMIT_MSG)
    assert len(fake_gemini.calls) == 1  # no model call once the limit is hit
    assert await chat_count(qc_db, alice) == 20
    msgs = (await client.get(f"/api/chat/sessions/{session['_id']}/messages", headers=alice.headers)).json()
    assert len(msgs) == 2


async def test_ep21_limit_is_per_user_across_reviews_PR_CHAT_06(client, qc_db, alice, bob, fake_gemini):
    r1 = await create_review(client, alice)
    r2 = await create_review(client, alice)
    s1 = await start_chat(client, alice, r1["_id"])
    s2 = await start_chat(client, alice, r2["_id"])
    await set_quota(qc_db, alice, 19)
    assert (await ask(client, alice, s1["_id"])).status_code == 201
    assert_error(await ask(client, alice, s2["_id"]), 429, LIMIT_MSG)
    # Another user is unaffected.
    rb = await create_review(client, bob)
    sb = await start_chat(client, bob, rb["_id"])
    assert (await ask(client, bob, sb["_id"])).status_code == 201


async def test_ep21_day_rollover_resets_counter_PR_CHAT_06_PDD_6_14(client, qc_db, alice, chat):
    _, session = chat
    await set_quota(qc_db, alice, 20, days_ago=1)
    r = await ask(client, alice, session["_id"])
    assert r.status_code == 201, r.text
    assert r.json()["remainingMessagesToday"] == 19
    assert await chat_count(qc_db, alice) == 1


@pytest.mark.parametrize(
    "failure,detail",
    [
        (TimeoutError("deadline"), "AI service did not respond"),
        (RuntimeError("quota"), "AI service did not respond"),
        ("", "AI returned an empty response"),
        ("   \n ", "AI returned an empty response"),
    ],
    ids=["timeout", "provider_error", "empty", "whitespace"],
)
async def test_ep21_ai_failure_502_refund_nothing_saved_PR_CHAT_09_PDD_3_9(client, qc_db, alice, chat, fake_gemini, failure, detail):
    _, session = chat
    await ask(client, alice, session["_id"], "ok question")
    fake_gemini.push(failure)
    r = await ask(client, alice, session["_id"], "this one fails")
    assert_error(r, 502, detail)
    assert await chat_count(qc_db, alice) == 1  # refunded
    msgs = (await client.get(f"/api/chat/sessions/{session['_id']}/messages", headers=alice.headers)).json()
    assert [m["content"] for m in msgs if m["role"] == "user"] == ["ok question"]
    s = (await client.post(f"/api/chat/reviews/{chat[0]['_id']}/start", headers=alice.headers)).json()
    assert s["remainingMessagesToday"] == 19


async def test_ep21_ai_failure_at_limit_edge_refund_allows_retry_PR_CHAT_09(client, qc_db, alice, chat, fake_gemini):
    _, session = chat
    await set_quota(qc_db, alice, 19)
    fake_gemini.push(TimeoutError())
    assert (await ask(client, alice, session["_id"])).status_code == 502
    r = await ask(client, alice, session["_id"])
    assert r.status_code == 201 and r.json()["remainingMessagesToday"] == 0


async def test_ep21_blocked_reply_502_empty_response_refund_PDD_3_9(client, qc_db, alice, chat, fake_gemini):
    """The Gemini SDK raises ValueError from response.text for a blocked reply.
    PDD v1.4 §3.9: 502 "AI returned an empty response", quota refunded, no
    SDK text in the body (PRD §7)."""
    _, session = chat
    fake_gemini.push(FakeResponse(text_error=ValueError(
        "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`")))
    r = await ask(client, alice, session["_id"])
    assert_error(r, 502, "AI returned an empty response")
    assert "Invalid operation" not in r.text
    assert await chat_count(qc_db, alice) == 0
