# PRD: AI Lecture Notes & Quiz Generator

**Author:** [Your Name]
**Status:** Draft v1.0
**Last updated:** 2026-08-29

> **Scoping note (read first):** The discovery brief for this project contained an unresolved conflict — `COMPLEXITY_LEVEL: 10/10` against `TIMELINE: 1 day, solo`. Per this PRD's own constraint ("don't scope an MVP that can't be built in the stated time by team size"), this document resolves that conflict explicitly rather than silently: **the MVP is scoped to intermediate complexity, buildable solo in 1 day.** Features that require auth, persistent multi-user storage, and a dashboard (user accounts, save/search history) are real, valid requirements — but they are v2 scope, not MVP. This is called out again in Section 8. If the class rubric requires those features for a passing grade, that changes the timeline and must be revisited (see Section 9, Risks).

---

## 1. Executive Summary

Students spend hours manually condensing long lecture PDFs into revision material. This project is a web app where a student uploads a lecture PDF, selects an output language (English, Hindi, or Bengali), and receives an AI-generated summary, key-point bullets, and an interactive multiple-choice quiz — all in one pass, in under a minute. The MVP is a stateless, no-login tool: upload → generate → review → take quiz → download notes. It is built solo in 1 day on a $0 budget using free-tier hosting and an LLM API, and doubles as a class assignment deliverable and a resume-ready portfolio piece demonstrating applied LLM integration, structured output generation, and end-to-end deployment.

---

## 2. Problem Statement & Target Users

**Problem:** Converting a dense lecture PDF into usable revision material (a summary, key points, and self-test questions) is manual, slow, and repetitive. Students either skip this step (and revise less effectively) or spend hours doing it by hand.

**Target users:** Students, across any subject that produces text-based lecture PDFs (notes, slides exported as PDF, transcripts).

### Personas

**1. Priya — Undergraduate, exam crunch**
- Has 8 lecture PDFs to revise the night before an exam.
- Wants: fast summaries and a quiz to self-test, not another slow tool.
- Success for her: uploads a PDF, has a quiz in under a minute, in English.

**2. Arindam — Regional-medium student**
- More comfortable revising technical concepts in Bengali than English, even though lecture material is in English.
- Wants: summary and quiz output in Bengali so revision is actually easier to process, not just translated jargon.
- Success for him: selects Bengali output and gets coherent, non-literal-translation-quality notes.

**3. You (the builder) — Student/developer**
- Needs this to work end-to-end, be deployable, and be defensible in an interview or to a grader.
- Success for you: a working deployed link, a README that explains real engineering decisions (chunking, JSON schema enforcement, error handling), not just "it calls an API."

---

## 3. Goals & Success Metrics

Since there are no real users or business metrics (academic/portfolio project), KPIs are technical and functional rather than growth-based.

| Goal | Metric | Target |
|---|---|---|
| Fast turnaround | Time from PDF upload to results rendered | < 30s for a 10–15 page text-based PDF |
| Reliable structured output | % of generations that return valid, schema-conformant JSON on first try | > 95% |
| MCQ correctness | % of generated MCQs where `correct_answer` matches one of the provided `options` (self-validated before display) | 100% (hard validation gate, not a soft target) |
| Multilingual quality | Manual spot-check: output in Hindi/Bengali is coherent and not a broken literal translation | Pass/fail on 5 test PDFs per language before demo |
| Deployment reliability | App uptime during grading/demo window | No downtime during a scheduled 15-min demo |
| Portfolio readiness | README completeness (problem statement, architecture, decisions, screenshots, limitations) | All sections present, reviewable in < 5 min |

---

## 4. Scope

### In-Scope (MVP — 1 day, solo)
- Upload a single PDF (text-based, not scanned/image-only)
- Extract text from the PDF
- User selects output language: English, Hindi, or Bengali
- Single LLM call generates: summary, key points (bulleted), and MCQs (with options, correct answer, explanation) as structured JSON
- Frontend displays results in tabs: Summary / Key Points / Quiz
- Interactive quiz mode: click an answer, get instant right/wrong feedback, see running score
- Download generated notes (summary + key points) as a text/markdown file
- Basic error handling: empty PDF, no extractable text (scanned PDF), LLM timeout/failure, oversized file
- MCQ self-validation before rendering (correct_answer must match an option)
- Deployed publicly (frontend + backend), with a README

### Out-of-Scope for MVP (explicitly deferred — see Roadmap)
- User accounts / authentication / login
- Persistent multi-session storage of past notes
- User dashboard
- Save & search previous notes
- Score history / progress tracking across sessions
- Multi-file / batch upload
- OCR support for scanned/image PDFs
- Payment or any business model (none — academic project)
- Real-time collaboration or sharing between users
- Mobile app (web-responsive only)

