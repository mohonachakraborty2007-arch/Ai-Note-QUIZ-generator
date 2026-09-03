# Testing Strategy: AI Lecture Notes & Quiz Generator

**Companion docs:** `/docs/prd.md`, `/docs/architecture.md`, `/docs/api-spec.md`, `/docs/security.md`, `/docs/devops.md`

> **Scope note:** Consistent with every prior doc in this series, this plan is sized for what it's actually testing — a solo, 1-day, intermediate-complexity MVP (per the PRD's own scoping resolution), not a team-scale test org. The instruction to build the test strategy pyramid "appropriate for complexity level and timeline" is taken seriously here: this document deliberately does **not** reach for tools (Playwright/Cypress e2e suites, load-testing infra) that would cost more setup time than the risk they retire at this scale. Where something is skipped, the reasoning is stated, not just the omission.

---

## 1. Test Strategy Pyramid

```
                    ▲
                   ╱ ╲        Manual QA (Section 5)
                  ╱   ╲       — cross-browser, visual, real-LLM smoke test
                 ╱─────╲
                ╱       ╲     Integration tests (few)
               ╱         ╲    — route-level, LLM mocked
              ╱───────────╲
             ╱             ╲  Unit tests (many)
            ╱               ╲ — services/*.py: pure, fast, high-value
           ╱─────────────────╲
```

**Base — unit tests, the bulk of automated coverage:** `services/pdf_extractor.py`, `services/prompt_builder.py`, `services/mcq_validator.py` are all pure functions with no I/O dependencies (per the Business Logic Layer split in `/docs/api-spec.md` Section 2) — exactly the kind of code that's cheap to test exhaustively and where bugs are most likely to hide, since this is where every PRD functional requirement's actual logic lives.

**Middle — a handful of integration tests:** `POST /api/v1/generate` exercised end-to-end through FastAPI's `TestClient`, with `llm_client.py` mocked (never calling the real LLM API in tests — this is the same reasoning already established in `/docs/devops.md` Section 2: real API calls in an automated suite burn free-tier quota on every run and aren't necessary to test *this* app's logic, since the LLM's own output quality isn't something a unit/integration test can meaningfully assert on anyway).

**Top — deliberately thin, replaced by manual QA:** no automated browser-level e2e suite (Playwright/Cypress). **Why skip it, explicitly:** setting up and maintaining a real e2e framework is genuine ongoing work — browser installs, flaky-test triage, CI runner minutes — that pays off when a team is shipping repeatedly over months. For a solo 1-day build shipped once for a demo/grading window, that setup cost exceeds the risk it retires; the three critical user journeys (`/docs/design-system.md` Section 2) are few enough and stable enough to verify manually before the demo, which is exactly what Section 5's checklist is for. This isn't "no e2e testing happens" — it's "e2e testing happens manually once, deliberately, instead of automated repeatedly for a project that ships once."

**Frontend unit tests, one honest exception:** `QuizTab.jsx`'s scoring/state logic (FR-5.1–5.4) is stateful and non-trivial enough to be worth one real component test (Section 4) — this is the one piece of frontend logic dense enough that "just read the code" isn't sufficient confidence, unlike the mostly-declarative `UploadForm.jsx`.

---

## 2. Test Cases (derived from PRD acceptance criteria)

### Feature: PDF Upload & Extraction (FR-1.x, US-5)

| Case | Type | Expected result |
|---|---|---|
| Valid text-based PDF, well within size limit | Happy path | Text extracted successfully, length ≥ threshold |
| Non-PDF file (e.g., `.docx` renamed to `.pdf`) | Failure mode | `400 INVALID_FILE_TYPE` (and post-security-review: rejected by magic-byte check even if `Content-Type` header is spoofed — `/docs/security.md` Section 5) |
| PDF with no extractable text (scanned/image-only) | Edge case (US-5) | `422 NO_EXTRACTABLE_TEXT`, specific user-facing message |
| File exceeding 15MB | Failure mode (FR-1.3) | `413 FILE_TOO_LARGE`, rejected before extraction is attempted |
| Corrupt/malformed PDF bytes | Edge case | `422 PDF_READ_ERROR`, not an unhandled 500 |
| PDF exactly at the `min_extracted_text_chars` boundary | Edge case | Confirms the threshold comparison is correct (`>=` vs `>`), a classic off-by-one risk |

### Feature: Language-Aware Generation (FR-2.x, FR-3.x, US-1, US-2)

