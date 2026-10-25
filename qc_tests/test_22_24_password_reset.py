"""#22–#24 forgot password (PDD §3.5, §4.4, §6.5a, §7; PR-FPW-01…14)."""

from datetime import timedelta

from bson import ObjectId

import app.routes.auth as auth_routes
from app.config import settings
from app.utils.time import utc_now
from qc_helpers import (
    NEW_PASSWORD,
    PASSWORD,
    assert_422_shape,
    assert_error,
    bearer,
    make_token,
    random_oid,
    unique_email,
)

FORGOT_MSG = "If an account exists for this email, we've sent a 6-digit code to it."
INVALID_CODE = "Invalid or expired code"
RESET_EXPIRED = "Your reset session has expired. Please start again."
RESET_OK = "Password updated. Please sign in with your new password."


async def forgot(client, email, **kw):
    return await client.post("/api/auth/forgot-password", json={"email": email}, **kw)


async def verify(client, email, code, **kw):
    return await client.post("/api/auth/verify-reset-code", json={"email": email, "code": code}, **kw)


async def reset(client, token, password=NEW_PASSWORD, **kw):
    return await client.post(
        "/api/auth/reset-password", json={"resetToken": token, "newPassword": password}, **kw
    )


def wrong_code(code):
    return f"{(int(code) + 1) % 10**6:06d}"


async def get_code(client, outbox, user):
    r = await forgot(client, user.email)
    assert r.status_code == 200, r.text
    code = outbox.last_code_for(user.email)
    assert code is not None, "no reset code in the log output"
    return code


async def get_reset_token(client, outbox, user):
    code = await get_code(client, outbox, user)
    r = await verify(client, user.email, code)
    assert r.status_code == 200, r.text
    return r.json()["resetToken"]


async def age_reset_record(qc_db, user, seconds):
    """Pretends the last code was issued `seconds` ago (cooldown tests)."""
    await qc_db.password_resets.update_many(
        {"user_id": ObjectId(user.id)},
        {"$set": {"created_at": utc_now() - timedelta(seconds=seconds)}},
    )


# ── #22 POST /api/auth/forgot-password ───────────────────────────────────
async def test_ep22_known_email_200_and_code_sent_PR_FPW_02_PR_FPW_03(client, qc_db, alice, outbox):
    r = await forgot(client, alice.email)
    assert r.status_code == 200
    assert r.json() == {"message": FORGOT_MSG}
    code = outbox.last_code_for(alice.email)
    assert code and len(code) == 6 and code.isdigit()

    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    assert rec is not None and rec["attempts"] == 0 and rec["verified"] is False
    assert code not in str(rec)  # PDD §5.2: only the HMAC is stored
    lifetime = (rec["expires_at"] - rec["created_at"]).total_seconds()
    assert 14 * 60 < lifetime <= 15 * 60 + 1  # PR-FPW-06: 15 minutes


async def test_ep22_email_text_mentions_15_minutes_and_ignore_PR_FPW_03(client, alice, capsys):
    await forgot(client, alice.email)
    out = capsys.readouterr().out
    assert "Your KrishnaLens password reset code" in out
    assert "expires in 15 minutes" in out
    assert "ignore this email" in out
    assert PASSWORD not in out  # PR-Q-03


async def test_ep22_unknown_email_same_200_no_record_PR_FPW_02(client, qc_db, alice, outbox):
    known = await forgot(client, alice.email)
    email = unique_email()
    unknown = await forgot(client, email)
    assert unknown.status_code == 200
    assert unknown.json() == known.json() == {"message": FORGOT_MSG}
    assert outbox.last_code_for(email) is None


async def test_ep22_malformed_email_422_PDD_3_5(client):
    assert_422_shape(await forgot(client, "not-an-email"), "email")
    assert_422_shape(await client.post("/api/auth/forgot-password", json={}), "email")


