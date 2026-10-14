"""FastAPI app: `/api` routes, dev CORS, and the built SPA on the same origin
(ARCHITECTURE.md section 16.1, D-18, D-20, DATABASE.md section 11).

Run: `uv run uvicorn freshroute.api.app:app --host 127.0.0.1 --port 8000`.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from freshroute.api.data_access import ROOT
from freshroute.api.routes import router
from freshroute.config import API_CORS_ORIGINS, API_VERSION

app = FastAPI(title="FreshRoute API", version=str(API_VERSION))
app.add_middleware(CORSMiddleware, allow_origins=API_CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])
app.include_router(router)


@app.exception_handler(ValueError)  # bad JSON/CSV on disk: 400, never a 500 (DATABASE 11.1)
def _bad_data(_: Request, e: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(e)}, status_code=400)


_dist = ROOT / "frontend" / "dist"
if _dist.is_dir():  # after /api so the SPA never shadows an endpoint
    app.mount("/", StaticFiles(directory=_dist, html=True), name="spa")
