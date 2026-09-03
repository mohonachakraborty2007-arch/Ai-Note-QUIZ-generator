# Data Model: AI Lecture Notes & Quiz Generator (v2 — Persistence Layer)

**Author:** [Your Name]
**Status:** Draft v1.0
**Companion docs:** `/docs/prd.md`, `/docs/architecture.md`

> **Scope note (read first):** The MVP (v1) defined in the PRD and Architecture doc is explicitly stateless — no database (see Architecture ADR-1). This document designs the schema for **v2**, the roadmap tier that adds user accounts, a dashboard, and save/search history (PRD Section 8). It does not apply to the 1-day MVP build. It exists so that when v2 work starts, the schema doesn't have to be designed from scratch, and so this project demonstrates data-modeling ability as a portfolio artifact even though v1 doesn't use a database. If v1 is the only thing being graded/submitted, this document is supplementary, not required for Definition of Done.

---

## 1. Entity-Relationship Breakdown

### Core entities

**User**
- Represents an authenticated student.
- Attributes: `id`, `email`, `password_hash` (or OAuth provider fields), `display_name`, `created_at`.
- Exists only because v2 requires "my notes" — there is no user concept in v1.

**Note**
- One generation result: the summary + key points produced from one uploaded PDF.
- Attributes: `id`, `user_id` (owner), `source_filename`, `language`, `summary`, `key_points`, `created_at`.
- This is the entity "save & search previous notes" (PRD FR-f) operates on.

**Quiz**
- The set of MCQs generated alongside a Note.
- Attributes: `id`, `note_id`, `created_at`.
- Modeled as a separate entity from Note (rather than folded in) because Quiz has its own child entities (Questions) and its own relationship to Attempts — keeping it separate avoids overloading Note with quiz-taking concerns.

**Question**
- A single MCQ belonging to a Quiz.
- Attributes: `id`, `quiz_id`, `prompt`, `options` (JSONB array), `correct_option_index`, `explanation`.

**QuizAttempt**
- One instance of a user taking a Quiz (supports score history across sessions/devices — PRD v2 roadmap item).
- Attributes: `id`, `quiz_id`, `user_id`, `score`, `total_questions`, `completed_at`.

**QuestionResponse**
- One answer given during one attempt — the granular data needed for v3's "which topics do students get wrong most" analytics (PRD Section 8, v3).
- Attributes: `id`, `attempt_id`, `question_id`, `selected_option_index`, `is_correct`.

### Relationships

| Relationship | Cardinality | Justification |
|---|---|---|
| User → Note | 1:M | A user generates many notes over time; each note belongs to exactly one user (ownership needed for FR-f "save & search"). |
| Note → Quiz | 1:1 | Each generation produces exactly one quiz alongside one summary (matches PRD FR-3: single LLM call producing both). |
| Quiz → Question | 1:M | A quiz contains 5–10 questions (PRD FR-3.4). |
| User → QuizAttempt | 1:M | A user can retake the same quiz multiple times, each a separate attempt (supports score history, not just latest score). |
| Quiz → QuizAttempt | 1:M | Same reasoning — a quiz can be attempted many times, by the same or (in a future multi-user-sharing world) different users. |
| QuizAttempt → QuestionResponse | 1:M | Each attempt is composed of one response per question in that quiz. |
| Question → QuestionResponse | 1:M | A question is answered across many attempts over time — this is what enables future "which questions are most-missed" analytics. |

No M:M relationships are needed at this stage — every relationship in this domain is naturally hierarchical (user owns notes, notes own quizzes, quizzes own questions, attempts own responses). This is a straightforward tree-shaped data model, not a graph — flagging this because it directly informs the normalization decisions in Section 4.

---

## 2. Schema (SQL / PostgreSQL)

