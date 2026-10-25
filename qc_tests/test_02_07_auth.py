"""#2–#7 auth endpoints (PDD §3.5, §6.1–§6.5; PR-ACC, PR-SIGN, PR-PRF, PR-DEL)."""

from bson import ObjectId

from qc_helpers import (
    NEW_PASSWORD,
    PASSWORD,
    USER_OUT_KEYS,
    assert_422_shape,
    assert_error,
    assert_iso_naive,
    bearer,
    create_collection,
    create_review,
    start_chat,
    unique_email,
)

ALL_RULES = (
    "Password must be at least 8 characters; "
    "Password must contain at least one uppercase letter; "
    "Password must contain at least one lowercase letter; "
    "Password must contain at least one special character"
)


def assert_user_out(user, email=None, name=None):
    assert set(user.keys()) == USER_OUT_KEYS, user
    assert "password" not in user
    assert_iso_naive(user["createdAt"])
    if email is not None:
        assert user["email"] == email
    if name is not None:
        assert user["name"] == name


# ── #2 POST /api/auth/register ───────────────────────────────────────────
async def test_ep02_register_success_201_PR_ACC_01_PR_ACC_05(client, qc_db):
    email = unique_email()
    r = await client.post("/api/auth/register", json={"name": "Priya", "email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == {"token", "user"}
    assert_user_out(body["user"], email=email, name="Priya")
    assert body["user"]["avatar"] is None and body["user"]["preferredLanguages"] == []
    # PR-ACC-05: signed in straight away.
    me = await client.get("/api/auth/me", headers=bearer(body["token"]))
    assert me.status_code == 200
    # PDD §6.1: empty user_stats created; password stored as bcrypt hash.
    uid = ObjectId(body["user"]["_id"])
    assert await qc_db.user_stats.count_documents({"user_id": uid}) == 1
    doc = await qc_db.users.find_one({"_id": uid})
    assert doc["password"] != PASSWORD and doc["password"].startswith("$2")


async def test_ep02_register_duplicate_email_400_PR_ACC_02(client, alice):
    r = await client.post(
        "/api/auth/register", json={"name": "Again", "email": alice.email, "password": PASSWORD}
    )
    assert_error(r, 400, "Email already in use")


async def test_ep02_register_all_password_rules_in_one_msg_PR_ACC_04_PDD_2_4(client):
    r = await client.post(
        "/api/auth/register", json={"name": "W", "email": unique_email(), "password": "1234"}
    )
    detail = assert_422_shape(r, "password")
    msg = next(e["msg"] for e in detail if e["loc"] == ["body", "password"])
    assert msg == f"Value error, {ALL_RULES}"
    assert "1234" not in r.text  # §2.4: rejected value never echoed


async def test_ep02_register_each_password_rule_PR_ACC_03(client):
    cases = {
        "Short#1": "Password must be at least 8 characters",
        "password#1": "Password must contain at least one uppercase letter",
        "PASSWORD#1": "Password must contain at least one lowercase letter",
        "Password11": "Password must contain at least one special character",
    }
    for pw, rule in cases.items():
        r = await client.post(
            "/api/auth/register", json={"name": "W", "email": unique_email(), "password": pw}
        )
        detail = assert_422_shape(r, "password")
        assert detail[0]["msg"] == f"Value error, {rule}", (pw, detail)
        assert pw not in r.text


async def test_ep02_register_invalid_email_422_PDD_3_5(client):
    r = await client.post("/api/auth/register", json={"name": "W", "email": "not-an-email", "password": PASSWORD})
    assert_422_shape(r, "email")
    assert "not-an-email" not in r.text


async def test_ep02_register_missing_fields_422_PDD_3_5(client):
    r = await client.post("/api/auth/register", json={})
    detail = assert_422_shape(r)
    assert {tuple(e["loc"]) for e in detail} >= {("body", "name"), ("body", "email"), ("body", "password")}


async def test_ep02_register_email_normalised_domain_lowercased_PDD_L12(client):
    local = f"Priya.{ObjectId()}"
    r = await client.post(
        "/api/auth/register",
        json={"name": "P", "email": f"{local}@Example.COM", "password": PASSWORD},
    )
    assert r.status_code == 201, r.text
    assert r.json()["user"]["email"] == f"{local}@example.com"
    # Local part stays case-sensitive (documented limitation L12).
    bad = await client.post("/api/auth/login", json={"email": f"{local.lower()}@example.com", "password": PASSWORD})
    assert_error(bad, 401, "Invalid email or password")
    ok = await client.post("/api/auth/login", json={"email": f"{local}@EXAMPLE.com", "password": PASSWORD})
    assert ok.status_code == 200


async def test_ep02_register_accepts_snake_and_camel_input_PDD_2_3(client):
    # Register has no multiword fields; checked on #6 instead. Here: extra
    # unknown fields are ignored and output stays camelCase.
    r = await client.post(
        "/api/auth/register",
        json={"name": "C", "email": unique_email(), "password": PASSWORD, "isAdmin": True},
    )
    assert r.status_code == 201
    assert "preferredLanguages" in r.json()["user"]


# ── #3 POST /api/auth/login ──────────────────────────────────────────────
async def test_ep03_login_success_200_PR_SIGN_01(client, alice):
    r = await client.post("/api/auth/login", json={"email": alice.email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"token", "user"}
    assert_user_out(body["user"], email=alice.email)
    assert (await client.get("/api/auth/me", headers=bearer(body["token"]))).status_code == 200


async def test_ep03_login_token_expires_in_7_days_PR_SIGN_03_PDD_2_1(client, alice):
    from jose import jwt
    from app.config import settings

    claims = jwt.get_unverified_claims(alice.token)
    assert ObjectId.is_valid(claims["sub"]) and claims["sub"] == alice.id
    assert set(claims.keys()) == {"sub", "exp"}
    import time

    days = (claims["exp"] - time.time()) / 86400
    assert 6.99 < days <= 7.0 and settings.jwt_algorithm == "HS256"


async def test_ep03_login_wrong_password_and_unknown_email_same_401_PR_SIGN_02(client, alice):
    wrong = await client.post("/api/auth/login", json={"email": alice.email, "password": "Wrong#Pass1"})
    unknown = await client.post("/api/auth/login", json={"email": unique_email(), "password": PASSWORD})
    assert_error(wrong, 401, "Invalid email or password")
    assert_error(unknown, 401, "Invalid email or password")


async def test_ep03_login_malformed_email_and_missing_fields_422_PDD_3_5(client):
    assert_422_shape(await client.post("/api/auth/login", json={"email": "nope", "password": "x"}), "email")
    r = await client.post("/api/auth/login", json={"email": unique_email()})
    assert_422_shape(r, "password")


# ── #4 GET /api/auth/me ──────────────────────────────────────────────────
async def test_ep04_me_returns_unwrapped_user_out_PDD_3_5(client, alice):
    r = await client.get("/api/auth/me", headers=alice.headers)
    assert r.status_code == 200
    assert_user_out(r.json(), email=alice.email, name="Alice")
    assert r.json()["_id"] == alice.id


# ── #5 PATCH /api/auth/profile ───────────────────────────────────────────
async def test_ep05_profile_update_name_and_languages_PR_PRF_01_PR_PRF_02(client, alice):
    r = await client.patch(
        "/api/auth/profile",
        json={"name": "Priya S", "preferredLanguages": ["Python", "Go"]},
        headers=alice.headers,
    )
    assert r.status_code == 200, r.text
    assert_user_out(r.json(), name="Priya S")
    assert r.json()["preferredLanguages"] == ["Python", "Go"]
    me = (await client.get("/api/auth/me", headers=alice.headers)).json()
    assert me["name"] == "Priya S" and me["preferredLanguages"] == ["Python", "Go"]


async def test_ep05_profile_snake_case_input_accepted_PDD_2_3(client, alice):
    r = await client.patch("/api/auth/profile", json={"preferred_languages": ["Rust"]}, headers=alice.headers)
    assert r.status_code == 200
    assert r.json()["preferredLanguages"] == ["Rust"]


async def test_ep05_profile_empty_body_400_PDD_3_5(client, alice):
    assert_error(await client.patch("/api/auth/profile", json={}, headers=alice.headers), 400, "Nothing to update")


async def test_ep05_profile_all_null_400_PDD_3_5(client, alice):
    r = await client.patch(
        "/api/auth/profile", json={"name": None, "preferredLanguages": None}, headers=alice.headers
    )
    assert_error(r, 400, "Nothing to update")


async def test_ep05_profile_blank_name_ignored_not_error_PDD_3_5(client, alice):
    r = await client.patch("/api/auth/profile", json={"name": "   "}, headers=alice.headers)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Alice"


async def test_ep05_profile_cannot_change_email_PR_PRF_09(client, alice):
    r = await client.patch(
        "/api/auth/profile", json={"name": "New", "email": unique_email()}, headers=alice.headers
    )
    assert r.status_code == 200
    assert r.json()["email"] == alice.email


async def test_ep05_profile_wrong_types_422_PDD_2_4(client, alice):
    r = await client.patch("/api/auth/profile", json={"preferredLanguages": "Python"}, headers=alice.headers)
    assert_422_shape(r)


# ── #6 PATCH /api/auth/password ──────────────────────────────────────────
async def test_ep06_password_change_success_PR_PRF_04_PR_PRF_08(client, alice):
    r = await client.patch(
        "/api/auth/password",
        json={"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD},
        headers=alice.headers,
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"message": "Password updated successfully"}
    old = await client.post("/api/auth/login", json={"email": alice.email, "password": PASSWORD})
    assert_error(old, 401, "Invalid email or password")
    new = await client.post("/api/auth/login", json={"email": alice.email, "password": NEW_PASSWORD})
    assert new.status_code == 200
    # PDD §3.5 / L6: existing tokens stay valid.
    assert (await client.get("/api/auth/me", headers=alice.headers)).status_code == 200


async def test_ep06_password_snake_case_input_accepted_PDD_2_3(client, alice):
    r = await client.patch(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=alice.headers,
    )
    assert r.status_code == 200, r.text


async def test_ep06_password_wrong_current_400_not_401_PR_PRF_06(client, alice):
    r = await client.patch(
        "/api/auth/password",
        json={"currentPassword": "Wrong#Pass1", "newPassword": NEW_PASSWORD},
        headers=alice.headers,
    )
    assert_error(r, 400, "Current password is incorrect")


async def test_ep06_password_new_breaks_rules_422_all_listed_PR_PRF_07_PR_ACC_04(client, alice):
    r = await client.patch(
        "/api/auth/password",
        json={"currentPassword": PASSWORD, "newPassword": "abc"},
        headers=alice.headers,
    )
    detail = assert_422_shape(r, "newPassword")
    msg = next(e["msg"] for e in detail if e["loc"][-1] == "newPassword")
    assert msg == (
        "Value error, Password must be at least 8 characters; "
        "Password must contain at least one uppercase letter; "
        "Password must contain at least one special character"
    )
    assert PASSWORD not in r.text and '"abc"' not in r.text


async def test_ep06_password_missing_fields_422_PDD_2_4(client, alice):
    assert_422_shape(await client.patch("/api/auth/password", json={}, headers=alice.headers))


# ── #7 DELETE /api/auth/account ──────────────────────────────────────────
async def test_ep07_delete_account_cascade_PR_DEL_03_PDD_5_5(client, qc_db, users, outbox):
    u = await users.create("Doomed")
    other = await users.create("Bystander")
    review = await create_review(client, u)
    other_review = await create_review(client, other)
    await create_collection(client, u)
    session = await start_chat(client, u, review["_id"])
    r = await client.post(
        f"/api/chat/sessions/{session['_id']}/messages", json={"content": "hi"}, headers=u.headers
    )
    assert r.status_code == 201
    await client.post("/api/auth/forgot-password", json={"email": u.email})

    uid = ObjectId(u.id)
    sid = ObjectId(session["_id"])
    assert await qc_db.password_resets.count_documents({"user_id": uid}) == 1

    r = await client.delete("/api/auth/account", headers=u.headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"message": "Account deleted successfully"}

    assert await qc_db.users.count_documents({"_id": uid}) == 0
    assert await qc_db.reviews.count_documents({"user_id": uid}) == 0
    assert await qc_db.user_stats.count_documents({"user_id": uid}) == 0
    assert await qc_db.collections.count_documents({"user_id": uid}) == 0
    assert await qc_db.chat_sessions.count_documents({"user_id": uid}) == 0
    assert await qc_db.chat_messages.count_documents({"session_id": sid}) == 0
    assert await qc_db.password_resets.count_documents({"user_id": uid}) == 0

    # Other users untouched.
    assert await qc_db.reviews.count_documents({"_id": ObjectId(other_review["_id"])}) == 1

    # PR-DEL-04: can't sign in again; old token is rejected.
    login = await client.post("/api/auth/login", json={"email": u.email, "password": PASSWORD})
    assert_error(login, 401, "Invalid email or password")
    assert_error(await client.get("/api/auth/me", headers=u.headers), 401, "User not found")


async def test_ep07_delete_account_email_can_register_again_PR_ACC_02(client, users):
    u = await users.create("Once")
    assert (await client.delete("/api/auth/account", headers=u.headers)).status_code == 200
    r = await client.post("/api/auth/register", json={"name": "Twice", "email": u.email, "password": PASSWORD})
    assert r.status_code == 201
