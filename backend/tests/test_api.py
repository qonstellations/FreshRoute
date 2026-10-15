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
    assert client.get("/api/health").json() == {"status": "ok", "schema_version": 2,
                                                "api_version": 1}


def test_config_verbatim(client):
    from freshroute import config
    body = client.get("/api/config").json()
    assert body["LAMBDA_SPOIL"] == config.LAMBDA_SPOIL
    assert body["MC_NAMED"] == {k: list(v) for k, v in config.MC_NAMED.items()}
    assert body["API_VERSION"] == 1 and all(k.isupper() for k in body)


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
    r = ran.get(f"/api/runs/{RUN}/reason-cards")  # cli.run writes them
    on_disk = json.loads((data_access.OUTPUTS / RUN / "reason_cards.json").read_text("utf-8"))
    assert r.status_code == 200 and r.json() == on_disk


def test_reason_cards_null_when_absent(client, tmp_path):
    (tmp_path / "no_cards").mkdir()
    (tmp_path / "no_cards" / "metrics.json").write_text("{}", encoding="utf-8")
    assert client.get("/api/runs/no_cards/reason-cards").json() is None


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


def test_milp_run_reports_progress(client, tmp_path):
    """A MILP run publishes plans while it solves; the last status carries the final version."""
    req = {"scenario": "backend/tests/fixtures/tiny_3batch", "policy": "milp", "seed": 42}
    rid = client.post("/api/runs", json=req).json()["run_id"]
    s = _wait(client, rid)
    p = s["progress"]
    assert s["state"] == "done" and p["final"] and p["version"] >= 1
    m = json.loads((tmp_path / rid / "metrics.json").read_text(encoding="utf-8"))
    assert p["net_inr"] == m["kpis"]["net_inr"]  # copied from the run, never computed by the API


def test_run_listed_by_directory_name(client, tmp_path):
    cli.run(TINY, "fifo", 42, str(tmp_path / "check_fifo"))  # --out dir != metrics.run_id
    ids = [r["run_id"] for r in client.get("/api/runs").json()["runs"]]
    assert ids == ["check_fifo"]
    assert client.get("/api/runs/check_fifo").status_code == 200


REL_TINY = "backend/tests/fixtures/tiny_3batch"


def _wait(client, job_id):
    for _ in range(600):
        s = client.get(f"/api/runs/{job_id}/status").json()
        if s["state"] != "running":
            return s
        time.sleep(0.1)
    raise AssertionError("job still running")


def test_stress_404_then_post_then_get(client, tmp_path):
    assert client.get("/api/stress?scenario=tiny_3batch&seed=42").status_code == 404
    req = {"scenario": REL_TINY, "policy": "milp", "seed": 42, "n": 4}
    r = client.post("/api/stress", json=req)
    assert r.status_code == 202 and r.json()["run_id"] == "tiny_3batch__stress__s42"
    assert _wait(client, r.json()["run_id"])["state"] == "done"
    body = client.get("/api/stress?scenario=tiny_3batch&seed=42").json()
    assert body["summary"]["n"] == 4 and body["rows"]
    bad = {"scenario": REL_TINY, "policy": "nope"}
    assert client.post("/api/stress", json=bad).status_code == 400


def test_sensitivity_404_when_absent(client):
    assert client.get("/api/sensitivity?scenario=tiny_3batch&seed=42").status_code == 404


def test_replan_post_poll_get(client, tmp_path):
    cli.run(TINY, "fifo", 42, str(tmp_path / RUN))
    ev = {"event_id": "E-T1", "type": "price_shock", "target": "dest:D1|*",
          "magnitude": 0.9, "at_h": 8}
    assert client.get(f"/api/runs/{RUN}/replan/E-T1").status_code == 404
    r = client.post("/api/replan", json={"run_id": RUN, "event": ev})
    assert r.status_code == 202 and r.json()["event_id"] == "E-T1"
    assert _wait(client, f"{RUN}__replan__E-T1")["state"] == "done"
    got = client.get(f"/api/runs/{RUN}/replan/E-T1").json()
    assert got["diff"]["event_id"] == "E-T1" and isinstance(got["narration"], str)


def test_replan_bad_event_and_run(client, tmp_path):
    cli.run(TINY, "fifo", 42, str(tmp_path / RUN))
    bad = {"event_id": "E-X", "type": "nope", "target": "*", "magnitude": 1, "at_h": 0}
    assert client.post("/api/replan", json={"run_id": RUN, "event": bad}).status_code == 400
    assert client.post("/api/replan", json={"run_id": "nope", "event": bad}).status_code == 404


def test_post_newsvendor_flag(client, tmp_path):
    body = {"scenario": REL_TINY, "policy": "fifo", "seed": 42, "flags": {"newsvendor": True}}
    assert client.post("/api/runs", json=body).status_code == 400  # MILP policies only
    body["policy"] = "milp"
    r = client.post("/api/runs", json=body)
    assert r.status_code == 202 and r.json()["run_id"] == "tiny_3batch__milp__s42__nv"
    assert _wait(client, r.json()["run_id"])["state"] == "done"


def test_records_replaces_inf(tmp_path):
    from freshroute.api.services import outputs

    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,inf\n2,-inf\n", encoding="utf-8")
    assert outputs.records(p)["records"] == [{"a": 1, "b": None}, {"a": 2, "b": None}]


@pytest.mark.parametrize("scenario", ["../secret", "backend/../../x", "/etc/passwd",
                                      "C:" + chr(92) + "Windows", chr(92) * 2 + "host"])
def test_scenario_traversal_and_absolute_rejected_400(client, scenario):
    for url, body in (("/api/runs", {"scenario": scenario, "policy": "fifo"}),
                      ("/api/stress", {"scenario": scenario, "policy": "fifo"})):
        r = client.post(url, json=body)
        assert r.status_code == 400 and "not allowed" in r.json()["detail"]


def test_corrupt_output_json_is_500(client, tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "metrics.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bad" / "reason_cards.json").write_text("{not json", encoding="utf-8")
    assert TestClient(app, raise_server_exceptions=False).get(
        "/api/runs/bad/reason-cards").status_code == 500


def test_concurrent_submit_runs_once(tmp_path):
    import threading

    from freshroute.api.jobs import JobQueue

    q, gate, calls = JobQueue(workers=4), threading.Event(), []
    done = tmp_path / "done.json"

    def fn():
        calls.append(1)
        gate.wait(5)
        done.write_text("{}")

    ts = [threading.Thread(target=q.submit_if_idle, args=(tmp_path, "j", fn, done))
          for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    gate.set()
    q._executor.shutdown(wait=True)
    assert len(calls) == 1


def test_job_error_keeps_traceback(tmp_path):
    from freshroute.api import jobs

    q = jobs.JobQueue(workers=1)

    def boom():
        raise RuntimeError("kaput")

    q.submit_if_idle(tmp_path, "j", boom, tmp_path / "never")
    q._executor.shutdown(wait=True)
    job = jobs.read_job(tmp_path, "j")
    assert job["state"] == "error" and job["error"] == "kaput"
    assert "RuntimeError: kaput" in job["traceback"]