**Why PostgreSQL (relational), not NoSQL:** The data is inherently relational — every entity above has a clear owning parent, dashboard/search queries need joins (e.g., "all notes for user X, most recent first"), and score-tracking requires transactional integrity (an attempt's responses and final score should commit together, not partially). None of this data has the schema-flexibility or massive-horizontal-scale needs that would justify a document store. This also matches the Architecture doc's stated evolution path (Postgres via Supabase free tier).

```sql
-- /db/schema.sql

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT,                    -- nullable: allows OAuth-only accounts later
    display_name    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_filename   TEXT NOT NULL,
    language          TEXT NOT NULL CHECK (language IN ('en', 'hi', 'bn')),
    summary           TEXT NOT NULL,
    key_points        JSONB NOT NULL,         -- array of strings; see Section 4 for why
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE quizzes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id     UUID NOT NULL UNIQUE REFERENCES notes(id) ON DELETE CASCADE,  -- UNIQUE enforces 1:1
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE questions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id                UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    prompt                 TEXT NOT NULL,
    options                JSONB NOT NULL,     -- array of option strings; see Section 4
    correct_option_index   SMALLINT NOT NULL,
    explanation            TEXT NOT NULL,
    CONSTRAINT correct_index_in_range
        CHECK (correct_option_index >= 0 AND correct_option_index < jsonb_array_length(options))
);

CREATE TABLE quiz_attempts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id          UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score            SMALLINT NOT NULL CHECK (score >= 0),
    total_questions  SMALLINT NOT NULL CHECK (total_questions > 0),
    completed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT score_not_exceeding_total CHECK (score <= total_questions)
);

CREATE TABLE question_responses (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id              UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id             UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_option_index   SMALLINT NOT NULL,
    is_correct              BOOLEAN NOT NULL,
    UNIQUE (attempt_id, question_id)   -- one response per question per attempt
);
```

---

## 3. Indexing Strategy

Indexes chosen based on the actual query patterns implied by the PRD's functional requirements, not added speculatively.

| Index | Table.Column(s) | Query it serves |
|---|---|---|
| `idx_notes_user_created` | `notes(user_id, created_at DESC)` | Dashboard: "show my notes, most recent first" (PRD FR-e, User Dashboard) — the single most common query in v2. |
| `idx_notes_search` | GIN index on `to_tsvector('english', source_filename \|\| ' ' \|\| summary)` | Save & search previous notes (PRD FR-f) — full-text search across filename and summary. |
| `users_email_key` (implicit, from `UNIQUE`) | `users(email)` | Login lookup — every auth request queries by email. |
| `idx_questions_quiz` | `questions(quiz_id)` | Rendering a quiz's questions (already covered by the FK, but explicit since it's a hot path on every quiz load). |
| `idx_attempts_user_quiz` | `quiz_attempts(user_id, quiz_id, completed_at DESC)` | Score history: "show my past attempts at this quiz" (v2 roadmap: score history across sessions). |
| `idx_responses_question` | `question_responses(question_id)` | v3 analytics: "which questions are most-missed across all attempts" — not needed for v2 but cheap to add now since the table is written once per response and read rarely until v3. |

**Not indexed, deliberately:** `notes.language`, `notes.key_points` — low cardinality (3 values) or not queried directly; an index here would add write overhead with no read benefit at this scale.

---

## 4. Normalization vs Denormalization Decisions

