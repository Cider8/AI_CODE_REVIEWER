# Design: Authentication & Security

**Feature:** sign-up, sign-in, profile, password change and account deletion, plus the rules that keep each member's data private.
**Code:** `app/routes/auth.py`, `app/dependencies.py`, `app/utils/security.py`, `app/schemas/auth_schema.py`, `app/main.py`

## API

| # | Method & path | Body | Success | Errors |
|---|---|---|---|---|
| 2 | `POST /api/auth/register` | `{name, email, password}` | 201 `{token, user}` | 400 email in use · 422 |
| 3 | `POST /api/auth/login` | `{email, password}` | 200 `{token, user}` | 401 wrong credentials |
| 4 | `GET /api/auth/me` 🔒 | — | 200 user | 401 |
| 5 | `PATCH /api/auth/profile` 🔒 | `{name?, preferredLanguages?}` | 200 user | 400 nothing to update |
| 6 | `PATCH /api/auth/password` 🔒 | `{currentPassword, newPassword}` | 200 `{message}` | 400 wrong current password · 422 |
| 7 | `DELETE /api/auth/account` 🔒 | — | 200 `{message}` | — |

**User response**
```json
{ "_id": "…", "name": "Priya", "email": "priya@example.com", "avatar": null,
  "preferredLanguages": ["Python"], "createdAt": "…" }
```
`GET /me` returns this object directly, not wrapped. Register and login return `{token, user}`.

## Session model

```
login/register ─► JWT (HS256, sub = userId, exp = 7 days) ─► client stores it in localStorage
every 🔒 request: Authorization: Bearer <JWT>
   └─► get_current_user: decode → valid id → user exists? ──no──► 401
```
- No server-side sessions: logging out means the client discards the token.
- The client treats **401 as "session over" → logout**. #3 is the only endpoint that returns 401 for a wrong password; #6 returns **400** for a wrong current password, so a typo doesn't log the member out.

## Passwords

- Stored as **bcrypt** hashes only.
- Rules (sign-up and change): at least 8 characters, an uppercase letter, a lowercase letter, and a special character from `!@#$%^&+=[]{}|;:,.<>?`.
- **All** broken rules are reported together in one 422 `msg`, joined by `"; "`, so the user can fix everything at once.

## Data privacy rules

| Rule | How |
|---|---|
| Members see only their own data | Every query filters by `user_id` |
| Don't reveal whether something exists | A resource that isn't yours gets the same **404** as one that doesn't exist; login uses the same message for an unknown email and a wrong password |
| Never echo input back | A custom 422 handler returns only `{type, loc, msg}`, never the rejected value (e.g. a password) |
| No duplicate accounts | Unique index on `users.email`; a race is caught and returned as 400 |
| Deleting an account removes everything | Chats → reviews → stats → collections → the user |

## Data: `users` collection

`name`, `email` (unique), `password` (bcrypt), `avatar`, `preferred_languages[]`, `created_at`.

## Known gaps

- Tokens can't be revoked: changing the password doesn't sign out other devices, which stay signed in for up to 7 days.
- The token is kept in `localStorage`, which an XSS bug could read. An httpOnly cookie would be safer.
- Email matching is case-sensitive before the `@`.