**Explicit call-out:** Functional requirements (e) User Dashboard and (f) Save/search previous notes, as originally requested, require auth and a database. They are **not achievable within a 1-day solo timeline** alongside the rest of MVP scope without cutting something else. They are moved to the v2 roadmap (Section 8) rather than silently dropped.

---

## 5. Functional Requirements

Grouped by module. Each requirement is testable.

### 5.1 Upload & Parsing
- **FR-1.1:** User can upload a PDF file via a file picker or drag-and-drop.
- **FR-1.2:** System rejects non-PDF files with a clear error message.
- **FR-1.3:** System rejects files over a defined size limit (e.g., 15MB) with a clear error message.
- **FR-1.4:** System extracts text from the PDF using a text-extraction library.
- **FR-1.5:** If extracted text is empty or below a minimum length threshold (likely a scanned/image-only PDF), system shows an explicit error: "No extractable text found — this PDF may be scanned/image-based."

### 5.2 Language Selection
- **FR-2.1:** User selects one output language from: English, Hindi, Bengali, before generation.
- **FR-2.2:** Selected language applies to summary, key points, and MCQ text (questions, options, explanations) — not just a UI label change.

### 5.3 AI Generation
- **FR-3.1:** System sends extracted text (chunked/truncated if it exceeds model context limits) to the LLM with a single structured prompt.
- **FR-3.2:** LLM response is requested and parsed as JSON matching a fixed schema: `{ summary: string, key_points: string[], mcqs: [{ question, options: string[], correct_answer, explanation }] }`.
- **FR-3.3:** If the LLM response fails to parse as valid JSON, system retries once, then shows a user-facing error if it still fails.
- **FR-3.4:** System generates a minimum of 5 and maximum of 10 MCQs per lecture (configurable constant).
- **FR-3.5:** Before displaying results, system validates that every MCQ's `correct_answer` exactly matches one entry in its `options` array; any MCQ failing this check is discarded, not shown.

### 5.4 Results Display
- **FR-4.1:** Results render in three tabs: Summary, Key Points, Quiz.
- **FR-4.2:** Summary tab shows the generated summary as readable paragraph(s).
- **FR-4.3:** Key Points tab shows a bulleted list.
- **FR-4.4:** Quiz tab shows one question at a time (or all at once — implementation choice), with clickable answer options.

### 5.5 Quiz Mode
- **FR-5.1:** Clicking an option immediately shows whether it was correct or incorrect.
- **FR-5.2:** Incorrect selections reveal the correct answer and the explanation text.
- **FR-5.3:** A running score (e.g., "3/7 correct") is visible during the quiz.
- **FR-5.4:** At the end of the quiz, a final score summary is shown.
- **FR-5.5:** Score/quiz state resets on page reload (no persistence required for MVP — see Out-of-Scope).

### 5.6 Export
- **FR-6.1:** User can download the summary + key points as a `.txt` or `.md` file.

### 5.7 Error Handling
- **FR-7.1:** Any backend failure (LLM API error, timeout, parsing failure) shows a user-readable error message, not a raw stack trace or blank screen.
- **FR-7.2:** A loading state is shown during generation (this step can take several seconds).

---

## 6. Non-Functional Requirements

Each target below is deliberately scoped to what a free-tier, solo, 1-day project can actually meet — not aspirational enterprise numbers.

| Category | Requirement | Target |
|---|---|---|
| Performance | End-to-end generation time for a 10–15 page PDF | < 30 seconds |
| Performance | Frontend initial load time | < 3 seconds on standard broadband |
| Scalability | Concurrent users supported without failure | Single-digit concurrent users (class-demo scale, not production SaaS) — free-tier hosting limits apply and are accepted |
| Availability | Uptime during demo/grading window | No downtime during a scheduled ~15-min window; free-tier cold-starts are acceptable and should be documented, not hidden |
| Accessibility | Baseline usability | Usable via keyboard for quiz interaction; sufficient color contrast on right/wrong feedback (not full WCAG AA audit — out of scope for 1-day timeline, documented as a known limitation) |
| Security | Input handling | File type/size validation on upload; no execution of uploaded file content; API keys never exposed client-side |
| Security | Data handling | No PII collected; uploaded PDFs are not persisted beyond the processing request (stateless by design) |
| Maintainability | Code readability | Backend and frontend each have a README section explaining structure, so a grader or future-you can onboard in under 10 minutes |
| Cost | Budget | $0 — all infra on free tiers (hosting, LLM API free quota) |

---

## 7. User Stories

**US-1**
As Priya (exam-crunch student), I want to upload a lecture PDF and get a summary and quiz quickly, so that I can revise efficiently the night before an exam.
*Acceptance criteria:*
- Given a valid text-based PDF, when I upload it and click "Generate," then I see a summary, key points, and quiz within 30 seconds.
- If generation fails, I see a clear error message, not a blank/broken screen.

