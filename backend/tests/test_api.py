"""HTTP API contract (DATABASE.md section 11) via TestClient, against a tmp outputs/ dir."""
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from freshroute import cli
from freshroute.api import data_access
from freshroute.api.app import app

TINY = str(Path(__file__).parent / "fixtures" / "tiny_3batch")
RUN = "tiny_3batch__fifo__s42"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(data_access, "OUTPUTS", tmp_path)
    return TestClient(app)


@pytest.fixture(scope="module")
def run_outputs(tmp_path_factory):
    out = tmp_path_factory.mktemp("outputs")
    cli.run(TINY, "fifo", 42, str(out / RUN))
    return out


@pytest.fixture
def ran(run_outputs, monkeypatch):
    monkeypatch.setattr(data_access, "OUTPUTS", run_outputs)
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "schema_version": 1,
                                                "api_version": 1}


def test_scenarios_sorted(client):
    names = [s["name"] for s in client.get("/api/scenarios").json()]
    assert names == sorted(names) and "small" in names


def test_fixture_fallback_when_outputs_empty(client):
    assert client.get("/api/runs").json() == {"runs": [], "fixture": True}
    rid = json.loads(data_access.FIXTURE.read_text(encoding="utf-8"))["run_id"]
    run = client.get(f"/api/runs/{rid}").json()
    assert run["fixture"] is True and "kpis" in run
    assert (run["baseline"], run["validation"], run["manifest"]) == (None, None, None)


def test_run_list_and_verbatim_metrics(ran, run_outputs):
    body = ran.get("/api/runs").json()
    assert body == {"runs": [{"run_id": RUN, "scenario": "tiny_3batch", "policy": "fifo",
                              "seed": 42, "has_ladder": False}], "fixture": False}
    got = ran.get(f"/api/runs/{RUN}").json()
    metrics = json.loads((run_outputs / RUN / "metrics.json").read_text(encoding="utf-8"))
    assert {k: got[k] for k in metrics} == metrics
    assert got["validation"] is not None and got["manifest"]["run_id"] == RUN
    assert got["fixture"] is False


def test_unknown_run_404(ran):
    assert ran.get("/api/runs/nope__fifo__s1").status_code == 404
    assert ran.get("/api/runs/nope__fifo__s1/status").status_code == 404


def test_tables_json_and_csv(ran, run_outputs):
    t = ran.get(f"/api/runs/{RUN}/tables/plan").json()
    assert t["columns"][0] == "shipment_id" and len(t["records"]) > 0
    r = ran.get(f"/api/runs/{RUN}/tables/plan?format=csv")
    assert r.headers["content-type"].startswith("text/csv")
    assert r.content == (run_outputs / RUN / "plan.csv").read_bytes()
    assert ran.get(f"/api/runs/{RUN}/tables/metrics").status_code == 404


def test_dispatch_sheet_and_reason_cards(ran):
    sheet = ran.get(f"/api/runs/{RUN}/dispatch-sheet").json()
    assert isinstance(sheet["csv"], list) and isinstance(sheet["text"], str)
    r = ran.get(f"/api/runs/{RUN}/reason-cards")
    assert r.status_code == 200 and r.json() is None


def test_ladder_absent_404(ran):
    assert ran.get("/api/ladder?scenario=tiny_3batch&seed=42").status_code == 404


@pytest.mark.parametrize("policy", ["nope", "organizer_baseline"])
def test_post_bad_policy_400(client, policy):
    r = client.post("/api/runs", json={"scenario": TINY, "policy": policy, "seed": 42})
    assert r.status_code == 400
    if policy == "organizer_baseline":
        assert r.json()["detail"] == cli.ORGANIZER_BASELINE_BLOCKED


def test_post_bad_scenario_400(client, tmp_path):
    r = client.post("/api/runs", json={"scenario": str(tmp_path / "x"), "policy": "fifo"})
    assert r.status_code == 400


def test_post_run_202_then_done(client, tmp_path):
    req = {"scenario": "backend/tests/fixtures/tiny_3batch", "policy": "fifo", "seed": 42}
    r = client.post("/api/runs", json=req)  # repo-relative path, as the UI sends it
    assert r.status_code == 202 and r.json()["run_id"] == RUN
    for _ in range(300):
        s = client.get(f"/api/runs/{RUN}/status").json()
        if s["state"] != "running":
            break
        time.sleep(0.1)
    assert s["state"] == "done", s
    assert (tmp_path / RUN / "metrics.json").is_file()
    assert json.loads((tmp_path / ".api" / "jobs" / f"{RUN}.json").read_text())["state"] == "done"
