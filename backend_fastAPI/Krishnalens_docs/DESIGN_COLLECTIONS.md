# Design: Collections

**Feature:** a member groups reviews into named folders (e.g. "DSA Practice").
**Code:** `app/routes/collections.py`, `app/models/collection.py`, `app/schemas/stats_schema.py`

## API

All of these require sign-in. A collection that isn't yours returns 404.

| # | Method & path | Body | Success | Errors |
|---|---|---|---|---|
| 13 | `POST /api/collections` | `{name, description?}` | 201 collection | 422 missing name |
| 14 | `GET /api/collections` | — | 200 collection[] | — |
| 15 | `PATCH /api/collections/{id}` | `{name?, description?}` (at least one) | 200 collection | 400 "Nothing to update" / "Collection name cannot be empty" · 404 |
| 16 | `PATCH /api/collections/{id}/add-review` | `{reviewId}` | 200 collection | 404 "Collection not found" / "Review not found" |
| 17 | `PATCH /api/collections/{id}/remove-review` | `{reviewId}` | 200 collection | 404 "Collection not found" |
| 18 | `DELETE /api/collections/{id}` | — | 200 `{message}` | 404 |

**Collection response**
```json
{ "_id": "…", "userId": "…", "name": "DSA Practice", "description": "Interview prep",
  "reviewIds": [ { "_id": "…", "title": "…", "language": "Python", "overallScore": 78, "createdAt": "…" } ],
  "createdAt": "…" }
```
`reviewIds` contains **review summaries, not plain IDs**. Reviews that no longer exist are left out.

## Flow: add a review

```
PATCH /{id}/add-review ─► collection is mine? ──no──► 404 "Collection not found"
                              │
                         review is mine? ──no──► 404 "Review not found"
                              │
                         already in the list? ──yes──► unchanged
                              │no
                         append ─► 200 collection
```

## Data: `collections` collection

`user_id` (indexed) · `name` · `description` · `review_ids[]` (references to `reviews`) · `created_at` · `updated_at` · `is_archived` (reserved, unused)

## Key decisions

| Decision | Why |
|---|---|
| Store review IDs and fill in summaries when reading | One review can sit in many collections without copying it |
| Add and remove do nothing on repeats (idempotent) | A double click or retry is safe |
| Remove doesn't look the review up | IDs left behind by deleted reviews can still be cleared |
| Deleting a collection keeps its reviews | A collection is only a folder |
| Deleting a review removes it from every collection | No dead entries (done in the review delete) |

## Known gaps on this branch

- `POST` accepts a blank name, while `PATCH` refuses one (fixed on `feature/forgot-password-qc-fixes`).
- The field name `reviewIds` suggests plain IDs but holds objects. Renaming it is a breaking change, so agree it with the frontend first.
