"""A-MORE backend entrypoint (section 2.1).

Run from the repo root:

    uvicorn server.app:app --reload

CORS is open so the browser extension and the static dashboard can call the API
during development.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import (
    routes_feedback,
    routes_insights,
    routes_score,
    routes_selection,
)
from server.db import relational

app = FastAPI(title="A-MORE", version="0.1.0",
              description="Decision-support layer for dating apps.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # dev only; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_score.router)
app.include_router(routes_feedback.router)
app.include_router(routes_insights.router)
app.include_router(routes_selection.router)


@app.on_event("startup")
def _startup() -> None:
    relational.init_db()


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "A-MORE", "version": "0.1.0"}