| Case | Type | Expected result |
|---|---|---|
| Generate with `language=en` | Happy path | System prompt contains "English"; response parsed successfully |
| Generate with `language=bn` (Arindam's case) | Happy path | System prompt contains "Bengali", not English — this is the one test that would actually catch a copy-paste bug where the language param is accepted but silently ignored |
| Invalid `language` value (e.g., `fr`) | Failure mode | `400 INVALID_LANGUAGE` before any LLM call is made (never waste quota on an invalid request) |
| LLM returns malformed JSON on first attempt, valid on retry | Edge case (FR-3.3) | Second attempt succeeds; caller never sees the first failure |
| LLM returns malformed JSON on both attempts | Failure mode | `502 LLM_GENERATION_FAILED`, user-safe message |
| Lecture text longer than `max_prompt_chars` | Edge case (FR-3.1) | Truncated before being sent, not passed through untruncated |

### Feature: MCQ Self-Validation (FR-3.4, FR-3.5) — the highest-value test target in the whole system

| Case | Type | Expected result |
|---|---|---|
| All MCQs have a `correct_answer` matching one of their `options` | Happy path | All MCQs pass through unchanged |
| One MCQ's `correct_answer` does NOT match any option | Edge case — this is the exact scenario FR-3.5 exists to catch | That MCQ is dropped; the rest pass through |
| Empty `options` list on an MCQ | Edge case | Dropped (can't match against an empty list) |
| All MCQs fail validation | Edge case | Empty `mcqs` array returned, not an error — the API still returns `200` with a shorter quiz, per the "hard gate, not a warning" design in `/docs/architecture.md` Section 4 |
| Fewer than `min_mcqs` (5) remain after filtering | Gap, worth naming explicitly: **neither the PRD nor the current implementation defines behavior here.** FR-3.4 sets a 5–10 generation target *before* validation, but says nothing about what happens if validation drops the count below 5. Recommend treating this as a known limitation for v1 (a shorter-than-intended quiz is still usable) rather than adding retry-the-whole-generation logic, which would cost both time and LLM quota disproportionate to how rarely this edge case should occur given FR-3.5's validation rate target (>95%, PRD Section 3). |

### Feature: Quiz-Taking (FR-5.1–5.5, US-3)

| Case | Type | Expected result |
|---|---|---|
| Select the correct option | Happy path | Score increments by 1; correct styling shown |
| Select an incorrect option | Happy path | Score does not increment; both the selected (wrong) and actual-correct options are visually distinguished |
| Attempt to select a second option after already answering | Edge case | No-op — `hasAnswered` guard prevents double-counting (this is the one bug class most worth a real test: an off-by-one in scoring is invisible in casual manual testing but easy to introduce in a refactor) |
| Answer the last question | Edge case (FR-5.4) | Transitions to final-score view, not "Next Question" |
| Click "Retake Quiz" | Edge case | All state resets to question 1, score 0 — confirms no stale state leaks between attempts |

### Feature: Error Handling (FR-7.1, FR-7.2)

| Case | Type | Expected result |
|---|---|---|
| Any of the above failure modes | — | Response body matches the standardized `{ error: { code, message } }` shape (`/docs/api-spec.md` Section 3) — never a raw 500 with a stack trace |
| Backend unreachable (network failure) | Edge case, frontend-side | `useGenerate` catches the fetch failure and surfaces a generic connection-error message, not an unhandled promise rejection |

---

## 3. Testing Tools & Setup

### Backend

| Tool | Purpose | Install |
|---|---|---|
| `pytest` | Test runner | `pip install pytest` |
| `pytest-mock` | Mocking (`mocker` fixture, thin wrapper on `unittest.mock`) | `pip install pytest-mock` |
| FastAPI `TestClient` (via `httpx`) | Route-level integration tests without running a real server | `pip install httpx` (already a transitive dep of `fastapi`, but pin it explicitly) |
| `reportlab` | **Test-only** dependency to generate real PDF bytes for fixtures (not used by the app itself — `pypdf` remains the app's extraction library) | `pip install reportlab` |

All added to `backend/requirements-dev.txt` (kept separate from `requirements.txt` — test tooling should never ship to production, consistent with `/docs/devops.md`'s minimal-production-footprint reasoning).

```
# backend/requirements-dev.txt
-r requirements.txt
pytest
pytest-mock
httpx
reportlab
```

Run with: `cd backend && pytest -v` — this is exactly the command already wired into `/docs/devops.md`'s CI workflow, so local and CI test runs are identical.

### Frontend

| Tool | Purpose | Install |
|---|---|---|
| `vitest` | Test runner, native to Vite (shares config, no separate webpack/babel setup needed) | `npm install -D vitest` |
| `@testing-library/react` | Component testing (render, fire events, query by role — matches the accessibility-first component design in `/docs/design-system.md` Section 6, since `QuizOptionButton`s are real `<button>` elements queryable by role) | `npm install -D @testing-library/react @testing-library/jest-dom` |
| `jsdom` | DOM environment for Vitest (no real browser needed) | `npm install -D jsdom` |

```js
// frontend/vite.config.js — add a test block to the existing Vite config
export default {
  // ...existing config
  test: {
    environment: "jsdom",
    globals: true,
  },
};
```

Run with: `cd frontend && npx vitest run`.

---

## 4. Sample Test Code

Three files, covering the highest-value targets identified in Section 2: the MCQ validator (the single most important piece of logic in the whole system), the PDF extractor (the most edge-case-prone), and the generate route (the one integration test tying it all together). All three are provided as real, executable code — not illustrative snippets.

### `backend/tests/test_mcq_validator.py`
### `backend/tests/test_pdf_extractor.py`
### `backend/tests/test_generate_route.py`
### `frontend/src/components/__tests__/QuizTab.test.jsx`

See the code files in this repo. Fixtures (`fixtures/valid_lecture.pdf`, `fixtures/scanned_blank.pdf`) are generated by a small script (`tests/fixtures/generate_fixtures.py`) rather than committed as opaque binary files — this keeps the fixture generation itself reviewable and reproducible, which matters for a portfolio repo where a reviewer might want to understand test setup, not just trust a binary blob.

---

## 5. Manual QA Checklist

Things deliberately **not** automated, with reasoning:

- [ ] **Real end-to-end LLM smoke test** — CI mocks the LLM (Section 1), so at least one genuine `POST /api/v1/generate` call against the real API, for each of the 3 languages, must be run manually before the demo. This is the literal test the PRD's own Section 3 metric asks for ("Pass/fail on 5 test PDFs per language before demo") and can't be meaningfully automated anyway, since assessing *output quality* (not just JSON validity) requires human judgment.
- [ ] **Hindi/Bengali script rendering, visual check** — confirm the Noto Sans font stack (`/docs/design-system.md` Section 3) actually renders correctly in the deployed app, not just in local dev — font-loading issues are a real, common gap between environments that no unit test catches.
- [ ] **Cross-browser check** — Chrome, Firefox, and Safari at minimum (Safari specifically, since it's historically the most likely to diverge on flexbox/font-rendering edge cases).
- [ ] **Mobile responsive check** — the mobile-first design (`/docs/design-system.md` Section 7) on an actual phone, not just a resized desktop browser window; touch-target sizing on `LanguageSelector` and `QuizOptionButton`s in particular.
- [ ] **Keyboard-only navigation through the full quiz flow** — Tab/Enter/Space through upload, tab switching, and every quiz question, per the accessibility baseline in `/docs/design-system.md` Section 6.
- [ ] **Screen reader spot-check** (VoiceOver or NVDA, whichever is available) — confirm the `aria-live` regions on loading/error states actually announce, since this is easy to get syntactically right but functionally silent.
- [ ] **Download-notes file, opened on a real device** — confirm the exported `.txt`/`.md` file (FR-6.1) actually opens cleanly, especially for Bengali/Hindi content (encoding issues are a classic silent-failure mode for non-Latin scripts in exported files).
- [ ] **Free-tier cold-start timing** — confirm the actual cold-start delay on Render's free tier (per `/docs/architecture.md` Section 5) is tolerable for a live demo, and rehearse accordingly (e.g., "warm" the backend a few minutes before demoing).
- [ ] **Deliberate prompt-injection test PDF** — from `/docs/security.md` Section 8's manual checklist, carried forward here since it's as much a QA check as a security one: upload a PDF containing an explicit injection attempt and confirm the mitigation holds.

---

## 6. Performance/Load Testing

**Explicitly out of scope for this stage**, and the PRD's own NFRs are the reason, not an oversight: `/docs/prd.md` Section 6 states scalability as *"single-digit concurrent users (class-demo scale, not production SaaS) — free-tier hosting limits apply and are accepted."* Standing up a load-testing tool (k6, Locust) to generate synthetic concurrent traffic against a system whose own requirements document explicitly disclaims production-scale concurrency would be effort spent validating a property the project was never trying to have.

**What actually substitutes for load testing at this scale:** the single timing check already in the Manual QA checklist above (confirm real generation stays under the 30s NFR) covers the one performance property the PRD actually specifies a number for. If this project's scope ever grows toward `/docs/architecture.md` Section 5's evolution path (a job queue, response caching, multi-instance hosting), *that* is the point where load testing earns its setup cost — introducing it now would be solving a problem the project doesn't have yet, which is the same anti-pattern flagged against premature auth/database work throughout this whole doc series.
