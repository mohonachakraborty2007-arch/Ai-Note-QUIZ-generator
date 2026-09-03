"""Lightweight, unauthenticated health check — safe for uptime monitors to
hit every 5 minutes indefinitely. See /docs/devops.md Section 5.

Deliberately does NOT touch the LLM API or any expensive resource — this
must stay cheap enough to ping constantly without becoming its own
resource-abuse vector (the same concern /docs/security.md raises about
/api/v1/generate)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}
