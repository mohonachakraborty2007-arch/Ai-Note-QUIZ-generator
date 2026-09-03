# API Specification: AI Lecture Notes & Quiz Generator

**Companion docs:** `/docs/prd.md`, `/docs/architecture.md`, `/docs/data-model.md`

> **Scope note (consistent with prior docs):** This spec covers **two tiers**, clearly separated throughout:
> - **v1 (MVP):** `/api/v1/*` — stateless, no auth, no database. This is the 1-day solo build.
> - **v2 (Roadmap):** `/api/v2/*` — adds auth, persistence, dashboard/search, using the schema in `/db/schema.sql`.
>
> If only v1 is being submitted/graded, everything under "v2" in this document is supplementary design work, not a build requirement. This mirrors the same scope discipline applied in the PRD, Architecture, and Data Model docs — v2 is real, designed, and ready to build, but it is not silently smuggled into the MVP definition.

---

## 1. API Design

**Choice: REST**, not GraphQL.

**Justification:** Every resource here (notes, quizzes, attempts) sits in a shallow, fixed hierarchy (Section 1 of the Data Model doc: no M:M relationships, no graph-shaped queries). The client screens are fixed and known upfront — an upload form, a results view, a dashboard list, a quiz-taking view — none of which need GraphQL's flexible field-selection. GraphQL would add a resolver/schema layer and client tooling overhead with no corresponding benefit for a solo 1–2 day build, and REST pairs more directly with FastAPI's native idioms (automatic OpenAPI docs, `Depends()` injection) used throughout the Architecture doc.

### Endpoint list

#### v1 — MVP (stateless, no auth)

| Method | Path | Auth | Request | Response | Status Codes |
|---|---|---|---|---|---|
| POST | `/api/v1/generate` | None | `multipart/form-data`: `file` (PDF), `language` (`en`\|`hi`\|`bn`) | `{ summary, key_points[], mcqs[] }` | `200` success · `400` invalid file type/language · `413` file too large · `422` no extractable text / PDF read error · `502` LLM generation failed |

#### v2 — Roadmap (auth required unless noted)

| Method | Path | Auth | Request | Response | Status Codes |
|---|---|---|---|---|---|
| POST | `/api/v2/auth/register` | None | `{ email, password, display_name? }` | `{ user: {...}, access_token, refresh_token }` | `201` created · `400` validation error · `409` email already exists |
| POST | `/api/v2/auth/login` | None | `{ email, password }` | `{ user: {...}, access_token, refresh_token }` | `200` success · `401` invalid credentials |
| POST | `/api/v2/auth/refresh` | Refresh token | `{ refresh_token }` | `{ access_token }` | `200` success · `401` invalid/expired refresh token |
| GET | `/api/v2/users/me` | Access token | — | `{ id, email, display_name, created_at }` | `200` success · `401` unauthorized |
| POST | `/api/v2/notes` | Access token | `multipart/form-data`: `file`, `language` | `NoteOut` (note + quiz + questions) | `201` created · `400`/`413`/`422`/`502` as v1 above · `401` unauthorized |
| GET | `/api/v2/notes` | Access token | Query: `search?`, `limit?` (default 20, max 100), `offset?` | `{ notes: NoteOut[], limit, offset }` | `200` success · `401` unauthorized |
| GET | `/api/v2/notes/{note_id}` | Access token | — | `NoteOut` | `200` success · `401` unauthorized · `403` not owner · `404` not found |
| DELETE | `/api/v2/notes/{note_id}` | Access token | — | — | `204` deleted · `401` unauthorized · `403` not owner · `404` not found |
| POST | `/api/v2/quizzes/{quiz_id}/attempts` | Access token | `{ responses: [{ question_id, selected_option_index }] }` | `{ attempt_id, score, total_questions, responses[] }` | `201` created · `401` unauthorized · `404` quiz not found |
| GET | `/api/v2/quizzes/{quiz_id}/attempts` | Access token | Query: `limit?`, `offset?` | `{ attempts: AttemptOut[] }` | `200` success · `401` unauthorized |

**Ownership note:** `403` (not `404`) is returned when a note/quiz exists but belongs to a different user — this is a deliberate choice (Section 4 below) over silently 404-ing, since the resource genuinely exists; the distinction matters for correct client-side error messaging, though some APIs prefer 404 to avoid confirming existence. Documented as a conscious tradeoff, not an oversight.