async def test_ep22_email_provider_disabled_503_PR_FPW_13(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "")
    r = await forgot(client, alice.email)
    assert_error(r, 503, "Password reset by email is not available right now")


async def test_ep22_brevo_without_key_503_PDD_4_4(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "brevo_api_key", None)
    r = await forgot(client, alice.email)
    assert_error(r, 503, "Password reset by email is not available right now")


async def test_ep22_cooldown_60s_no_second_email_PR_FPW_05(client, qc_db, alice, outbox):
    await forgot(client, alice.email)
    first = outbox.read()
    rec1 = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    r = await forgot(client, alice.email)
    assert r.status_code == 200 and r.json() == {"message": FORGOT_MSG}
    assert outbox.read() == [], "a second email was sent inside the 60 s cooldown"
    rec2 = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    assert rec1["_id"] == rec2["_id"]
    assert len(first) == 1


async def test_ep22_after_cooldown_new_code_replaces_old_PR_FPW_05(client, qc_db, alice, outbox):
    old_code = await get_code(client, outbox, alice)
    await age_reset_record(qc_db, alice, 61)
    new_code = await get_code(client, outbox, alice)
    assert await qc_db.password_resets.count_documents({"user_id": ObjectId(alice.id)}) == 1
    if old_code != new_code:
        assert_error(await verify(client, alice.email, old_code), 400, INVALID_CODE)
    assert (await verify(client, alice.email, new_code)).status_code == 200


async def test_ep22_email_trimmed_and_domain_lowercased_PDD_3_5_L12(client, alice, outbox):
    local, domain = alice.email.split("@")
    r = await forgot(client, f"  {local}@{domain.upper()}  ")
    assert r.status_code == 200, r.text
    assert outbox.last_code_for(alice.email) is not None


async def test_ep22_authorization_header_ignored_PDD_3_5(client, alice, outbox):
    r = await forgot(client, alice.email, headers=bearer("garbage"))
    assert r.status_code == 200
    assert outbox.last_code_for(alice.email) is not None


async def test_ep22_send_failure_drops_record_retry_immediately_PDD_4_4(client, qc_db, alice, monkeypatch, outbox):
    async def boom(*a, **k):
        raise RuntimeError("smtp down")

    original = auth_routes.send_password_reset_code
    monkeypatch.setattr(auth_routes, "send_password_reset_code", boom)
    r = await forgot(client, alice.email)
    assert r.status_code == 200 and r.json() == {"message": FORGOT_MSG}
    assert await qc_db.password_resets.count_documents({"user_id": ObjectId(alice.id)}) == 0

    monkeypatch.setattr(auth_routes, "send_password_reset_code", original)
    r = await forgot(client, alice.email)
    assert r.status_code == 200
    assert outbox.last_code_for(alice.email) is not None
    assert await qc_db.password_resets.count_documents({"user_id": ObjectId(alice.id)}) == 1


# ── #23 POST /api/auth/verify-reset-code ─────────────────────────────────
async def test_ep23_correct_code_returns_reset_token_PR_FPW_09(client, qc_db, alice, outbox):
    from jose import jwt

    code = await get_code(client, outbox, alice)
    r = await verify(client, alice.email, code)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"resetToken", "expiresInMinutes"}
    assert body["expiresInMinutes"] == 10
    claims = jwt.get_unverified_claims(body["resetToken"])
    assert claims["purpose"] == "password_reset" and claims["sub"] == alice.id
    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    assert rec["verified"] is True and str(rec["_id"]) == claims["rid"]
    lifetime = (rec["expires_at"] - utc_now()).total_seconds()
    assert 9 * 60 < lifetime <= 10 * 60 + 1


async def test_ep23_wrong_code_400_PR_FPW_07(client, alice, outbox):
    code = await get_code(client, outbox, alice)
    assert_error(await verify(client, alice.email, wrong_code(code)), 400, INVALID_CODE)


