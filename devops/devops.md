# DevOps & Deployment: AI Lecture Notes & Quiz Generator

**Companion docs:** `/docs/prd.md`, `/docs/architecture.md`, `/docs/api-spec.md`, `/docs/security.md`

> **Scope note (consistent with prior docs):** This plan is built for **v1** — the stateless, no-auth MVP actually described in the pasted Architecture doc. Where a v2 decision (a database, staging environment) would meaningfully change something here, it's noted briefly, not designed in full — same discipline as every prior doc in this series.

---

## 1. Environment Strategy

**Two environments: local and production. No staging.**

This is a deliberate call, not an oversight: a staging environment earns its cost when there's a database to test migrations against safely, or a team that needs a shared pre-prod integration point. v1 has neither — it's a single stateless service with no schema to migrate and no second developer to coordinate with. A staging environment here would be pure overhead against the 1-day timeline for zero risk reduction. **This changes at v2**: once a real Postgres database and migrations (Alembic, per the Data Model doc) exist, a staging environment becomes worth its cost — testing a migration against production data for the first time is a real risk a solo staging tier meaningfully reduces.

| | **Local** | **Production** |
|---|---|---|
| Frontend | `vite dev` on `localhost:5173` | Vercel (free tier), deployed from `main` |
| Backend | `uvicorn --reload` on `localhost:8000` | Render (free tier), deployed from `main` |
| `VITE_API_BASE_URL` | `http://localhost:8000` | `https://<app>.onrender.com` |
| CORS allow-list (backend) | `http://localhost:5173` | `https://<app>.vercel.app` (exact origin, never `*` — per `/docs/security.md` A05 finding) |
| LLM API key | Personal dev key, low-usage | Same key or a separate one; either way, real spend — see Section 4 |
| Secrets source | Local `.env` (gitignored, never committed) | Render/Vercel dashboard environment variables |

---

## 2. CI/CD Pipeline

**Tool: GitHub Actions** — free for public repos and generously free (2,000 minutes/month) for private ones, which comfortably covers a single-developer project's usage.

