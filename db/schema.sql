-- /db/schema.sql
-- AI Lecture Notes & Quiz Generator — v2 persistence layer
-- See /docs/data-model.md for full rationale (ERD, indexing strategy,
-- normalization decisions). NOT used by the v1 MVP, which is stateless.

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
    key_points        JSONB NOT NULL,         -- array of strings; denormalized, see data-model.md Sec 4
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
    options                JSONB NOT NULL,     -- array of option strings; denormalized, see data-model.md Sec 4
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

-- ============================================================
-- Indexes (see /docs/data-model.md Section 3 for query rationale)
-- ============================================================

CREATE INDEX idx_notes_user_created ON notes (user_id, created_at DESC);

CREATE INDEX idx_notes_search ON notes
    USING GIN (to_tsvector('english', source_filename || ' ' || summary));

CREATE INDEX idx_questions_quiz ON questions (quiz_id);

CREATE INDEX idx_attempts_user_quiz ON quiz_attempts (user_id, quiz_id, completed_at DESC);

CREATE INDEX idx_responses_question ON question_responses (question_id);
