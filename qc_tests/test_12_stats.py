"""#12 GET /api/stats (PDD §3.7, §5.4, §6.10; PR-DSH-01…08)."""

import json

from bson import ObjectId

from qc_helpers import REVIEW_LIST_ITEM_KEYS, STATS_KEYS, assert_iso_naive, create_review, valid_review_json


def review_with(score, bug_categories=(), sec_types=()):
    return json.dumps(valid_review_json(
        overall_score=score,
        bugs=[{"severity": "low", "category": c, "description": "d", "suggestion": "s"} for c in bug_categories],
        security_issues=[{"type": t, "description": "d", "fix": "f"} for t in sec_types],
    ))


async def get_stats(client, user):
    r = await client.get("/api/stats", headers=user.headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_ep12_new_user_empty_stats_shape_PR_DSH_05_PDD_3_7(client, alice):
    body = await get_stats(client, alice)
    assert set(body.keys()) == {"stats", "recentReviews"}
    s = body["stats"]
    assert set(s.keys()) == STATS_KEYS  # chat-quota fields not returned
    assert s["userId"] == alice.id
    assert (s["totalReviews"], s["averageScore"], s["totalBugsFound"], s["totalSecurityIssuesFound"]) == (0, 0.0, 0, 0)
    assert s["scoreHistory"] == [] and s["languageBreakdown"] == [] and s["commonWeaknesses"] == []
    assert_iso_naive(s["updatedAt"])
    assert body["recentReviews"] == []


async def test_ep12_stats_created_on_demand_PDD_3_7(client, qc_db, alice):
    await qc_db.user_stats.delete_many({"user_id": ObjectId(alice.id)})
    body = await get_stats(client, alice)
    assert body["stats"]["totalReviews"] == 0
    assert await qc_db.user_stats.count_documents({"user_id": ObjectId(alice.id)}) == 1


async def test_ep12_headline_figures_PR_DSH_01_PDD_5_4(client, alice, fake_gemini):
    fake_gemini.push(
        review_with(70, ["A", "B"], ["X"]),
        review_with(71, ["C"], []),
        review_with(73, [], ["Y", "Z"]),
    )
    for lang in ("Python", "Go", "Python"):
        await create_review(client, alice, language=lang)
    s = (await get_stats(client, alice))["stats"]
    assert s["totalReviews"] == 3
    assert s["averageScore"] == 71.33  # 2 decimal places
    assert s["totalBugsFound"] == 3
    assert s["totalSecurityIssuesFound"] == 3


async def test_ep12_score_history_oldest_first_PR_DSH_02(client, alice, fake_gemini):
    fake_gemini.push(review_with(10), review_with(20), review_with(30))
    for _ in range(3):
        await create_review(client, alice)
    s = (await get_stats(client, alice))["stats"]
    assert [p["score"] for p in s["scoreHistory"]] == [10, 20, 30]
    for p in s["scoreHistory"]:
        assert set(p.keys()) == {"score", "date"}
        assert_iso_naive(p["date"])


async def test_ep12_language_breakdown_most_used_first_PR_DSH_03(client, alice):
    for lang in ("Go", "Python", "Python", "Rust", "Python", "Go"):
        await create_review(client, alice, language=lang)
    s = (await get_stats(client, alice))["stats"]
    assert s["languageBreakdown"][0] == {"language": "Python", "count": 3}
    assert s["languageBreakdown"][1] == {"language": "Go", "count": 2}
    assert s["languageBreakdown"][2] == {"language": "Rust", "count": 1}


async def test_ep12_recent_reviews_5_newest_first_PR_DSH_04(client, alice):
    ids = [(await create_review(client, alice, title=f"R{i}"))["_id"] for i in range(7)]
    body = await get_stats(client, alice)
    assert [r["_id"] for r in body["recentReviews"]] == list(reversed(ids))[:5]
    for r in body["recentReviews"]:
        assert set(r.keys()) == REVIEW_LIST_ITEM_KEYS


async def test_ep12_common_weaknesses_rules_PR_DSH_07_PDD_5_4(client, alice, fake_gemini):
    fake_gemini.push(
        # "Off-by-one error" five times in ONE review counts once.
        review_with(50, ["Off-by-one error"] * 5 + ["Null handling"], ["SQL Injection"]),
        review_with(50, ["off-by-one   ERROR", "Race condition"], ["sql injection"]),
        review_with(50, ["Null handling"], []),
        review_with(50, ["One-off thing"], []),
    )
    for _ in range(4):
        await create_review(client, alice)
    s = (await get_stats(client, alice))["stats"]
    weak = s["commonWeaknesses"]
    norm = [" ".join(w.split()).lower() for w in weak]
    assert set(norm) == {"off-by-one error", "null handling", "sql injection"}, weak
    assert len(norm) == len(set(norm))  # case/space variants merged
    assert "one-off thing" not in norm and "race condition" not in norm


async def test_ep12_common_weaknesses_max_5_most_frequent_first_PR_DSH_07(client, alice, fake_gemini):
    labels = ["W1", "W2", "W3", "W4", "W5", "W6"]
    # W1 in 4 reviews, W2 in 3, the rest in 2.
    fake_gemini.push(
        review_with(50, labels),
        review_with(50, labels),
        review_with(50, ["W1", "W2"]),
        review_with(50, ["W1"]),
    )
    for _ in range(4):
        await create_review(client, alice)
    weak = (await get_stats(client, alice))["stats"]["commonWeaknesses"]
    assert len(weak) == 5
    assert weak[:2] == ["W1", "W2"]


async def test_ep12_figures_follow_deletes_PR_DSH_08_PDD_5_4(client, alice, fake_gemini):
    fake_gemini.push(review_with(40, ["Leak"]), review_with(80, ["Leak"]))
    r1 = await create_review(client, alice, language="C")
    await create_review(client, alice, language="Go")
    before = (await get_stats(client, alice))["stats"]
    assert before["commonWeaknesses"] == ["Leak"] and before["averageScore"] == 60.0
    assert (await client.delete(f"/api/reviews/{r1['_id']}", headers=alice.headers)).status_code == 200
    after = (await get_stats(client, alice))["stats"]
    assert after["totalReviews"] == 1 and after["averageScore"] == 80.0
    assert after["commonWeaknesses"] == []
    assert after["languageBreakdown"] == [{"language": "Go", "count": 1}]
    assert [p["score"] for p in after["scoreHistory"]] == [80]


async def test_ep12_recompute_keeps_chat_quota_PDD_5_4(client, qc_db, alice):
    await qc_db.user_stats.update_one({"user_id": ObjectId(alice.id)}, {"$set": {"daily_chat_count": 7}})
    await create_review(client, alice)
    doc = await qc_db.user_stats.find_one({"user_id": ObjectId(alice.id)})
    assert doc["daily_chat_count"] == 7


async def test_ep12_only_own_figures_PR_Q_01(client, alice, bob):
    await create_review(client, alice)
    s = (await get_stats(client, bob))["stats"]
    assert s["totalReviews"] == 0 and s["userId"] == bob.id