---

## 2. Business Logic Layer

**Pattern: Route → Service → Repository**, matching the folder structure already laid out in the Architecture doc (`routes/`, `services/`) with a `repositories/` layer added for v2's database access.

- **Routes** (`app/routes/*.py`): HTTP concerns only — parsing the request, calling services/repositories, mapping results to response models and status codes. No business logic lives here.
- **Services** (`app/services/*.py`): the actual workflow logic that's independent of HTTP or the database — PDF extraction, prompt building, LLM calling, MCQ validation. These are pure/testable functions, reusable by both v1 and v2 routes (the v2 `create_note` endpoint reuses the exact same services as v1 `generate`, then adds persistence on top).
- **Repositories** (`app/repositories/*.py`, v2 only): all SQL/ORM access, isolated so routes never construct queries directly. This is what makes the `idx_notes_search`/`idx_notes_user_created` indexes from the Data Model doc actually get used correctly in one place, not reimplemented per-route.

### Mapping PRD user stories to this layering

| User Story | Flow |
|---|---|
| US-1 (Priya, fast generation) | `routes/generate.py` → `services/pdf_extractor.py` → `services/prompt_builder.py` → `services/llm_client.py` → `services/mcq_validator.py` → response. No repository involved (v1 stateless). |
| US-2 (Arindam, Bengali output) | Same flow; `language` param threads through `prompt_builder.build_prompt()`, which is the single place language-specific instruction text is generated (FR-2.2). |
| US-3 (instant quiz feedback) | Entirely client-side (Architecture ADR-5) — no backend route involved during quiz-taking in v1. In v2, `POST /quizzes/{id}/attempts` is called once at quiz completion, not per-answer, keeping the same "instant local feedback" UX while still persisting the final result. |
| US-4 (download notes) | Entirely client-side (`downloadNotes.js`, per Architecture folder structure) — no backend endpoint. |
| US-5 (scanned PDF error) | `services/pdf_extractor.py` raises `ScannedPDFError`, caught in the route layer and mapped to a `422` with a specific error code — see Section 3. |
| v2: dashboard/search (FR-e/f) | `routes/notes.py::list_notes` → `repositories/notes_repository.py::list_for_user`, which applies the `ILIKE`/full-text filter and ownership scoping in one place. |

---

## 3. Error Handling Strategy

**Standardized error response shape** (every non-2xx response):

```json
{
  "error": {
    "code": "SCREAMING_SNAKE_CASE_CODE",
    "message": "Human-readable message safe to show the user.",
    "details": { "optional": "structured context, e.g. field-level validation errors" }
  }
}
```

**Error codes used (extendable, not exhaustive):**

| Code | HTTP Status | Meaning |
|---|---|---|
| `INVALID_FILE_TYPE` | 400 | Uploaded file is not a PDF |
| `INVALID_LANGUAGE` | 400 | Language not one of `en`/`hi`/`bn` |
| `VALIDATION_ERROR` | 400 | Generic request body validation failure (auth endpoints) |
| `INVALID_CREDENTIALS` | 401 | Login email/password mismatch |
| `INVALID_TOKEN` | 401 | Access/refresh token missing, malformed, or expired |
| `FORBIDDEN` | 403 | Authenticated, but not the resource owner |
| `NOT_FOUND` | 404 | Resource does not exist |
| `EMAIL_ALREADY_EXISTS` | 409 | Registration with a taken email |
| `FILE_TOO_LARGE` | 413 | Upload exceeds 15MB (PRD FR-1.3) |
| `NO_EXTRACTABLE_TEXT` | 422 | Likely scanned/image PDF (PRD FR-1.5) |
| `PDF_READ_ERROR` | 422 | PDF is corrupt/unreadable |
| `LLM_GENERATION_FAILED` | 502 | LLM call/parsing failed after retry (PRD FR-3.3) |
| `RATE_LIMITED` | 429 | Too many requests (Section 5) |

**This directly satisfies PRD FR-7.1** ("user-readable error message, not a raw stack trace") — every raised exception in the service layer is caught at the route boundary and mapped to this shape; nothing unhandled reaches the client as a 500 with a stack trace.

