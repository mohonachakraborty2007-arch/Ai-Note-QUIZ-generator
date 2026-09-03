"""Integration test for POST /api/v1/generate — exercises the route +
service layer together, with the LLM call mocked (see testing.md Section 1
for why: never hit the real API in an automated suite).
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.generate import router

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def valid_pdf_bytes():
    return (FIXTURES_DIR / "valid_lecture.pdf").read_bytes()


@pytest.fixture
def scanned_pdf_bytes():
    return (FIXTURES_DIR / "scanned_blank.pdf").read_bytes()


MOCK_LLM_RESPONSE = {
    "summary": "This lecture covers the first and second laws of thermodynamics.",
    "key_points": ["Energy is conserved", "Entropy never decreases in an isolated system"],
    "mcqs": [
        {
            "question": "What does the first law of thermodynamics state?",
            "options": ["Energy is conserved", "Entropy decreases", "Mass increases", "Time is reversible"],
            "correct_answer": "Energy is conserved",
            "explanation": "Energy cannot be created or destroyed, only transformed.",
        }
    ],
}


def test_generate_happy_path(client, valid_pdf_bytes, mocker):
    mocker.patch(
        "app.routes.generate.generate_structured",
        return_value=MOCK_LLM_RESPONSE,
    )

    response = client.post(
        "/api/v1/generate",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == MOCK_LLM_RESPONSE["summary"]
    assert len(body["mcqs"]) == 1


def test_generate_rejects_non_pdf_file_type(client):
    response = client.post(
        "/api/v1/generate",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
        data={"language": "en"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_FILE_TYPE"


def test_generate_rejects_invalid_language(client, valid_pdf_bytes):
    response = client.post(
        "/api/v1/generate",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
        data={"language": "fr"},  # not in {en, hi, bn}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_LANGUAGE"


def test_generate_returns_422_for_scanned_pdf(client, scanned_pdf_bytes):
    """US-5: scanned PDF gives a specific, user-facing error — not a
    generic failure."""
    response = client.post(
        "/api/v1/generate",
        files={"file": ("scanned.pdf", scanned_pdf_bytes, "application/pdf")},
        data={"language": "en"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "NO_EXTRACTABLE_TEXT"


def test_generate_drops_invalid_mcqs_before_responding(client, valid_pdf_bytes, mocker):
    """Confirms the route actually wires up the FR-3.5 validation gate —
    not just that mcq_validator works in isolation (already covered by
    test_mcq_validator.py), but that generate.py actually calls it."""
    response_with_bad_mcq = {
        "summary": "Summary text.",
        "key_points": ["Point one"],
        "mcqs": [
            {
                "question": "Good question",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "ok",
            },
            {
                "question": "Hallucinated question",
                "options": ["X", "Y"],
                "correct_answer": "Not an option",
                "explanation": "should be dropped",
            },
        ],
    }
    mocker.patch(
        "app.routes.generate.generate_structured",
        return_value=response_with_bad_mcq,
    )

    response = client.post(
        "/api/v1/generate",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    mcqs = response.json()["mcqs"]
    assert len(mcqs) == 1
    assert mcqs[0]["question"] == "Good question"


def test_generate_returns_502_when_llm_fails_after_retry(client, valid_pdf_bytes, mocker):
    from app.services.llm_client import LLMGenerationError

    mocker.patch(
        "app.routes.generate.generate_structured",
        side_effect=LLMGenerationError("LLM did not return valid JSON after 2 attempt(s)"),
    )

    response = client.post(
        "/api/v1/generate",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
        data={"language": "en"},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["error"]["code"] == "LLM_GENERATION_FAILED"