async def test_ep23_unknown_email_400_same_message_PR_FPW_07(client):
    assert_error(await verify(client, unique_email(), "123456"), 400, INVALID_CODE)


async def test_ep23_no_pending_code_400_PR_FPW_07(client, alice):
    assert_error(await verify(client, alice.email, "123456"), 400, INVALID_CODE)


async def test_ep23_expired_code_400_PR_FPW_06(client, qc_db, alice, outbox):
    code = await get_code(client, outbox, alice)
    await qc_db.password_resets.update_one(
        {"user_id": ObjectId(alice.id)}, {"$set": {"expires_at": utc_now() - timedelta(seconds=1)}}
    )
    assert_error(await verify(client, alice.email, code), 400, INVALID_CODE)


async def test_ep23_code_single_use_already_verified_400_PR_FPW_06(client, alice, outbox):
    code = await get_code(client, outbox, alice)
    assert (await verify(client, alice.email, code)).status_code == 200
    assert_error(await verify(client, alice.email, code), 400, INVALID_CODE)


async def test_ep23_fifth_attempt_still_counts_correct_code_ok_PDD_6_5a(client, alice, outbox):
    code = await get_code(client, outbox, alice)
    for _ in range(4):
        assert_error(await verify(client, alice.email, wrong_code(code)), 400, INVALID_CODE)
    assert (await verify(client, alice.email, code)).status_code == 200


async def test_ep23_attempt_cap_5_burns_code_PR_FPW_07_PDD_5_5(client, qc_db, alice, outbox):
    code = await get_code(client, outbox, alice)
    for _ in range(5):
        assert_error(await verify(client, alice.email, wrong_code(code)), 400, INVALID_CODE)
    # §3.5: when the cap is reached the code is deleted.
    assert await qc_db.password_resets.count_documents({"user_id": ObjectId(alice.id)}) == 0
    assert_error(await verify(client, alice.email, code), 400, INVALID_CODE)


async def test_ep23_attempts_counted_per_call_PDD_3_5(client, qc_db, alice, outbox):
    code = await get_code(client, outbox, alice)
    for n in range(1, 4):
        await verify(client, alice.email, wrong_code(code))
        rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
        assert rec["attempts"] == n


async def test_ep23_code_format_422_PR_FPW_08(client, alice):
    for bad in ["12345", "1234567", "abcdef", "12 456", ""]:
        r = await verify(client, alice.email, bad)
        assert_422_shape(r, "code")
    assert_422_shape(await verify(client, "bad-email", "123456"), "email")


async def test_ep23_non_ascii_digits_422_not_an_attempt_PR_FPW_08(client, qc_db, alice, outbox):
    """PR-FPW-08: codes are 6 ASCII digits. Python/Rust regex \\d also matches
    fullwidth and Arabic-Indic digits, so these reach the handler and burn one
    of the 5 attempts instead of being rejected as 422."""
    await get_code(client, outbox, alice)
    for bad in ["１２３４５６", "١٢٣٤٥٦"]:
        assert_422_shape(await verify(client, alice.email, bad), "code")
    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    assert rec["attempts"] == 0


async def test_ep23_authorization_header_ignored_PDD_3_5(client, alice, outbox):
    code = await get_code(client, outbox, alice)
    r = await verify(client, alice.email, code, headers=bearer("garbage"))
    assert r.status_code == 200


