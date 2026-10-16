"""Serverless mode (VERCEL set): saved runs are served, live solves are refused (503),
and importing the API does not pull in the solver stack."""
import subprocess
import sys

from fastapi.testclient import TestClient

from freshroute.api.app import app


def test_solves_refused_on_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    c = TestClient(app)
    assert c.get("/api/capabilities").json() == {"live_solves": False}
    for path, body in (("/api/runs", {"scenario": "x", "policy": "milp", "seed": 1}),
                       ("/api/stress", {"scenario": "x", "policy": "milp", "n": 1, "seed": 1}),
                       ("/api/replan", {"run_id": "x", "event": {}})):
        assert c.post(path, json=body).status_code == 503


def test_live_solves_enabled_locally(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    assert TestClient(app).get("/api/capabilities").json() == {"live_solves": True}


def test_import_is_lazy():
    code = "import freshroute.api.app, sys; sys.exit('highspy' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
