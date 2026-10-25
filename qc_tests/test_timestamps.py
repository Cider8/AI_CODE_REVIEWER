"""PDD §3.1: one resource has one timestamp. The value returned by a create
call must equal the value later read back (MongoDB stores milliseconds, so a
create response carrying microseconds reports a time that is never stored)."""

from qc_helpers import create_collection, create_review, start_chat


async def test_ep02_vs_ep04_user_createdAt_consistent_PDD_3_1(client, users):
    r = await client.post("/api/auth/register", json={"name": "T", "email": f"ts.{__import__('uuid').uuid4().hex}@example.com", "password": "Password#1"})
    created = r.json()["user"]["createdAt"]
    me = (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"})).json()
    assert me["createdAt"] == created


async def test_ep08_vs_ep10_review_createdAt_consistent_PDD_3_1(client, alice):
    created = await create_review(client, alice)
    got = (await client.get(f"/api/reviews/{created['_id']}", headers=alice.headers)).json()
    assert got["createdAt"] == created["createdAt"]


async def test_ep13_vs_ep14_collection_createdAt_consistent_PDD_3_1(client, alice):
    created = await create_collection(client, alice)
    listed = (await client.get("/api/collections", headers=alice.headers)).json()[0]
    assert listed["createdAt"] == created["createdAt"]


async def test_ep19_new_vs_resumed_session_createdAt_consistent_PDD_3_1(client, alice):
    review = await create_review(client, alice)
    first = await start_chat(client, alice, review["_id"])
    again = await start_chat(client, alice, review["_id"])
    assert again["createdAt"] == first["createdAt"]


async def test_ep21_vs_ep20_message_createdAt_consistent_PDD_3_1(client, alice):
    review = await create_review(client, alice)
    s = await start_chat(client, alice, review["_id"])
    sent = (await client.post(f"/api/chat/sessions/{s['_id']}/messages", json={"content": "q"}, headers=alice.headers)).json()
    history = (await client.get(f"/api/chat/sessions/{s['_id']}/messages", headers=alice.headers)).json()
    assert [m["createdAt"] for m in history] == [sent["userMessage"]["createdAt"], sent["reply"]["createdAt"]]
