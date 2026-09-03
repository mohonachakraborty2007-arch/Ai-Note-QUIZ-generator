# Design System & UX Spec: AI Lecture Notes & Quiz Generator

**Companion docs:** `/docs/prd.md`, `/docs/architecture.md`, `/docs/api-spec.md`, `/docs/data-model.md`

> **Scope note (consistent with prior docs):** Unlike the last two prompts, this one lands mostly *inside* v1 scope already — PRD user stories US-1 through US-5 are all v1, and they map directly to three screens: Upload, Results, and the Quiz within Results. This document designs those three screens in full. The v2 screens implied by the roadmap (login, dashboard, saved-notes list) are named in the Information Architecture (Section 1) for completeness and forward-compatibility, but are **not** wireframed or coded here — designing UI for endpoints that don't exist yet in the MVP would be the same scope-creep pattern flagged in every prior doc, just moved to the frontend. If v2 gets built, those screens get their own pass.

---

## 1. Information Architecture

Derived directly from the PRD's user stories, not invented independently.

### v1 screens (in scope, designed below)

| Screen | Serves | Notes |
|---|---|---|
| **Upload** | US-1, US-2 | Single-page entry point: file upload + language selector + generate action. This *is* the app's home screen — no separate landing page needed for a utility this focused. |
| **Results** | US-1, US-2, US-4 | Tabbed view (Summary / Key Points / Quiz) rendered from one `/api/v1/generate` response. Contains the Download action (US-4). |
| **Quiz** (tab within Results) | US-3 | Question-by-question flow with instant feedback and running score, per FR-5.1–5.4. |

### v2 screens (named only — not designed in this document)

| Screen | Serves | Status |
|---|---|---|
| Login / Register | v2 auth | Not designed — no auth endpoints exist in v1. |
| Dashboard (saved notes list) | PRD FR-e/f | Not designed — depends on `/api/v2/notes` (GET), which is v2-only. |
| Note Detail (view saved note, past attempts) | v2 score history | Not designed — depends on `/api/v2/quizzes/{id}/attempts`. |

### Sitemap (v1)

```
/ (Upload)
  → generates results in-place, no route change (single-page app for v1 — no
    router library needed for 3 states on 1 screen; see Section 5)
    → Results (Summary tab | Key Points tab | Quiz tab)
```

---

## 2. UX Flow — Critical Journeys

### Journey 1: Upload → Generate → Review (US-1, US-2)
1. Student lands on Upload screen. Sees a drop zone, a language selector (defaulted to English), and a disabled "Generate" button.
2. Student drags a PDF in (or clicks to browse). File name + size appear; "Generate" enables.
3. Student picks a language (e.g., Bengali for Arindam) — this is a simple 3-option selector, not buried in a menu, since it's a core decision, not a setting.
4. Student clicks "Generate." Button shows a loading state; drop zone becomes non-interactive. A short reassuring status line appears ("Reading your PDF and generating your revision notes — this can take up to 30 seconds") so the wait doesn't feel broken (ties to PRD FR-7.2).
5. On success, the screen transitions in-place to the Results view, defaulting to the Summary tab.
6. On failure (any error code from Section 3 of the API spec), an error banner replaces the loading status with a specific, plain-language message and the Upload form re-enables for retry — never a dead end.

### Journey 2: Take the quiz (US-3)
1. From Results, student taps the "Quiz" tab.
2. One question shown at a time (chosen over "all at once" — see Wireframes, Section 4 — because it keeps focus during actual self-testing, which is the point of the feature).
3. Student taps an option. Immediately: the tapped option is marked correct/incorrect (color **and** icon, not color alone — Section 6), the correct answer is revealed if they were wrong, and the explanation text appears below.
4. A "Next" button appears only after an answer is given (prevents accidental skip-without-answering).
5. Running score is visible in the tab header throughout ("3/7"), updating after each question (FR-5.3).
6. After the last question, a final score summary screen appears with a "Retake Quiz" action (resets local state, no backend call — ADR-5) and the option to jump back to Summary/Key Points.

