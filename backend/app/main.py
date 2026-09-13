"""Application entry point — creates the FastAPI app and wires in the routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import generate, notes

app = FastAPI(title="AI Note & Quiz Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "https://ai-note-quiz-generator-c655zkmph-mohmakes.vercel.app",
], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(notes.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}