**US-2**
As Arindam (regional-medium student), I want to select Bengali as my output language, so that I can revise in the language I understand best.
*Acceptance criteria:*
- Given I select Bengali before generating, when results are returned, then the summary, key points, and all quiz text are in Bengali.
- The Bengali output is coherent (not machine-literal, broken text) — verified via manual spot-check per Section 3 metrics.

**US-3**
As a student taking the quiz, I want instant feedback when I click an answer, so that I know immediately if I understood the material.
*Acceptance criteria:*
- Given I click an answer option, when it is correct, then I see a clear "Correct" indicator immediately.
- When it is incorrect, then I see the correct answer and an explanation.
- My running score updates after each question.

**US-4**
As a student, I want to download my generated notes, so that I can keep them for revision without needing to revisit the app.
*Acceptance criteria:*
- Given results have been generated, when I click "Download Notes," then a `.txt` or `.md` file containing the summary and key points downloads to my device.

**US-5**
As a student uploading a scanned PDF by mistake, I want a clear error message, so that I understand why the tool didn't work rather than seeing a silent failure.
*Acceptance criteria:*
- Given I upload a PDF with no extractable text, when I click "Generate," then I see an explicit message identifying the likely cause (scanned/image-based PDF).

---

## 8. MVP vs Future Roadmap

### MVP (v1 — ships in 1 day, solo)
Everything in Section 4's In-Scope list: stateless upload → generate → quiz → download flow, 3 languages, structured JSON generation, basic error handling, deployed with README.

### v2 (Future — explicitly not MVP)
- User accounts / authentication
- Persistent storage of generated notes per user
- User dashboard (view past uploads/results)
- Save & search previous notes
- Score history across sessions/devices
- OCR support for scanned PDFs

### v3 (Further out / stretch)
- Batch upload of multiple lecture PDFs at once
- Spaced-repetition scheduling for quiz retakes
- Sharing generated quizzes with classmates
- Support for additional languages beyond English/Hindi/Bengali
- Analytics on which topics students get wrong most often

---

## 9. Assumptions, Risks & Dependencies

**Assumptions**
- Lecture PDFs are primarily text-based (not scanned images) — OCR is out of scope for MVP.
- Free-tier LLM API quota is sufficient for development + a live demo without hitting rate limits.
- Free-tier hosting (e.g., Vercel/Render) cold-start latency is acceptable and will be documented, not treated as a bug.
- 1-day timeline assumes a working MVP with the scope in Section 4 — it does **not** assume auth/dashboard/persistence are included.

**Risks**
- **Rubric mismatch risk (highest priority, unresolved):** If the class rubric explicitly requires user accounts, a dashboard, or persistent history, the MVP as scoped will not meet it, and the timeline must be revisited. *This was flagged as an open question in discovery and was not answered before this PRD was written — recommend confirming before development starts.*
- **LLM output reliability:** structured JSON generation can occasionally fail or hallucinate malformed MCQs; mitigated by FR-3.3 (retry) and FR-3.5 (self-validation), but not 100% eliminable in one day of engineering.
- **Multilingual quality risk:** Hindi/Bengali output quality depends entirely on the underlying LLM's fluency in those languages for domain/technical content — not independently verifiable without native-speaker review, which may not be available in the timeline.
- **Free-tier quota/rate-limit risk:** demo-day failures if the LLM free tier is exhausted from testing; mitigate by reserving quota and testing conservatively before the demo.

**Dependencies**
- LLM API availability and free-tier quota (Claude API or Gemini free tier, per original tech discussion).
- Free-tier hosting platforms (Vercel, Render, or equivalent) being available and within their free-usage limits.
- PDF text-extraction library correctly handling the format of test lecture PDFs used.

---

## 10. Definition of Done

The MVP is "done" when all of the following are true:

1. All Functional Requirements in Section 5 are implemented and manually tested against the acceptance criteria in Section 7.
2. A PDF upload in each of the 3 supported languages has been tested end-to-end at least once, with output manually spot-checked for coherence.
3. Error handling paths (empty PDF, oversized file, non-PDF file, LLM failure) have each been triggered and confirmed to show a user-facing message, not a crash.
4. MCQ self-validation (FR-3.5) is confirmed working — a deliberately malformed test case is discarded rather than shown.
5. The app is deployed and publicly reachable at a live URL (frontend + backend both live).
6. README is complete: problem statement, architecture overview, tech stack + justification, setup instructions, known limitations (including the OCR/no-scanned-PDF and no-auth limitations), and "what I'd do with more time" section referencing the v2 roadmap in this PRD.
7. This PRD itself is included in the repo at `/docs/prd.md` as a work sample.