### Journey 3: Error recovery — scanned PDF (US-5)
1. Student uploads a scanned PDF by mistake, clicks Generate.
2. Loading state briefly appears (the app does attempt extraction — it can't know it's scanned until it tries).
3. Backend returns `422 NO_EXTRACTABLE_TEXT`. Error banner appears in place of the loading status: *"We couldn't find readable text in this PDF — it may be scanned or image-based. Try a different file, or one with selectable text."*
4. Upload form re-enables immediately; the previously-selected language stays selected (don't make the student re-pick it) so retry is low-friction.

---

## 3. UI Design System

Design choices below are tied explicitly to **domain (edtech)** and **target users (students, often under exam-crunch stress, revising in English/Hindi/Bengali)** — not generic modern-clean defaults.

### Color palette

| Token | Value | Reasoning |
|---|---|---|
| `bg-base` | `#FAFAF9` (warm off-white) | Pure white (`#FFFFFF`) at high screen brightness during late-night revision sessions is harsher on eyes; a warm off-white is calmer for exactly the "Priya, exam crunch, probably studying at night" use case. |
| `text-primary` | `#1C1917` | Near-black, not pure black — softer contrast, same late-night-reading reasoning. |
| `primary` (actions, links, active tab) | `#4F46E5` (indigo) | Indigo reads as focused/academic rather than energetic-alarming (avoids red/orange as a primary, which would clash with error states below) or corporate-cold (avoids flat blue). |
| `success` (correct answer) | `#15803D` (green) | Standard, unambiguous "correct" signal — but never used alone (Section 6: paired with a checkmark icon). |
| `error` / `danger` (incorrect answer, error banners) | `#B91C1C` (red, slightly muted) | Deliberately not a bright/saturated red — this app's "error" state includes normal wrong-quiz-answers, which happen constantly during legitimate self-testing; a harsh red repeated dozens of times per quiz session reads as punishing rather than informative. |
| `surface` (cards, tabs) | `#FFFFFF` | Pure white reserved for content surfaces sitting on the warm base — creates depth without a full elevation/shadow system. |
| `border` | `#E7E5E4` | Low-contrast neutral, used sparingly (cards, dividers) — this app is content-dense (lecture summaries); heavy borders would compete with reading. |

### Typography

**Font: Noto Sans + Noto Sans Devanagari + Noto Sans Bengali** (Google Fonts, free, self-hostable).

This is a deliberate, non-default choice: the PRD's core requirement (FR-2.2) is that summaries, key points, and full MCQs render correctly in Hindi and Bengali script — most "modern clean UI" default fonts (Inter, Helvetica Neue, system-ui) either don't cover Devanagari/Bengali at all or fall back inconsistently, producing mismatched-looking text mid-sentence. Noto's whole design mandate is cross-script visual consistency, which is exactly the failure mode this product can't afford — a Bengali summary rendering in a fallback font would visibly undermine the "coherent, non-broken" quality bar set in PRD Section 3.

| Scale | Size | Weight | Use |
|---|---|---|---|
| `text-2xl` | 24px | 600 | Screen titles ("Your Revision Notes") |
| `text-lg` | 18px | 600 | Tab labels, question prompts |
| `text-base` | 16px | 400 | Body text (summary, key points, options) — never smaller than 16px, since this is read-heavy content, often on a phone, often by a tired student |
| `text-sm` | 14px | 400 | Metadata (file name, score counter) |

### Spacing scale
Tailwind's default 4px base scale (`1`=4px, `2`=8px, `4`=16px, `6`=24px, `8`=32px) — already implied by the Architecture doc's Tailwind choice; no need to invent a custom scale for a 3-screen app.

### Component inventory

| Component | States |
|---|---|
| `Button` (primary, secondary) | default, hover, disabled, loading (spinner replaces label) |
| `FileDropzone` | empty, file-selected, drag-active, error |
| `LanguageSelector` | 3-option segmented control (not a dropdown — 3 options don't need to hide behind a click, and a visible selector reduces the chance of generating in the wrong language by mistake, which wastes the LLM quota Section 5 of the API spec is protecting) |
| `Tabs` | active, inactive (no "disabled" state needed — all 3 tabs are always available once results exist) |
| `QuizOptionButton` | default, selected, correct, incorrect, disabled (after answering) |
| `ScoreBadge` | just a running counter, no complex states |
| `ErrorBanner` | one variant, dismissible |
| `LoadingStatus` | inline text + spinner, replaces the Generate button area |

---

## 4. Wireframe Descriptions

### Upload screen
- Centered single-column layout, max-width ~560px (this is a focused single-task screen, not a dashboard — wide layouts would just add empty space).
- Top: app name/title, one-line description.
- `FileDropzone`: large tappable/droppable area, dashed border, icon + "Drop your lecture PDF here, or click to browse." On file selected: shows filename + size + an "×" to clear.
- Below: `LanguageSelector` segmented control — English | हिन्दी | বাংলা (labels shown in-language, not translated to English, so the choice is unambiguous at a glance).
- Below: primary `Button` "Generate Notes & Quiz" — disabled until a file is selected.
- **Loading state:** Button becomes a disabled loading state with spinner + "Generating…"; a status line below reads the reassurance copy from Journey 1, step 4.
- **Error state:** `ErrorBanner` appears above the dropzone (not a modal — modals interrupt and require dismissal; a banner sits alongside the still-usable form).
- **Empty state:** the screen's default state IS the empty state — no separate empty-state design needed.

### Results screen
- Full width up to ~720px, single column.
- Top: file name + selected language as small metadata, plus a "Start Over" link (clears state, returns to Upload).
- `Tabs`: Summary | Key Points | Quiz — horizontal, underline-style active indicator (simple, low-chrome, matches the content-focused palette).
- **Summary tab:** plain readable paragraph text, generous line-height (1.6) for sustained reading.
- **Key Points tab:** bulleted list, one point per line, adequate spacing (16px) between items — this is meant to be skimmable, unlike the Summary.
- Bottom of both tabs: "Download Notes" secondary button (US-4) — exports the currently-visible content plus the other non-quiz tab, as specified in FR-6.1.

### Quiz tab (states)
- **Question state:** question prompt (`text-lg`), 4 `QuizOptionButton`s stacked vertically (never side-by-side — side-by-side options are harder to scan under exam-crunch time pressure and don't reliably fit Bengali/Devanagari text at 16px), score badge in the tab header ("3/7").
- **Answered state:** selected option shows correct (green + checkmark) or incorrect (red + ×) styling; if incorrect, the actually-correct option is also highlighted green so the student sees both; explanation text appears in a light card below the options; "Next Question" button appears, replacing the (now-disabled) option buttons' interactivity.
- **Final state:** large score display ("You got 6/7"), a short encouraging line (not effusive — see tone note below), "Retake Quiz" and "Back to Summary" buttons.

**Tone note:** given the exam-crunch persona, avoid celebratory/gamified language ("AMAZING JOB!! 🎉") — it reads as patronizing under real stress. Plain, respectful confirmation ("You got 6/7 — nice work.") fits the domain better than a consumer-app tone.

---

## 5. Component Architecture

**State management: local component state only (`useState`), no global store (Redux/Zustand/Context for app-wide state).** This is a direct extension of the Architecture doc's "don't over-engineer" principle (ADR-5: client-side quiz state) — three screens sharing one API response do not need a state management library; prop-drilling one `results` object two levels deep is simpler to read and debug than introducing a store for it.

**No router library.** Upload → Results is a single conditional render based on whether `results` is populated, not a route change — there's nothing to deep-link to yet (no saved notes, no shareable URLs in v1), so React Router would be dead weight.

### Component tree

```
App
├── UploadForm            (renders when results === null)
│   ├── FileDropzone
│   ├── LanguageSelector
│   ├── ErrorBanner        (conditional)
│   └── Button
│
└── ResultsTabs            (renders when results !== null)
    ├── SummaryTab
    ├── KeyPointsTab
    ├── QuizTab
    │   └── QuizOptionButton (×4 per question)
    └── downloadNotes.js    (utility, not a component — pure function)
```

### API consumption

- `useGenerate` hook (already named in the Architecture doc's folder structure) owns the `fetch` call to `POST /api/v1/generate`, exposing `{ generate(file, language), status, results, error }`. `status` is one of `idle | loading | success | error` — this single enum drives which UI state renders, rather than juggling separate booleans (`isLoading`, `hasError`, etc.) that could contradict each other.
- The hook parses the standardized error shape from `/docs/api-spec.md` Section 3 (`{ error: { code, message } }`) and surfaces `error.message` directly — the API's error messages were explicitly designed to be user-safe (per FR-7.1), so the frontend doesn't need its own error-message-mapping layer.

---

## 6. Accessibility

Scoped to the PRD's stated baseline (NFR: "usable via keyboard... not a full WCAG AA audit," documented as a known MVP limitation) — not overclaiming full compliance, but the specific things that matter for *this* product:

- **Never color-alone for correct/incorrect** (Section 3, Section 4): every quiz feedback state pairs color with an icon (✓/×) and text, so the app remains usable for colorblind students without needing a settings toggle.
- **Keyboard-operable quiz:** `QuizOptionButton`s are real `<button>` elements (not styled `<div>`s with click handlers), so Tab/Enter/Space work natively — this is the cheapest, highest-value accessibility decision available and directly satisfies the PRD's stated baseline.
- **`aria-live="polite"` region** around the loading status and error banner, so screen reader users are told generation succeeded/failed without needing to hunt for the change.
- **Focus management on tab switch:** moving to the Quiz tab moves focus to the first question's heading, so screen reader users land on new content rather than staying anchored to the tab control.
- **Contrast:** the palette in Section 3 was chosen with contrast in mind (`text-primary` on `bg-base` and `surface` both exceed 4.5:1); not independently audited against full WCAG AA, consistent with the PRD's documented limitation.

---

## 7. Responsive Strategy

**Mobile-first**, breakpoints via Tailwind defaults (`sm:640px`, `md:768px`, `lg:1024px`).

**Reasoning:** the exam-crunch persona (Priya) plausibly studies from whatever device is in hand at 11pm, and the Bengali/Hindi-medium persona (Arindam) skews toward mobile-primary usage patterns common among regional-language student populations — designing desktop-first and retrofitting mobile would risk exactly the population this product's multilingual feature is meant to serve. Concretely: the single-column layouts in Section 4 are mobile-native by default (no multi-column reflow needed), the `QuizOptionButton`s stack vertically at every breakpoint (Section 4's reasoning holds even more strongly on mobile), and the `LanguageSelector` segmented control needs to stay comfortably tappable at the `sm` breakpoint (44px minimum touch target) rather than shrinking to fit more on one line.

---

## 8. Starter Code

Three pieces, covering the full Upload→Generate→Quiz flow:

1. **`useGenerate.js`** — the API-consuming hook.
2. **`UploadForm.jsx`** — the Upload screen (Journey 1).
3. **`QuizTab.jsx`** — the Quiz (Journey 2), the most stateful/interesting piece of UI in the product.

Code files are under `frontend/src/` matching the Architecture doc's folder structure.
