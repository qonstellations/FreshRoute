"""FastAPI app: `/api` routes, dev CORS, and the built SPA on the same origin
(ARCHITECTURE.md section 16.1, D-18, D-20, DATABASE.md section 11).

Run: `uv run uvicorn freshroute.api.app:app --host 127.0.0.1 --port 8000`.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from freshroute.api.deps import ROOT, BadRequest, NotFound
from freshroute.api.routers import ladder, meta, replan, runs
from freshroute.config import API_CORS_ORIGINS, API_VERSION

app = FastAPI(title="FreshRoute API", version=str(API_VERSION))
app.add_middleware(CORSMiddleware, allow_origins=API_CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])
for _r in (meta, runs, ladder, replan):
    app.include_router(_r.router)


@app.exception_handler(NotFound)
def _not_found(_: Request, e: NotFound) -> JSONResponse:
    return JSONResponse({"detail": str(e)}, status_code=404)


@app.exception_handler(BadRequest)
def _bad_request(_: Request, e: BadRequest) -> JSONResponse:
    return JSONResponse({"detail": str(e)}, status_code=400)


@app.exception_handler(ValueError)  # corrupt JSON/CSV on disk is a server fault, not a 400
def _corrupt(_: Request, e: ValueError) -> JSONResponse:
    return JSONResponse({"detail": f"unreadable output file: {e}"}, status_code=500)


_dist = ROOT / "frontend" / "dist"
if _dist.is_dir():  # after /api so the SPA never shadows an endpoint
    app.mount("/", StaticFiles(directory=_dist, html=True), name="spa")