# ── #24 POST /api/auth/reset-password ────────────────────────────────────
async def test_ep24_reset_success_old_password_stops_working_PR_FPW_11(client, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    r = await reset(client, token)
    assert r.status_code == 200, r.text
    assert r.json() == {"message": RESET_OK}  # no login token returned
    old = await client.post("/api/auth/login", json={"email": alice.email, "password": PASSWORD})
    assert_error(old, 401, "Invalid email or password")
    new = await client.post("/api/auth/login", json={"email": alice.email, "password": NEW_PASSWORD})
    assert new.status_code == 200
    # PR-FPW-14 / L6: existing sessions stay valid.
    assert (await client.get("/api/auth/me", headers=alice.headers)).status_code == 200


async def test_ep24_token_single_use_PR_FPW_12(client, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    assert (await reset(client, token)).status_code == 200
    assert_error(await reset(client, token, "Another#Pass3"), 400, RESET_EXPIRED)
    ok = await client.post("/api/auth/login", json={"email": alice.email, "password": NEW_PASSWORD})
    assert ok.status_code == 200


async def test_ep24_superseded_by_newer_code_400_PDD_7(client, qc_db, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    await age_reset_record(qc_db, alice, 61)
    await get_code(client, outbox, alice)
    assert_error(await reset(client, token), 400, RESET_EXPIRED)


async def test_ep24_record_expired_400_PR_FPW_10(client, qc_db, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    await qc_db.password_resets.update_one(
        {"user_id": ObjectId(alice.id)}, {"$set": {"expires_at": utc_now() - timedelta(seconds=1)}}
    )
    assert_error(await reset(client, token), 400, RESET_EXPIRED)


async def test_ep24_token_expired_jwt_400_PR_FPW_10(client, qc_db, alice, outbox):
    await get_reset_token(client, outbox, alice)
    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    expired = make_token(alice.id, days=-1, extra={"rid": str(rec["_id"]), "purpose": "password_reset"})
    assert_error(await reset(client, expired), 400, RESET_EXPIRED)


async def test_ep24_garbage_and_login_token_rejected_400_PDD_6_5a(client, alice):
    assert_error(await reset(client, "garbage"), 400, RESET_EXPIRED)
    assert_error(await reset(client, alice.token), 400, RESET_EXPIRED)
    bad_rid = make_token(alice.id, extra={"rid": "nope", "purpose": "password_reset"})
    assert_error(await reset(client, bad_rid), 400, RESET_EXPIRED)
    unknown_rid = make_token(alice.id, extra={"rid": random_oid(), "purpose": "password_reset"})
    assert_error(await reset(client, unknown_rid), 400, RESET_EXPIRED)


async def test_ep24_unverified_record_cannot_be_used_PDD_6_5a(client, qc_db, alice, outbox):
    await get_code(client, outbox, alice)
    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    forged = make_token(alice.id, extra={"rid": str(rec["_id"]), "purpose": "password_reset"}, days=1)
    assert_error(await reset(client, forged), 400, RESET_EXPIRED)


async def test_ep24_token_bound_to_its_user_PDD_6_5a(client, qc_db, alice, bob, outbox):
    await get_reset_token(client, outbox, alice)
    rec = await qc_db.password_resets.find_one({"user_id": ObjectId(alice.id)})
    swapped = make_token(bob.id, extra={"rid": str(rec["_id"]), "purpose": "password_reset"})
    assert_error(await reset(client, swapped), 400, RESET_EXPIRED)


async def test_ep24_weak_password_422_all_rules_PR_FPW_09_PR_ACC_04(client, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    r = await reset(client, token, "weak")
    detail = assert_422_shape(r, "newPassword")
    assert "Password must be at least 8 characters; " in detail[0]["msg"]
    assert '"weak"' not in r.text
    # The 422 must not consume the token.
    assert (await reset(client, token)).status_code == 200


async def test_ep24_missing_fields_422_PDD_2_4(client):
    assert_422_shape(await client.post("/api/auth/reset-password", json={}))


async def test_ep24_authorization_header_ignored_PDD_3_5(client, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    r = await reset(client, token, headers=bearer("garbage"))
    assert r.status_code == 200


async def test_ep23_reset_token_is_not_a_login_token_PDD_7(client, alice, outbox):
    token = await get_reset_token(client, outbox, alice)
    assert_error(await client.get("/api/auth/me", headers=bearer(token)), 401, "Token invalid or expired")
