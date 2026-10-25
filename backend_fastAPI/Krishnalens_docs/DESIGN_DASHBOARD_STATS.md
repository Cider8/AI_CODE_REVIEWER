# Design: Dashboard Stats

**Feature:** a member sees their totals, average score, score trend, languages, common weaknesses and recent reviews.
**Code:** `app/routes/stats.py`, `app/utils/stats.py`, `app/models/stats.py`

## API

| # | Method & path | Success |
|---|---|---|
| 12 | `GET /api/stats` (sign-in required) | 200 `{stats, recentReviews}` |

`stats` = `totalReviews, averageScore, totalBugsFound, totalSecurityIssuesFound, scoreHistory[{score, date}], languageBreakdown[{language, count}], commonWeaknesses[], updatedAt`.
`recentReviews` = the 5 newest reviews, as list items.

## How the numbers are produced

The stats are stored in one `user_stats` document per user and **rebuilt from the user's current reviews** after every review create or delete (`recompute_stats`):

```
reviews (oldest → newest)
  ├─► totalReviews, totalBugsFound, totalSecurityIssuesFound   (counts)
  ├─► averageScore                                             (mean, 2 decimal places)
  ├─► scoreHistory                                             (one point per review)
  ├─► languageBreakdown                                        (count per language)
  └─► commonWeaknesses   bug.category + securityIssue.type,
                         normalised for case and spacing, counted once per review,
                         kept if seen in ≥ 2 reviews, top 5
```

## Data: `user_stats` collection

| Field | Notes |
|---|---|
| `user_id` | unique index, one document per user |
| totals, `average_score`, `score_history[]`, `language_breakdown[]`, `common_weaknesses[]` | derived; rebuilt on every review write |
| `daily_chat_count`, `chat_count_date` | chat quota (see the Review Chat design) |
| `updated_at` | |

The document is created on demand if it's missing.

## Key decisions

| Decision | Why |
|---|---|
| Rebuild from the reviews instead of updating counts one by one | Deletes stay correct; no drift from rounding or missed updates |
| Count a weakness once per review, and only if it appears in ≥ 2 reviews | One noisy snippet can't dominate; one-off findings aren't shown as "common" |
| Bug `category` is optional | Reviews saved before it existed still load; they contribute only security types |

## Trade-offs and possible simplification

- A rebuild reads all of the user's reviews: O(n) per write. That's fine at this scale.
- **A simpler alternative:** compute everything on `GET /api/stats` and store nothing derived. That removes `recompute_stats` and the stored copy, and costs one extra read per dashboard load. Worth considering when this is next touched.
