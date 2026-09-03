# AI Lecture Notes & Quiz Generator

**Turn a lecture PDF into a summary, key points, and a self-test quiz — in English, Hindi, or Bengali — in under a minute.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/tests-23%20passing-brightgreen)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

> **Project status:** Core MVP is implemented and fully unit/integration tested (23 passing automated tests). **Not yet deployed to a public URL** — see [Status & What's Left](#status--whats-left) below for exactly what that means. This README is written honestly around that: no fake demo link, no inflated claims.

---

## Demo

🚧 **Live demo:** _not yet deployed — will be linked here once hosted on Vercel/Render (see `/docs/devops.md` for the exact, ready-to-execute deployment plan)._

🚧 **Screenshots:** _to be added after the frontend is wired to a running backend and exercised against a real LLM call._

---

## The Problem

Converting a dense lecture PDF into usable revision material — a summary, key points, and self-test questions — is manual, slow, and repetitive. Students either skip this step entirely or spend hours doing it by hand. This tool automates that in one pass, with a distinguishing feature most similar tools skip: genuine multilingual output (not just a translated UI) for English, Hindi, and Bengali, so students who think more clearly in a regional language get study material that's actually easier to process, not just literally translated jargon.

## Key Features

- 📄 **PDF upload** with server-side text extraction and validation
- 🌐 **Multilingual generation** — summary, key points, and quiz questions all generated natively in English, Hindi, or Bengali (not translated after the fact)
- 🤖 **Single structured LLM call** returns a summary, bulleted key points, and 5–10 multiple-choice questions as validated JSON
- ✅ **Hard MCQ validation gate** — every generated question's correct answer is verified against its own options before the user ever sees it; anything that fails is silently dropped, not shown broken
- 🎯 **Interactive quiz mode** with instant right/wrong feedback, running score, and a final results screen
- 📥 **One-click notes export** to a downloadable `.txt`/`.md` file
- ♿ **Accessibility baseline** — keyboard-operable quiz, color-plus-icon feedback (never color alone), `aria-live` regions for loading/error states

## Architecture

```
Browser (React + Vite + Tailwind)
        │  POST /api/v1/generate  (multipart: PDF + language)
        ▼
FastAPI backend (stateless, no auth, no database in v1)
  1. Validate file type/size
  2. Extract text (pypdf)
  3. Build a language-aware structured prompt
  4. Call the LLM, retry once on malformed JSON
  5. Validate every MCQ before returning it
        │
        ▼
LLM API (Claude or Gemini)
```

Full diagram, architecture-pattern reasoning, and five documented ADRs (why stateless, why no auth in v1, why a monolith not microservices, etc.) live in **[`/docs/architecture.md`](docs/architecture.md)**.

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React (Vite) + Tailwind CSS |
| Backend | Python, FastAPI |
| PDF parsing | pypdf |
| LLM | Claude API / Gemini 1.5 Flash |
| Hosting (planned) | Vercel (frontend) + Render (backend), both free tier |
| Testing | pytest + pytest-mock (backend), Vitest + React Testing Library (frontend) |
| CI | GitHub Actions (lint, test, security scan on every push) |

Full stack justification (each choice tied to a specific requirement, not just "it's popular") is in `/docs/architecture.md` Section 1.

## Project Documentation

This project was built through a full, deliberately-scoped design process before any code was written — the complete series is included as work samples, not just the code:

| Doc | What it covers |
|---|---|
| [`/docs/prd.md`](docs/prd.md) | Product requirements, personas, functional/non-functional requirements, explicit MVP-vs-v2 scope resolution |
| [`/docs/architecture.md`](docs/architecture.md) | Tech stack, system diagram, 5 ADRs, scalability plan |
| [`/docs/api-spec.md`](docs/api-spec.md) | Full REST API spec, error handling strategy, auth design |
| [`/docs/data-model.md`](docs/data-model.md) | ERD, schema, indexing strategy for the v2 persistence layer |
| [`/docs/design-system.md`](docs/design-system.md) | UX flows, color/typography system, accessibility, wireframes |
| [`/docs/security.md`](docs/security.md) | STRIDE threat model, OWASP Top 10 checklist, findings (with fixes) |
| [`/docs/devops.md`](docs/devops.md) | CI/CD, hosting plan, cost estimate, rollback strategy |
| [`/docs/testing.md`](docs/testing.md) | Test strategy, test cases, manual QA checklist |

## Status & What's Left

Being direct about what "done" actually means here:

**✅ Built, and verified by actually running it:**
- The full v1 MVP request pipeline (upload → extract → prompt → validate → respond) — all 6 backend service/route files, syntax-checked and functionally tested.
- The core frontend flow (`UploadForm`, `QuizTab`, `useGenerate`) — compiled and, for `QuizTab`, tested against real user interactions (click-to-answer, scoring, retake).
- **23 automated tests, all passing** (17 backend `pytest`, 6 frontend `vitest`) — including a real generated-PDF fixture (not a mock), an intentionally-scanned/blank PDF to test the failure path, and an LLM-hallucination scenario proving the MCQ validation gate actually drops bad output.
- A security design review that caught and fixed one real bug before it shipped: `requirements.txt` was missing `python-multipart`, which FastAPI silently requires for any file-upload endpoint — the test suite itself surfaced this.

**📋 Designed in full, not yet built:**
- The v2 layer (auth, persistence, dashboard, save/search) — complete API spec, database schema, and starter code exist, but per the PRD's own scope resolution, this was never claimed as part of the 1-day MVP.

**⏳ Not yet done:**
- Actual deployment to Vercel/Render (the plan is fully written in `/docs/devops.md`, just not executed).
- A real end-to-end call to a live LLM API (all automated tests mock the LLM deliberately, to avoid burning free-tier quota on every test run — see `/docs/testing.md` Section 1).
- Screenshots and a live demo link, both blocked on the above.

## Setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY (or Gemini key)
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Testing

```bash
# Backend — 17 tests, mocked LLM, real generated PDF fixtures
cd backend && pytest -v

# Frontend — 6 tests, real component interactions
cd frontend && npx vitest run
```

## Why I Built This / What I Learned

I wanted a project that forced me through the entire lifecycle a real engineering team goes through — not just "write code that works," but requirements discovery, explicit scope negotiation, architecture decisions I could defend, a real security review, and a test suite I actually ran rather than just wrote.

The single most useful moment in the whole build was the discovery phase surfacing a real conflict: the assignment brief specified both `COMPLEXITY_LEVEL: 10/10` and `TIMELINE: 1 day, solo` — two numbers that can't both be true at once. Rather than silently picking one, I resolved it explicitly in the PRD (intermediate complexity, 1-day MVP, with the 10/10-complexity features honestly deferred to a fully-designed-but-unbuilt v2) and carried that same scope discipline through every subsequent document. That discipline is also what caught the concrete bugs and gaps in this project — a missing `requirements.txt` dependency, a spoofable file-upload check, an insecure default JWT secret, a CORS policy nobody had specified yet. None of those would have surfaced from "does the demo look like it works."

## Roadmap

See `/docs/prd.md` Section 8 for the full breakdown. Short version:

- **v2:** user accounts, persistent saved notes, a dashboard, save/search, score history across sessions — API and database schema already designed in `/docs/api-spec.md` and `/docs/data-model.md`.
- **v3 (stretch):** batch upload, spaced-repetition scheduling, quiz sharing, more languages, wrong-answer analytics.
- **Immediate next steps (pre-v2):** deploy v1 to Vercel/Render, run the real-LLM smoke test across all 3 languages, apply the three concrete security fixes flagged in `/docs/security.md` (magic-byte file validation, JWT secret startup check, CORS allow-list).

## License

MIT
