"""FastAPI app: `/api` routes, dev CORS, and the built SPA on the same origin
(ARCHITECTURE.md section 16.1, D-18, D-20, DATABASE.md section 11).

Run: `uv run uvicorn freshroute.api.app:app --host 127.0.0.1 --port 8000`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from freshroute.api.deps import ROOT, BadRequest, NotFound, Unavailable
from freshroute.api.routers import ladder, meta, replan, runs
from freshroute.config import API_CORS_ORIGINS, API_VERSION

app = FastAPI(title="FreshRoute API", version=str(API_VERSION))
app.add_middleware(CORSMiddleware, allow_origins=API_CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)  # reason_cards/trips are ~MBs
for _r in (meta, runs, ladder, replan):
    app.include_router(_r.router)


@app.middleware("http")
async def _cache(request: Request, call_next):
    """Serverless serves frozen demo runs: let Vercel's CDN cache GETs. Locally runs change."""
    resp = await call_next(request)
    if os.getenv("VERCEL") and request.method == "GET" and resp.status_code == 200:
        resp.headers.setdefault(
            "Cache-Control", "public, s-maxage=300, stale-while-revalidate=3600")
    return resp


@app.exception_handler(Unavailable)
def _unavailable(_: Request, e: Unavailable) -> JSONResponse:
    return JSONResponse({"detail": str(e)}, status_code=503)


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