| Decision | Choice | Why |
|---|---|---|
| `notes.key_points` | **Denormalized** — stored as a JSONB array, not a child `key_points` table | Key points are always read and written as a complete ordered list tied to exactly one note; there's no query pattern that needs to filter/search individual key points independently. Normalizing this into a table would add a join for zero query benefit. |
| `questions.options` | **Denormalized** — stored as a JSONB array, not a child `options` table | Options are fixed at generation time (typically 4), always read together as a set, and never queried individually ("find all questions with option X" is not a real use case). A child table would be classic over-normalization for this access pattern. |
| Users → Notes → Quizzes → Questions | **Normalized** into separate tables | Unlike the JSONB cases above, these each have independent lifecycles, independent query patterns (dashboard queries notes without needing quiz internals; quiz-taking queries questions without needing note metadata), and 1:M/1:1 relationships that benefit from real foreign keys and cascade behavior. |
| `quiz_attempts` / `question_responses` split | **Normalized** into two tables rather than storing responses as a JSONB array on the attempt | Unlike `options`/`key_points`, individual responses *are* independently queryable (Section 3's `idx_responses_question` index exists specifically to support per-question analytics in v3) — this is the deciding factor that flips the JSONB-vs-table decision the other way. |

The general rule applied throughout: **denormalize (JSONB) when the data is always accessed as a whole unit with no independent query need; normalize (separate table) when rows need independent indexing, filtering, or cascading lifecycle.**

---

## 5. Data Validation & Constraints (DB-level)

Enforced at the database layer, not just application code, so integrity holds even if the app has a bug:

- `users.email` — `UNIQUE` constraint, prevents duplicate accounts at the DB level regardless of app-layer checks.
- `notes.language` — `CHECK (language IN ('en', 'hi', 'bn'))` — matches PRD FR-2.1's fixed language set; an invalid value can't be written even by a buggy migration or manual insert.
- `questions.correct_option_index` — `CHECK` constraint validating the index is within bounds of the `options` array length — this is the DB-level backstop for the same invariant the Architecture doc's MCQ self-validation (FR-3.5) enforces at the app level. Defense in depth: app-level validation happens before the LLM output is trusted; DB-level validation ensures it can never be violated even by a direct write.
- `quiz_attempts.score` / `total_questions` — `CHECK` constraints ensure score is non-negative and never exceeds total questions — protects against an app-layer scoring bug silently writing nonsensical data.
- All parent-child relationships use `ON DELETE CASCADE` — deleting a user cleanly removes their notes, quizzes, questions, attempts, and responses, rather than leaving orphaned rows (important for a future "delete my account" feature and for keeping dev/test data clean).
- `question_responses` has a `UNIQUE (attempt_id, question_id)` constraint — structurally prevents duplicate/conflicting responses to the same question within one attempt.

---

## 6. Migration Strategy

**Tool: Alembic** (paired with the FastAPI/Python backend already chosen in the Architecture doc — same language, no new tooling ecosystem to learn).

- Migrations live in `/db/migrations/`, version-controlled in the same repo as the application code (not a separate infra repo) — appropriate for a solo project where splitting concerns across repos adds overhead with no team-coordination benefit.
- Each schema change is a new Alembic revision file with explicit `upgrade()` and `downgrade()` functions — every change is reversible, not just additive.
- Migrations run automatically as a pre-deploy step (e.g., a Render "pre-deploy command" or a manual `alembic upgrade head` run before deploying a new backend version) — never applied by hand directly against production via a GUI.
- The initial migration (`0001_initial_schema`) creates all six tables in Section 2 in dependency order (users → notes → quizzes → questions → quiz_attempts → question_responses), matching the FK dependency chain.
- Local dev uses the same migration files against a local Postgres instance (or Supabase's local dev CLI) — schema drift between local and production is not possible since both apply the same versioned migrations.

---

## 7. Sample Seed Data

Realistic small dataset for local dev/testing — one user, two notes (one per language to exercise the language constraint), one quiz with questions, and one completed attempt with responses.

```sql
-- /db/seed.sql

INSERT INTO users (id, email, password_hash, display_name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'priya@example.edu', '$2b$hashed_placeholder', 'Priya');

INSERT INTO notes (id, user_id, source_filename, language, summary, key_points) VALUES
    ('22222222-2222-2222-2222-222222222221',
     '11111111-1111-1111-1111-111111111111',
     'thermodynamics_lecture_04.pdf',
     'en',
     'This lecture covers the first and second laws of thermodynamics, including entropy and the concept of reversible vs irreversible processes.',
     '["Energy cannot be created or destroyed, only transformed", "Entropy of an isolated system never decreases", "Reversible processes are idealized; real processes are irreversible"]'
    ),
    ('22222222-2222-2222-2222-222222222222',
     '11111111-1111-1111-1111-111111111111',
     'thermodynamics_lecture_04.pdf',
     'bn',
     'এই বক্তৃতায় তাপগতিবিদ্যার প্রথম ও দ্বিতীয় সূত্র নিয়ে আলোচনা করা হয়েছে, যার মধ্যে এনট্রপি এবং বিপরীতমুখী বনাম অপরিবর্তনীয় প্রক্রিয়ার ধারণা অন্তর্ভুক্ত।',
     '["শক্তি সৃষ্টি বা ধ্বংস করা যায় না, শুধু রূপান্তরিত হয়", "একটি বিচ্ছিন্ন সিস্টেমের এনট্রপি কখনও হ্রাস পায় না"]'
    );

INSERT INTO quizzes (id, note_id) VALUES
    ('33333333-3333-3333-3333-333333333331', '22222222-2222-2222-2222-222222222221');

INSERT INTO questions (id, quiz_id, prompt, options, correct_option_index, explanation) VALUES
    ('44444444-4444-4444-4444-444444444441',
     '33333333-3333-3333-3333-333333333331',
     'What does the second law of thermodynamics state about entropy in an isolated system?',
     '["It always decreases", "It never decreases", "It stays exactly constant", "It becomes negative"]',
     1,
     'The second law states entropy in an isolated system never decreases over time — this is the basis for the arrow of time in thermodynamic processes.'
    ),
    ('44444444-4444-4444-4444-444444444442',
     '33333333-3333-3333-3333-333333333331',
     'A reversible process is best described as:',
     '["A real-world process with friction", "An idealized process with no entropy increase", "Any process that speeds up over time", "A process that only occurs in gases"]',
     1,
     'Reversible processes are theoretical idealizations where the system can be returned to its original state with no net entropy change — real processes are always somewhat irreversible.'
    );

INSERT INTO quiz_attempts (id, quiz_id, user_id, score, total_questions, completed_at) VALUES
    ('55555555-5555-5555-5555-555555555551',
     '33333333-3333-3333-3333-333333333331',
     '11111111-1111-1111-1111-111111111111',
     1, 2, now());

INSERT INTO question_responses (attempt_id, question_id, selected_option_index, is_correct) VALUES
    ('55555555-5555-5555-5555-555555555551', '44444444-4444-4444-4444-444444444441', 1, TRUE),
    ('55555555-5555-5555-5555-555555555551', '44444444-4444-4444-4444-444444444442', 0, FALSE);
```