**Logging approach:** structured JSON logs (Python's `logging` with a JSON formatter), one log line per request including a generated `request_id`, route, status code, and — on error — the error `code` (never the raw LLM response text, which could be large/sensitive-adjacent). This is a "with more time" item for full request tracing; for the 1-day MVP, basic structured logging to stdout (captured by Render's log viewer) is sufficient and free.

---

## 4. Auth & Authorization (v2 only — not part of v1 MVP)

**Mechanism: JWT**, access token + refresh token pair — not server-side sessions.

- **Access token:** short-lived (15 min), sent as `Authorization: Bearer <token>`, contains `sub` (user id) and `type: access`. Validated statelessly on every request via a FastAPI dependency (`get_current_user_id`) — no database lookup needed per request, which keeps the hot path fast.
- **Refresh token:** longer-lived (30 days), used only against `/api/v2/auth/refresh` to mint a new access token.
- **Password storage:** bcrypt via `passlib`, never plaintext, never reversible.

**Known gap, flagged rather than hidden:** the schema in `/db/schema.sql` has no `refresh_tokens` table, so this design has **no server-side refresh-token revocation** (e.g., can't force-logout a stolen token before it expires). For a portfolio/academic v2, this is an acceptable, explicitly-documented limitation — the fix (adding a `refresh_tokens` table with a `revoked_at` column) is a small, clearly-scoped follow-up, not a silent omission.

**Authorization:** no roles/permissions system — every authenticated user has identical capabilities over their own resources only. Ownership is enforced at the repository layer (every query is scoped by `user_id`), not left to the client to self-report.

---

## 5. Rate Limiting & Input Validation

**Rate limiting:** `slowapi` (FastAPI-native, free), applied per-IP to `/api/v1/generate` and `/api/v2/notes` (POST) specifically — these are the endpoints that consume the shared LLM free-tier quota (Architecture Section 5's #1 identified bottleneck). Suggested limit: 5 requests/minute per IP, generous enough for legitimate use, tight enough to protect the quota from accidental abuse (e.g., a broken frontend retry loop) during a public demo.

**Input validation:**
- **File type/size:** validated at the route layer before any processing begins (fail fast, don't waste LLM quota on a request that will be rejected anyway).
- **Request bodies:** Pydantic models validate shape/types automatically (FastAPI's built-in behavior) — a malformed JSON body never reaches business logic.
- **Language enum:** validated against the fixed `{en, hi, bn}` set, matching the DB `CHECK` constraint in `/db/schema.sql` — the same invariant enforced at both the API boundary and the database, consistent with the Data Model doc's "defense in depth" principle (Section 5 of that doc).

---

## 6. Background Jobs / Async Work

**The PRD does not imply a real background-job need for v1 or v2** — no emails, no notifications, no scheduled work. The one candidate is worth naming and explicitly deferring: making PDF generation itself asynchronous (return immediately with a job ID, poll for the result) rather than a single blocking request.

- **Not implemented in this spec** because the < 30s target (PRD NFR) is achievable synchronously with a single LLM call (Architecture ADR-2), and adding a job queue (Redis + worker, per Architecture Section 5's evolution path) is real infra complexity not justified until actual free-tier timeout problems are observed in practice.
- **If needed later:** FastAPI's built-in `BackgroundTasks` is the lightest first step (no new infra) before reaching for a full queue like Celery/RQ — noted here so the escalation path is deliberate, not ad hoc.

---

## 7. Starter Code

Three endpoints implemented, per the instruction to focus on the most important ones:

1. **`POST /api/v1/generate`** — the actual MVP core endpoint.
2. **`POST /api/v2/notes`** — the v2 counterpart: same generation pipeline, plus persistence and auth.
3. **`GET /api/v2/notes`** — the dashboard/search query that justifies the indexing strategy from the Data Model doc.

Code files are under `backend/app/` in this repo, matching the folder structure from `/docs/architecture.md`:

```
backend/app/
├── config.py
├── db.py
├── models.py
├── auth.py
├── routes/
│   ├── generate.py       # v1 MVP endpoint
│   └── notes.py          # v2 endpoints (create + list)
├── services/
│   ├── pdf_extractor.py
│   ├── prompt_builder.py
│   ├── llm_client.py
│   └── mcq_validator.py
├── schemas/
│   ├── generation.py
│   └── notes.py
└── repositories/
    └── notes_repository.py
```

See the code files themselves for inline comments mapping logic back to specific PRD requirement IDs (FR-1.x, FR-3.x, etc.).
