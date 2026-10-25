"""#8–#11 reviews (PDD §3.6, §4.1.1, §5.5, §6.6–§6.9; PR-REV, PR-RPT, PR-HIS)."""

import json

import pytest
from bson import ObjectId

from qc_helpers import (
    FakeGemini,
    FakeResponse,
    REVIEW_DETAIL_KEYS,
    REVIEW_LIST_ITEM_KEYS,
    assert_422_shape,
    assert_error,
    assert_iso_naive,
    create_collection,
    create_review,
    random_oid,
    start_chat,
    valid_review_json,
)


async def stats_of(client, user):
    r = await client.get("/api/stats", headers=user.headers)
    assert r.status_code == 200
    return r.json()["stats"]


# ── #8 POST /api/reviews ─────────────────────────────────────────────────
async def test_ep08_create_review_201_detail_shape_PR_REV_08_PDD_3_3(client, alice, fake_gemini):
    r = await client.post(
        "/api/reviews",
        json={"title": "Binary Search", "language": "Python", "originalCode": "def bs(a, x): pass"},
        headers=alice.headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == REVIEW_DETAIL_KEYS
    assert body["userId"] == alice.id and body["title"] == "Binary Search"
    assert body["originalCode"] == "def bs(a, x): pass" and body["language"] == "Python"
    assert body["overallScore"] == 78
    assert body["bugs"][0] == {
        "line": 4, "category": "Off-by-one error", "severity": "medium",
        "description": "Loop bound is wrong.", "suggestion": "Use < instead of <=.",
    }
    assert body["securityIssues"][0]["type"] == "Hardcoded Secret"
    assert body["securityIssues"][0]["line"] is None
    assert body["performanceIssues"][0]["impact"] == "low"
    assert body["complexity"] == {"time": "O(log n)", "space": "O(1)"}
    assert body["refactoredCode"] and body["tags"] == ["searching", "arrays"]
    assert_iso_naive(body["createdAt"])
    # Exactly one model call, and the prompt carries the code and language.
    assert len(fake_gemini.calls) == 1
    assert "def bs(a, x): pass" in fake_gemini.calls[0] and "Python" in fake_gemini.calls[0]


async def test_ep08_title_defaults_to_language_review_PR_REV_03(client, alice):
    r = await client.post(
        "/api/reviews", json={"language": "Go", "originalCode": "package main"}, headers=alice.headers
    )
    assert r.status_code == 201
    assert r.json()["title"] == "Go Review"


async def test_ep08_snake_case_input_accepted_PDD_2_3(client, alice):
    r = await client.post(
        "/api/reviews", json={"language": "Go", "original_code": "package main"}, headers=alice.headers
    )
    assert r.status_code == 201


async def test_ep08_fenced_json_is_accepted_PDD_4_1_1(client, alice, fake_gemini):
    fake_gemini.push("```json\n" + json.dumps(valid_review_json(overall_score=55)) + "\n```")
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": "x"}, headers=alice.headers)
    assert r.status_code == 201, r.text
    assert r.json()["overallScore"] == 55


async def test_ep08_review_without_bug_category_ok_PDD_3_3(client, alice, fake_gemini):
    data = valid_review_json()
    del data["bugs"][0]["category"]
    fake_gemini.push(json.dumps(data))
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": "x"}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["bugs"][0]["category"] is None


async def test_ep08_empty_code_422_PR_REV_04(client, alice, fake_gemini):
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": ""}, headers=alice.headers)
    assert_422_shape(r, "originalCode")
    assert fake_gemini.calls == []


async def test_ep08_missing_language_422_PDD_3_6(client, alice):
    r = await client.post("/api/reviews", json={"originalCode": "x"}, headers=alice.headers)
    assert_422_shape(r, "language")


async def _assert_nothing_saved(client, qc_db, user, before_stats):
    assert await qc_db.reviews.count_documents({"user_id": ObjectId(user.id)}) == 0
    assert await stats_of(client, user) == before_stats


NOT_JSON = "AI response was not valid JSON"
BAD_FORMAT = "AI response did not match the expected format"
EMPTY = "AI returned an empty response"
DETAILS_502_EP08 = {EMPTY, NOT_JSON, BAD_FORMAT, "AI service did not respond"}  # PDD v1.4 §3.6

BAD_AI_OUTPUTS = {
    "not_json": ("Sure! Here is my review: looks great.", NOT_JSON),
    "truncated_json": ('{"summary": "x", "overall_score": 5', NOT_JSON),
    "json_array": ("[1, 2, 3]", BAD_FORMAT),
    "score_over_100": (json.dumps(valid_review_json(overall_score=150)), BAD_FORMAT),
    "score_negative": (json.dumps(valid_review_json(overall_score=-1)), BAD_FORMAT),
    "bad_severity": (json.dumps(valid_review_json(bugs=[{"severity": "urgent", "description": "d", "suggestion": "s"}])), BAD_FORMAT),
    "bad_impact": (json.dumps(valid_review_json(performance_issues=[{"description": "d", "suggestion": "s", "impact": "huge"}])), BAD_FORMAT),
    "missing_summary": (json.dumps({k: v for k, v in valid_review_json().items() if k != "summary"}), BAD_FORMAT),
    "missing_complexity": (json.dumps({k: v for k, v in valid_review_json().items() if k != "complexity"}), BAD_FORMAT),
    "bugs_not_list": (json.dumps(valid_review_json(bugs="none")), BAD_FORMAT),
    "empty_text": ("", EMPTY),
    "whitespace_text": ("  \n ", EMPTY),
}


@pytest.mark.parametrize("case", list(BAD_AI_OUTPUTS), ids=list(BAD_AI_OUTPUTS))
async def test_ep08_bad_ai_output_502_exact_detail_nothing_saved_PR_REV_07_PDD_3_6(client, qc_db, users, fake_gemini, case):
    user = await users.create("BadAI")
    before = await stats_of(client, user)
    text, expected = BAD_AI_OUTPUTS[case]
    fake_gemini.push(text)
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": "x"}, headers=user.headers)
    assert_error(r, 502, expected)
    await _assert_nothing_saved(client, qc_db, user, before)


@pytest.mark.parametrize(
    "exc",
    [TimeoutError("deadline"), ConnectionError("reset"), RuntimeError("quota exceeded")],
    ids=["timeout", "connection", "provider_error"],
)
async def test_ep08_provider_error_502_ai_service_did_not_respond_PDD_L1(client, qc_db, users, fake_gemini, exc):
    user = await users.create("ProvErr")
    before = await stats_of(client, user)
    fake_gemini.push(exc)
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": "x"}, headers=user.headers)
    assert_error(r, 502, "AI service did not respond")
    await _assert_nothing_saved(client, qc_db, user, before)


async def test_ep08_blocked_reply_502_empty_response_no_sdk_text_PDD_3_6(client, qc_db, users, fake_gemini):
    """The Gemini SDK raises ValueError from response.text when a reply is
    blocked (safety/recitation). PDD v1.4 §3.6: 502 "AI returned an empty
    response"; SDK text is never passed through (PRD §7)."""
    user = await users.create("Blocked")
    fake_gemini.push(FakeResponse(text_error=ValueError(
        "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`")))
    r = await client.post("/api/reviews", json={"language": "Python", "originalCode": "x"}, headers=user.headers)
    assert_error(r, 502, EMPTY)
    assert "Invalid operation" not in r.text
    await _assert_nothing_saved(client, qc_db, user, await stats_of(client, user))


async def test_ep08_stats_recomputed_after_create_PR_REV_08_PDD_5_4(client, alice, fake_gemini):
    fake_gemini.push(json.dumps(valid_review_json(overall_score=60)), json.dumps(valid_review_json(overall_score=81)))
    await create_review(client, alice, language="Python")
    await create_review(client, alice, language="Go")
    s = await stats_of(client, alice)
    assert s["totalReviews"] == 2
    assert s["averageScore"] == 70.5
    assert s["totalBugsFound"] == 2 and s["totalSecurityIssuesFound"] == 2


# ── #9 GET /api/reviews ──────────────────────────────────────────────────
async def test_ep09_list_empty_pages_zero_PR_HIS_07_PDD_3_6(client, alice):
    r = await client.get("/api/reviews", headers=alice.headers)
    assert r.status_code == 200
    assert r.json() == {"reviews": [], "total": 0, "page": 1, "pages": 0}


async def test_ep09_list_newest_first_and_item_shape_PR_HIS_01(client, alice):
    ids = [(await create_review(client, alice, title=f"R{i}"))["_id"] for i in range(3)]
    r = await client.get("/api/reviews", headers=alice.headers)
    body = r.json()
    assert body["total"] == 3 and body["pages"] == 1 and body["page"] == 1
    assert [x["_id"] for x in body["reviews"]] == list(reversed(ids))
    for item in body["reviews"]:
        assert set(item.keys()) == REVIEW_LIST_ITEM_KEYS
        assert_iso_naive(item["createdAt"])


async def test_ep09_pagination_default_10_PR_HIS_02(client, users, fake_gemini):
    user = await users.create("Pager")
    for i in range(12):
        await create_review(client, user, title=f"P{i:02d}")
    p1 = (await client.get("/api/reviews", headers=user.headers)).json()
    assert len(p1["reviews"]) == 10 and p1["total"] == 12 and p1["pages"] == 2
    p2 = (await client.get("/api/reviews?page=2", headers=user.headers)).json()
    assert len(p2["reviews"]) == 2 and p2["page"] == 2
    assert {x["_id"] for x in p1["reviews"]}.isdisjoint({x["_id"] for x in p2["reviews"]})
    p3 = (await client.get("/api/reviews?page=3", headers=user.headers)).json()
    assert p3["reviews"] == [] and p3["total"] == 12
    lim = (await client.get("/api/reviews?limit=5", headers=user.headers)).json()
    assert len(lim["reviews"]) == 5 and lim["pages"] == 3


@pytest.mark.parametrize("qs", ["page=0", "page=-1", "limit=0", "limit=101", "page=abc", "limit=x"])
async def test_ep09_out_of_range_page_limit_422_PDD_3_6(client, alice, qs):
    r = await client.get(f"/api/reviews?{qs}", headers=alice.headers)
    assert_422_shape(r)


async def test_ep09_limit_100_allowed_PDD_3_6(client, alice):
    assert (await client.get("/api/reviews?limit=100", headers=alice.headers)).status_code == 200


async def test_ep09_search_case_insensitive_substring_PR_HIS_03(client, alice):
    await create_review(client, alice, title="Binary Search Tree")
    await create_review(client, alice, title="Bubble sort")
    r = (await client.get("/api/reviews?search=SEARCH", headers=alice.headers)).json()
    assert [x["title"] for x in r["reviews"]] == ["Binary Search Tree"]
    r = (await client.get("/api/reviews?search=b", headers=alice.headers)).json()
    assert r["total"] == 2


@pytest.mark.parametrize("pattern", ["(", "a+(", "[", ".*", "(a+)+$", "\\"])
async def test_ep09_search_regex_escaped_PDD_7(client, alice, pattern):
    await create_review(client, alice, title="plain title")
    r = await client.get("/api/reviews", params={"search": pattern}, headers=alice.headers)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0  # treated literally, so ".*" matches nothing


async def test_ep09_search_literal_special_chars_match_PDD_7(client, alice):
    await create_review(client, alice, title="C++ (templates)")
    r = await client.get("/api/reviews", params={"search": "++ (t"}, headers=alice.headers)
    assert r.json()["total"] == 1


async def test_ep09_language_filter_exact_PR_HIS_04(client, alice):
    await create_review(client, alice, language="Python")
    await create_review(client, alice, language="JavaScript")
    await create_review(client, alice, language="Java")
    r = (await client.get("/api/reviews?language=Java", headers=alice.headers)).json()
    assert r["total"] == 1 and r["reviews"][0]["language"] == "Java"
    r = (await client.get("/api/reviews?language=java", headers=alice.headers)).json()
    assert r["total"] == 0
    r = (await client.get("/api/reviews?language=Java&search=Binary", headers=alice.headers)).json()
    assert r["total"] == 1


async def test_ep09_only_own_reviews_listed_PR_Q_01(client, alice, bob):
    await create_review(client, alice, title="Alice only")
    r = (await client.get("/api/reviews", headers=bob.headers)).json()
    assert r["total"] == 0


# ── #10 GET /api/reviews/{id} ────────────────────────────────────────────
async def test_ep10_get_review_200_PR_RPT_01(client, alice):
    created = await create_review(client, alice)
    r = await client.get(f"/api/reviews/{created['_id']}", headers=alice.headers)
    assert r.status_code == 200
    got = r.json()
    # createdAt precision is checked separately in test_timestamps.py
    assert {k: v for k, v in got.items() if k != "createdAt"} == {k: v for k, v in created.items() if k != "createdAt"}
    assert got["createdAt"][:19] == created["createdAt"][:19]


async def test_ep10_missing_review_404_PR_RPT_13(client, alice):
    assert_error(await client.get(f"/api/reviews/{random_oid()}", headers=alice.headers), 404, "Review not found")


async def test_ep10_other_users_review_404_same_message_PR_RPT_13_PR_Q_02(client, alice, bob):
    created = await create_review(client, alice)
    assert_error(await client.get(f"/api/reviews/{created['_id']}", headers=bob.headers), 404, "Review not found")


# ── #11 DELETE /api/reviews/{id} ─────────────────────────────────────────
async def test_ep11_delete_review_cascade_PR_RPT_11_PDD_5_5(client, qc_db, alice, fake_gemini):
    keep = await create_review(client, alice, title="Keep")
    doomed = await create_review(client, alice, title="Doomed")
    c1 = await create_collection(client, alice, "C1")
    c2 = await create_collection(client, alice, "C2")
    for c in (c1, c2):
        for rid in (keep["_id"], doomed["_id"]):
            r = await client.patch(f"/api/collections/{c['_id']}/add-review", json={"reviewId": rid}, headers=alice.headers)
            assert r.status_code == 200
    session = await start_chat(client, alice, doomed["_id"])
    keep_session = await start_chat(client, alice, keep["_id"])
    for sid in (session["_id"], keep_session["_id"]):
        r = await client.post(f"/api/chat/sessions/{sid}/messages", json={"content": "q"}, headers=alice.headers)
        assert r.status_code == 201

    r = await client.delete(f"/api/reviews/{doomed['_id']}", headers=alice.headers)
    assert r.status_code == 200
    assert r.json() == {"message": "Review deleted"}

    did, sid = ObjectId(doomed["_id"]), ObjectId(session["_id"])
    assert await qc_db.reviews.count_documents({"_id": did}) == 0
    assert await qc_db.chat_sessions.count_documents({"_id": sid}) == 0
    assert await qc_db.chat_messages.count_documents({"session_id": sid}) == 0
    assert await qc_db.collections.count_documents({"review_ids": did}) == 0
    # Kept data untouched.
    assert await qc_db.chat_messages.count_documents({"session_id": ObjectId(keep_session["_id"])}) == 2
    cols = (await client.get("/api/collections", headers=alice.headers)).json()
    assert all([x["_id"] for x in c["reviewIds"]] == [keep["_id"]] for c in cols)
    # Stats recomputed (PR-DSH-08).
    s = await stats_of(client, alice)
    assert s["totalReviews"] == 1 and len(s["scoreHistory"]) == 1
    assert_error(await client.get(f"/api/reviews/{doomed['_id']}", headers=alice.headers), 404, "Review not found")


async def test_ep11_delete_missing_404_PDD_3_6(client, alice):
    assert_error(await client.delete(f"/api/reviews/{random_oid()}", headers=alice.headers), 404, "Review not found")


async def test_ep11_delete_twice_404_PDD_3_6(client, alice):
    created = await create_review(client, alice)
    assert (await client.delete(f"/api/reviews/{created['_id']}", headers=alice.headers)).status_code == 200
    assert_error(await client.delete(f"/api/reviews/{created['_id']}", headers=alice.headers), 404, "Review not found")


async def test_ep11_delete_other_users_review_404_untouched_PR_Q_01(client, qc_db, alice, bob):
    created = await create_review(client, alice)
    assert_error(await client.delete(f"/api/reviews/{created['_id']}", headers=bob.headers), 404, "Review not found")
    assert await qc_db.reviews.count_documents({"_id": ObjectId(created["_id"])}) == 1
