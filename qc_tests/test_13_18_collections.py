"""#13–#18 collections (PDD §3.8, §5.5, §6.11; PR-COL-01…11)."""

from bson import ObjectId

from qc_helpers import (
    COLLECTION_OUT_KEYS,
    REVIEW_LIST_ITEM_KEYS,
    assert_422_shape,
    assert_error,
    assert_iso_naive,
    create_collection,
    create_review,
    random_oid,
)


def assert_collection_out(c):
    assert set(c.keys()) == COLLECTION_OUT_KEYS, c
    assert_iso_naive(c["createdAt"])
    for item in c["reviewIds"]:
        assert set(item.keys()) == REVIEW_LIST_ITEM_KEYS


async def add(client, user, cid, rid):
    return await client.patch(f"/api/collections/{cid}/add-review", json={"reviewId": rid}, headers=user.headers)


async def remove(client, user, cid, rid):
    return await client.patch(f"/api/collections/{cid}/remove-review", json={"reviewId": rid}, headers=user.headers)


# ── #13 POST /api/collections ────────────────────────────────────────────
async def test_ep13_create_201_empty_review_ids_PR_COL_01(client, alice):
    r = await client.post(
        "/api/collections", json={"name": "DSA Practice", "description": "Interview prep"}, headers=alice.headers
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert_collection_out(c)
    assert c["name"] == "DSA Practice" and c["description"] == "Interview prep"
    assert c["reviewIds"] == [] and c["userId"] == alice.id


async def test_ep13_description_optional_PR_COL_01(client, alice):
    r = await client.post("/api/collections", json={"name": "No desc"}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["description"] is None


async def test_ep13_missing_name_422_PDD_3_8(client, alice):
    assert_422_shape(await client.post("/api/collections", json={"description": "x"}, headers=alice.headers), "name")


async def test_ep13_blank_name_400_PR_COL_09_PDD_3_8(client, qc_db, alice):
    for name in ("", "   ", "\t\n"):
        r = await client.post("/api/collections", json={"name": name}, headers=alice.headers)
        assert_error(r, 400, "Collection name cannot be empty")
    assert await qc_db.collections.count_documents({"user_id": ObjectId(alice.id)}) == 0


async def test_ep13_name_trimmed_empty_description_null_PDD_3_8(client, alice):
    r = await client.post("/api/collections", json={"name": "  Trim me  ", "description": ""}, headers=alice.headers)
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Trim me" and r.json()["description"] is None


# ── #14 GET /api/collections ─────────────────────────────────────────────
async def test_ep14_list_own_collections_populated_PR_COL_02(client, alice, bob):
    review = await create_review(client, alice, title="Populated")
    c = await create_collection(client, alice, "Mine")
    await add(client, alice, c["_id"], review["_id"])
    await create_collection(client, bob, "Bob's")
    r = await client.get("/api/collections", headers=alice.headers)
    assert r.status_code == 200
    cols = r.json()
    assert [x["name"] for x in cols] == ["Mine"]
    assert_collection_out(cols[0])
    item = cols[0]["reviewIds"][0]
    assert item["_id"] == review["_id"] and item["title"] == "Populated"


async def test_ep14_empty_list_PR_COL_08(client, alice):
    r = await client.get("/api/collections", headers=alice.headers)
    assert r.status_code == 200 and r.json() == []


async def test_ep14_dead_review_ids_left_out_PDD_3_3(client, qc_db, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    await add(client, alice, c["_id"], review["_id"])
    # Simulate a dead id (e.g. an orphan after a partial cascade, §8 L4).
    await qc_db.reviews.delete_one({"_id": ObjectId(review["_id"])})
    cols = (await client.get("/api/collections", headers=alice.headers)).json()
    assert cols[0]["reviewIds"] == []


# ── #15 PATCH /api/collections/{id} ──────────────────────────────────────
async def test_ep15_rename_and_edit_description_PR_COL_09(client, alice):
    c = await create_collection(client, alice, "Old", "old desc")
    r = await client.patch(f"/api/collections/{c['_id']}", json={"name": "New", "description": "new"}, headers=alice.headers)
    assert r.status_code == 200, r.text
    assert_collection_out(r.json())
    assert r.json()["name"] == "New" and r.json()["description"] == "new"
    r = await client.patch(f"/api/collections/{c['_id']}", json={"name": "Newer"}, headers=alice.headers)
    assert r.json()["name"] == "Newer" and r.json()["description"] == "new"


async def test_ep15_empty_description_clears_PR_COL_09(client, alice):
    c = await create_collection(client, alice, "N", "something")
    r = await client.patch(f"/api/collections/{c['_id']}", json={"description": ""}, headers=alice.headers)
    assert r.status_code == 200
    assert r.json()["description"] in (None, "")
    assert r.json()["name"] == "N"


async def test_ep15_nothing_to_update_400_PDD_3_8(client, alice):
    c = await create_collection(client, alice)
    assert_error(await client.patch(f"/api/collections/{c['_id']}", json={}, headers=alice.headers), 400, "Nothing to update")


async def test_ep15_blank_name_400_PR_COL_09(client, alice):
    c = await create_collection(client, alice, "Keep")
    for name in ("", "   "):
        r = await client.patch(f"/api/collections/{c['_id']}", json={"name": name}, headers=alice.headers)
        assert_error(r, 400, "Collection name cannot be empty")
    cols = (await client.get("/api/collections", headers=alice.headers)).json()
    assert cols[0]["name"] == "Keep"


async def test_ep15_missing_and_other_users_404_PR_Q_02(client, alice, bob):
    c = await create_collection(client, alice)
    assert_error(await client.patch(f"/api/collections/{random_oid()}", json={"name": "x"}, headers=alice.headers), 404, "Collection not found")
    assert_error(await client.patch(f"/api/collections/{c['_id']}", json={"name": "x"}, headers=bob.headers), 404, "Collection not found")


async def test_ep15_updated_at_set_PDD_5_2(client, qc_db, alice):
    c = await create_collection(client, alice)
    before = (await qc_db.collections.find_one({"_id": ObjectId(c["_id"])}))["updated_at"]
    await client.patch(f"/api/collections/{c['_id']}", json={"name": "Renamed"}, headers=alice.headers)
    after = (await qc_db.collections.find_one({"_id": ObjectId(c["_id"])}))["updated_at"]
    assert after > before


# ── #16 PATCH /api/collections/{id}/add-review ───────────────────────────
async def test_ep16_add_review_200_populated_PR_RPT_12(client, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    r = await add(client, alice, c["_id"], review["_id"])
    assert r.status_code == 200, r.text
    assert_collection_out(r.json())
    assert [x["_id"] for x in r.json()["reviewIds"]] == [review["_id"]]


async def test_ep16_add_twice_idempotent_PR_COL_05(client, qc_db, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    await add(client, alice, c["_id"], review["_id"])
    r = await add(client, alice, c["_id"], review["_id"])
    assert r.status_code == 200
    assert len(r.json()["reviewIds"]) == 1
    doc = await qc_db.collections.find_one({"_id": ObjectId(c["_id"])})
    assert doc["review_ids"] == [ObjectId(review["_id"])]


async def test_ep16_review_in_several_collections_PR_COL_10(client, alice):
    review = await create_review(client, alice)
    for name in ("A", "B", "C"):
        c = await create_collection(client, alice, name)
        assert (await add(client, alice, c["_id"], review["_id"])).status_code == 200
    cols = (await client.get("/api/collections", headers=alice.headers)).json()
    assert all(len(c["reviewIds"]) == 1 for c in cols) and len(cols) == 3


async def test_ep16_collection_missing_or_other_users_404_PDD_3_8(client, alice, bob):
    review = await create_review(client, alice)
    c = await create_collection(client, bob)
    assert_error(await add(client, alice, random_oid(), review["_id"]), 404, "Collection not found")
    assert_error(await add(client, alice, c["_id"], review["_id"]), 404, "Collection not found")


async def test_ep16_review_missing_or_other_users_404_PDD_3_8(client, alice, bob):
    c = await create_collection(client, alice)
    bobs_review = await create_review(client, bob)
    assert_error(await add(client, alice, c["_id"], random_oid()), 404, "Review not found")
    assert_error(await add(client, alice, c["_id"], bobs_review["_id"]), 404, "Review not found")


async def test_ep16_body_validation_422_PDD_2_4(client, alice):
    c = await create_collection(client, alice)
    assert_422_shape(await client.patch(f"/api/collections/{c['_id']}/add-review", json={}, headers=alice.headers), "reviewId")
    r = await client.patch(f"/api/collections/{c['_id']}/add-review", json={"reviewId": "nope"}, headers=alice.headers)
    assert_422_shape(r, "reviewId")


async def test_ep16_snake_case_review_id_accepted_PDD_2_3(client, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    r = await client.patch(f"/api/collections/{c['_id']}/add-review", json={"review_id": review["_id"]}, headers=alice.headers)
    assert r.status_code == 200


# ── #17 PATCH /api/collections/{id}/remove-review ────────────────────────
async def test_ep17_remove_review_keeps_review_PR_COL_09_PR_COL_11(client, qc_db, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    await add(client, alice, c["_id"], review["_id"])
    r = await remove(client, alice, c["_id"], review["_id"])
    assert r.status_code == 200, r.text
    assert_collection_out(r.json())
    assert r.json()["reviewIds"] == []
    assert await qc_db.reviews.count_documents({"_id": ObjectId(review["_id"])}) == 1


async def test_ep17_remove_absent_id_noop_200_PDD_3_8(client, alice):
    c = await create_collection(client, alice)
    r = await remove(client, alice, c["_id"], random_oid())
    assert r.status_code == 200 and r.json()["reviewIds"] == []


async def test_ep17_remove_dead_id_clears_it_PDD_3_8(client, qc_db, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    await add(client, alice, c["_id"], review["_id"])
    await qc_db.reviews.delete_one({"_id": ObjectId(review["_id"])})  # dead id left behind
    r = await remove(client, alice, c["_id"], review["_id"])
    assert r.status_code == 200
    doc = await qc_db.collections.find_one({"_id": ObjectId(c["_id"])})
    assert doc["review_ids"] == []


async def test_ep17_collection_missing_or_other_users_404_PDD_3_8(client, alice, bob):
    c = await create_collection(client, bob)
    assert_error(await remove(client, alice, random_oid(), random_oid()), 404, "Collection not found")
    assert_error(await remove(client, alice, c["_id"], random_oid()), 404, "Collection not found")


async def test_ep17_body_validation_422_PDD_2_4(client, alice):
    c = await create_collection(client, alice)
    assert_422_shape(await client.patch(f"/api/collections/{c['_id']}/remove-review", json={}, headers=alice.headers), "reviewId")


# ── #18 DELETE /api/collections/{id} ─────────────────────────────────────
async def test_ep18_delete_keeps_reviews_PR_COL_07_PDD_5_5(client, qc_db, alice):
    review = await create_review(client, alice)
    c = await create_collection(client, alice)
    await add(client, alice, c["_id"], review["_id"])
    r = await client.delete(f"/api/collections/{c['_id']}", headers=alice.headers)
    assert r.status_code == 200
    assert r.json() == {"message": "Collection deleted"}
    assert await qc_db.collections.count_documents({"_id": ObjectId(c["_id"])}) == 0
    assert (await client.get(f"/api/reviews/{review['_id']}", headers=alice.headers)).status_code == 200


async def test_ep18_missing_twice_and_other_users_404_PDD_3_8(client, qc_db, alice, bob):
    c = await create_collection(client, alice)
    assert_error(await client.delete(f"/api/collections/{c['_id']}", headers=bob.headers), 404, "Collection not found")
    assert await qc_db.collections.count_documents({"_id": ObjectId(c["_id"])}) == 1
    assert (await client.delete(f"/api/collections/{c['_id']}", headers=alice.headers)).status_code == 200
    assert_error(await client.delete(f"/api/collections/{c['_id']}", headers=alice.headers), 404, "Collection not found")
