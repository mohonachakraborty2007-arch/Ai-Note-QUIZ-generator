# Resume & Portfolio Notes: AI Lecture Notes & Quiz Generator

> Companion to `/README.md`. Everything below is calibrated to what was **actually built and verified** in this project — see the README's "Status & What's Left" section for the specific line between "built and tested," "designed but not built," and "not yet done." No claim here overstates that line.

---

## Portfolio Summary

Designed and built the backend and core frontend of a multilingual, AI-powered study tool that converts lecture PDFs into summaries, key points, and self-grading quizzes in English, Hindi, or Bengali — including a full pre-implementation design process (PRD, system architecture with 5 documented ADRs, REST API spec, database schema, UX/accessibility spec, STRIDE/OWASP security review, and CI/CD plan) and a 23-test automated suite (pytest + Vitest) covering the core generation pipeline, PDF-extraction edge cases, and quiz-scoring logic, all verified passing. The project resolved a stated scope conflict (a 10/10 complexity target against a 1-day solo timeline) by explicitly scoping a buildable MVP and deferring auth/persistence/dashboard features to a fully-designed, ready-to-build v2 — a decision documented and carried consistently through all eight project artifacts.

---

## Resume Bullets

- **Designed and implemented an AI-integrated document-processing pipeline** (FastAPI/Python) that extracts text from uploaded PDFs and generates structured, schema-validated summaries and quizzes via a single LLM call, including a hard self-validation gate that programmatically discards any AI-generated quiz question whose answer doesn't match its own options before it reaches the user.
- **Built and verified a 23-test automated suite** (pytest + Vitest/React Testing Library) spanning backend service logic, API error handling, and frontend quiz-scoring state, achieving a 100% pass rate; used generated (not mocked) PDF fixtures to test real extraction behavior, including a deliberately-blank PDF to validate the scanned-document failure path.
- **Authored a complete 8-document engineering design series** (PRD, architecture with 5 ADRs, REST API spec, database schema/ERD, UX/accessibility spec, security review, DevOps/CI plan, test strategy) that explicitly resolved a stated timeline-vs-complexity conflict by scoping a buildable MVP and cleanly deferring 6 additional features to a fully-specified v2 roadmap.
- **Conducted a STRIDE/OWASP-based security design review** that identified and specified concrete fixes for 3 real implementation gaps before they shipped — a client-spoofable file-upload validation check, an insecure default JWT secret, and a missing CORS policy — plus a documented, product-specific LLM prompt-injection mitigation strategy.

---

## Interview Story Brief

### "Walk me through the architecture."
It's a stateless, single-service FastAPI backend behind a React frontend — deliberately not microservices, not serverless-per-endpoint, no database in v1. The reasoning is in the architecture doc as five ADRs, but the short version: with one developer and a fixed short timeline, every service boundary is infrastructure time spent instead of feature time, and the actual workload here is a linear pipeline (extract → prompt → validate), not independently-scaling components. The interesting design decision isn't the stack — it's that the whole request round-trips exactly once: one PDF upload, one LLM call, one JSON response, no polling, no job queue. That's what makes a sub-30-second response time achievable without infrastructure I didn't have time to build.

### "How would this scale if it got real traffic?"
Deliberately not built for that yet, and I can name exactly what breaks first because I mapped it out rather than guessing: the LLM API's free-tier rate limit breaks before anything else, then the hosting platform's free-tier cold starts and single-instance concurrency, then in-memory PDF handling under concurrent load. The evolution path is documented too — a job queue to make generation async, response caching keyed on PDF content hash (since the same lecture PDF getting uploaded by multiple students in a class is a very plausible cache hit), and a real database once persistence features land. I didn't build any of that preemptively, because the project's own requirements explicitly scope it to single-digit concurrent users — building for scale I don't need would have been the wrong call, not a missed opportunity.

### "What was the most interesting problem you ran into?"
Doing a real security review surfaced something I hadn't originally thought about: this app feeds untrusted PDF content directly into an LLM prompt, which means a malicious PDF could contain a prompt-injection attempt — text trying to hijack the generation with something like "ignore prior instructions." That's not a classic OWASP category; it's specific to building on top of an LLM. I ended up documenting three layers that already partially mitigate it (a system-prompt instruction I added, the MCQ validation gate that happened to also limit exploit surface as a side effect, and rendering all LLM output as plain text so even a successful injection can't execute as HTML/script) — while being honest that full mitigation of prompt injection is an open industry problem, not something a solo project fully solves.

### "How did you approach testing, given the timeline?"
I didn't try to build a full test pyramid with browser-level e2e automation — for a project that ships once, the setup and maintenance cost of something like Playwright would have cost more time than it saved. Instead I put the automated-test weight on the pure-function service layer (PDF extraction, MCQ validation, prompt building), where bugs are cheapest to catch and most likely to hide, plus a handful of integration tests against the actual API route with the LLM mocked — deliberately never calling the real LLM API in automated tests, since that would burn free-tier quota on every single test run for no real benefit (assessing LLM output *quality* isn't something a unit test can do anyway; that's what a manual pre-demo check is for). The one thing worth mentioning concretely: writing the integration test actually caught a real bug — `python-multipart` was missing from `requirements.txt`, which would have been a broken `pip install` on day one of the real build.

### "What would you do differently, or what's next?"
Two honest gaps I found in my own security review and didn't just paper over: the v2 JWT design has no refresh-token revocation table, so a leaked refresh token stays valid until it naturally expires — I documented a cheap interim fix (refresh token rotation) rather than pretending the full fix (a revocation table) was already handled. And the v2 API is missing an account-deletion endpoint, which would be a real gap against GDPR's right-to-erasure if this ever had EU users — flagged as a concrete backlog item, not an abstract compliance note. Immediate next step for the actual v1 build is deploying it and running the real end-to-end LLM smoke test I haven't done yet, since everything so far has deliberately mocked the LLM in automated tests.

---

## Changelog / Roadmap

**Current state**
- ✅ v1 MVP: designed, implemented, unit/integration tested (23 passing tests). Not yet deployed.
- ✅ Full design doc series complete (PRD → architecture → API spec → data model → design system → security review → DevOps plan → test strategy).
- 📋 v2 (auth, persistence, dashboard, save/search): fully designed (API spec, schema, starter code), not built.

**Next (pre-v2)**
- [ ] Deploy v1 to Vercel + Render
- [ ] Run the real end-to-end LLM smoke test across all 3 languages (English/Hindi/Bengali)
- [ ] Apply the three flagged security fixes: magic-byte file validation, JWT secret startup check, CORS allow-list
- [ ] Add screenshots + live demo link to the README

**v2**
- [ ] User accounts / auth (JWT, designed in `/docs/api-spec.md`)
- [ ] Persistent notes + dashboard + save/search (schema in `/docs/data-model.md`)
- [ ] Score history across sessions
- [ ] Account-deletion endpoint (GDPR gap flagged in `/docs/security.md`)
- [ ] Refresh-token rotation or revocation table

**v3 (stretch)**
- [ ] Batch PDF upload
- [ ] Spaced-repetition quiz retakes
- [ ] Quiz sharing between classmates
- [ ] Additional languages
- [ ] Wrong-answer analytics