**Important scoping decision:** GitHub Actions here handles **CI only** (lint, test, security scan) as a quality gate on every push/PR — it does **not** handle deployment. Vercel and Render both deploy automatically on push to `main` via their own native Git integration (the "zero-config deploys from Git" already chosen in the Architecture doc's hosting justification). Writing custom deploy steps in GitHub Actions to replicate what Vercel/Render already do for free would be redundant work with no benefit — the right move is to let CI gate the code, and let the hosting platforms' own integration handle shipping it.

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    name: Backend (lint, test, security)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff bandit pip-audit pytest

      - name: Lint (ruff)
        run: ruff check .

      - name: Security scan (bandit)
        run: bandit -r app -ll

      - name: Dependency vulnerability scan (pip-audit)
        run: pip-audit -r requirements.txt

      # NOTE: no test hits the real LLM API — every test mocks
      # services/llm_client.py. Real API calls in CI would burn free-tier
      # quota on every push, which is exactly the resource-abuse risk
      # /docs/security.md flags for the unauthenticated /generate endpoint.
      - name: Run tests
        run: pytest -v

  frontend:
    name: Frontend (lint, build, security)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint (eslint)
        run: npm run lint

      - name: Dependency vulnerability scan
        run: npm audit --audit-level=high

      # Build here is a CI correctness gate, not a deploy step — Vercel
      # runs its own build independently when it deploys from `main`.
      - name: Build
        run: npm run build
```

### `.github/dependabot.yml`

Referenced in `/docs/security.md` Section 6 — the config that actually turns that recommendation into something running.

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"

  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## 3. Containerization

**Decision: no Docker on the deployment path. A backend Dockerfile is provided anyway, as an optional local-dev-parity and portfolio artifact — not part of the critical path.**

**Justification for not deploying via Docker:** Render's native Python buildpack already does exactly what's needed here (installs `requirements.txt`, runs `uvicorn`) with zero extra configuration, and it's what the Architecture doc's "zero-config deploys from Git" hosting choice assumes. Introducing Docker into the deploy path would mean writing and maintaining a Dockerfile, a `.dockerignore`, and Render's Docker-specific build config — real work with no functional benefit, since the native buildpack path is equally free and strictly simpler for a single FastAPI service with no unusual system dependencies.

**Why provide one anyway:** Docker familiarity is a reasonable thing to demonstrate in a portfolio project, and a Dockerfile is genuinely useful for local dev parity (guarantees "works on my machine" actually matches the deployed Python version) even when it's not the deploy mechanism. It's included below as a real, working artifact — explicitly optional, not required to ship v1.

### `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first, separately from app code, so Docker's layer
# cache is invalidated only when requirements.txt actually changes — not
# on every code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Render (and most PaaS providers) inject PORT at runtime; default to 8000
# for local `docker run` convenience.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

**Frontend does not get a Dockerfile.** A Vite React app builds to static files (HTML/JS/CSS) — there's no server runtime to containerize. Vercel's build pipeline consumes the repo directly and serves the static output from its CDN; wrapping that in a container (e.g., an nginx image serving the built assets) would only make sense if deploying to a platform without native static-site hosting, which isn't the case here.

---

## 4. Hosting Plan & Cost Estimate

| Service | Choice | Free tier limits (relevant ones) | Cost |
|---|---|---|---|
| Frontend | Vercel (Hobby/free) | 100GB bandwidth/month, unlimited deployments | $0 |
| Backend | Render (free web service) | 750 instance-hours/month (covers 1 always-on-ish service), spins down after ~15 min idle → cold start on next request (already flagged in Architecture doc Section 5) | $0 |
| Domain | None — use the platform-provided `*.vercel.app` / `*.onrender.com` subdomains | — | $0 (a custom domain would run ~$10–15/year; not worth it for a portfolio/demo project, skip it) |
| LLM API | 🔴 **Needs an honest correction, not carried forward from the Architecture doc as-is:** Anthropic's Claude API does **not** have an ongoing free tier — only initial trial credits (currently around a few dollars, subject to change). **Google's Gemini 1.5 Flash free tier is the actually-sustainable $0 choice** for continued use beyond initial testing/demo. If the Claude API is preferred for output quality, budget for trial credits covering development + the grading demo only, and treat it as a time-boxed exception to the $0 constraint, not a standing assumption. | Free tier real / trial credits time-boxed | $0 (Gemini) or ~a few $ one-time (Claude trial) |
| Error tracking | Sentry (free tier) | 5,000 events/month | $0 |
| Uptime monitoring | UptimeRobot (free tier) | 50 monitors, 5-minute check interval | $0 |
| **Total** | | | **$0/month**, assuming Gemini for sustained LLM use |

---

## 5. Monitoring & Logging

Minimal viable observability for this scale — enough to know when something's broken, not a full production observability stack.

- **Backend logs:** Render's built-in log viewer, fed by the structured JSON logging already planned in `/docs/api-spec.md` Section 3 (one line per request: `request_id`, route, status, error code on failure). No separate log aggregation service needed at this traffic volume — Render's own dashboard is sufficient and free.
- **Frontend errors:** Sentry's free tier (5,000 events/month is generous at this scale) catches unhandled JS exceptions in production that would otherwise be invisible once deployed — genuinely useful for a solo project since there's no one else who'd notice a broken build in the wild.
- **Uptime monitoring, with a useful side effect:** UptimeRobot pinging a health endpoint every 5 minutes serves double duty — it alerts if the backend is actually down, *and* the regular pings help keep Render's free-tier instance from fully spinning down between real user requests, partially mitigating the cold-start issue the Architecture doc already flags (Section 5). Not a complete fix (Render still enforces its own sleep policy), but a free, low-effort improvement worth taking.
- **A `/health` endpoint is required for this and doesn't exist yet** — flagging this as a small, concrete gap: none of the routes built so far (`/api/v1/generate`, `/api/v2/notes`) are suitable for uptime pings, since hitting `/generate` repeatedly would itself be the resource-abuse pattern `/docs/security.md` warns about. A trivial addition closes this:

```python
# backend/app/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Lightweight, unauthenticated, no side effects — safe for
    uptime monitors to hit every 5 minutes indefinitely."""
    return {"status": "ok"}
```

(Registered in `app/main.py` alongside the existing routers — not shown in full here since `main.py` wasn't part of this series' prior deliverables.)

---

## 6. Environment Variables & Secrets Management

- **Local:** `.env` file per the Architecture doc's existing `.env.example` pattern — gitignored, never committed, populated by each developer (in this case, just you) individually.
- **Production:** secrets live only in Vercel's and Render's own environment variable dashboards — `ANTHROPIC_API_KEY` (or Gemini equivalent) and, once v2 lands, `JWT_SECRET` and `DATABASE_URL` on the Render side; `VITE_API_BASE_URL` on the Vercel side. Neither platform requires (or benefits from) a dedicated secrets vault at this scale — that's a "with more time / at real production scale" answer, already noted the same way in `/docs/security.md` Section 4.
- **CI:** deliberately needs **no secrets at all** in the pipeline above — every test mocks `llm_client.py` rather than calling a real API key from within GitHub Actions, both to avoid burning LLM quota on every push and to avoid the operational overhead of managing a CI-scoped API key at all. If integration tests against the real LLM are ever added, they should be a separate, manually-triggered workflow, not part of the on-every-push CI gate.
- **The `JWT_SECRET` startup-check fix from `/docs/security.md` Section 3** (fail loudly if unset in production rather than silently falling back to the insecure default) is the operational counterpart to this section — worth cross-referencing rather than restating, since it's the one place a misconfigured environment variable becomes a security issue, not just a broken deploy.

---

## 7. Rollback Strategy

**No custom rollback tooling — both hosting platforms already provide this for free, and building anything on top of it would be unjustified effort at this scale.**

- **Vercel:** every deployment is retained and instantly promotable — rolling back the frontend is a dashboard click (or `vercel rollback` via CLI) to re-promote the last known-good deployment, with no rebuild needed.
- **Render:** similarly keeps deploy history per service; rolling back the backend is a dashboard action to redeploy a previous successful build.
- **Manual fallback (always available, no platform dependency):** `git revert` the breaking commit and push to `main` — both platforms' auto-deploy-on-push picks this up the same way as any other change, so this always works even if the dashboard rollback UI is somehow unavailable.

**Post-deploy smoke test, tying back to Section 5's health endpoint:** after any deploy, hit `GET /health` and confirm a `200` before considering the deploy verified — this is a 5-second manual check for a solo project at this scale; a full automated post-deploy smoke-test job (Actions workflow that curls `/health` after Render reports deploy-complete) is a reasonable "with more time" addition but isn't necessary to justify for a single-developer, low-traffic deployment.

**What actually breaks a deploy here, concretely, given everything reviewed so far:** the most likely real failure mode isn't a code bug — it's a missing or misconfigured environment variable (the `JWT_SECRET` default-value gap and the CORS allow-list from `/docs/security.md` are exactly this class of risk). The rollback strategy above handles code regressions well; **the actual mitigation for env-var misconfiguration is the startup-check fix in Section 6**, since a bad env var would get redeployed identically on rollback too — rollback undoes code, not configuration.
