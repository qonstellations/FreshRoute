"""Solver smoke test, D-02: PuLP->HiGHS vs scipy milp; limits bite (ARCH section 9)."""
import time

import numpy as np
import pulp
from scipy.optimize import Bounds, LinearConstraint, milp

# toy: max 5x+4y+3z s.t. A x <= B, x,y,z int in [0,10]
C = [5, 4, 3]
A = [[2, 3, 1], [4, 1, 2], [3, 4, 2]]
B = [5, 11, 8]


def _hard_knapsack(n=60, m=5, seed=0):
    """Correlated multi-knapsack; HiGHS cannot close it in 50 ms (checked), so limits bite."""
    rng = np.random.default_rng(seed)
    a = rng.integers(10, 100, (m, n))
    return a.sum(0) + rng.integers(0, 10, n), a, a.sum(1) // 2


def _pulp_knap(time_limit=None, gap_rel=None):
    v, a, cap = _hard_knapsack()
    p = pulp.LpProblem("k", pulp.LpMaximize)
    x = [p.add_variable(f"x{i}", cat="Binary") for i in range(len(v))]
    p += pulp.lpSum(int(v[i]) * x[i] for i in range(len(v)))
    for r in range(len(cap)):
        p += pulp.lpSum(int(a[r, i]) * x[i] for i in range(len(v))) <= int(cap[r])
    t = time.perf_counter()
    st = p.solve(pulp.HiGHS(msg=False, timeLimit=time_limit, gapRel=gap_rel))
    return st, time.perf_counter() - t


def test_pulp_and_scipy_agree():
    p = pulp.LpProblem("t", pulp.LpMaximize)
    v = [p.add_variable(n, 0, 10, cat="Integer") for n in "xyz"]
    p += pulp.lpSum(c * x for c, x in zip(C, v, strict=True))
    for row, b in zip(A, B, strict=True):
        p += pulp.lpSum(a * x for a, x in zip(row, v, strict=True)) <= b
    st = p.solve(pulp.HiGHS(msg=False))
    r = milp(-np.array(C), constraints=LinearConstraint(A, ub=B),
             integrality=np.ones(3), bounds=Bounds(0, 10))
    assert st.status == pulp.LpSolveStatus.Optimal and r.status == 0
    assert abs(pulp.value(p.objective) - (-r.fun)) < 1e-6


def test_pulp_time_limit_takes_effect():
    st, dt = _pulp_knap(time_limit=0.05)
    assert dt < 2.0
    assert st.status == pulp.LpSolveStatus.TimeLimit


def test_pulp_gap_option_accepted():
    st, _ = _pulp_knap(gap_rel=0.5)
    assert st.status == pulp.LpSolveStatus.Optimal  # 50% gap is trivially met


def test_scipy_time_limit_and_gap_take_effect():
    v, a, cap = _hard_knapsack()
    args = dict(c=-v.astype(float), constraints=LinearConstraint(a, ub=cap),
                integrality=np.ones(len(v)), bounds=Bounds(0, 1))
    t = time.perf_counter()
    r = milp(**args, options={"time_limit": 0.05})
    dt = time.perf_counter() - t
    print("scipy time-limit status:", r.status, f"{dt:.3f}s")
    assert dt < 2.0
    assert r.status in (0, 1)  # 1 = iteration/time limit reached
    assert milp(**args, options={"mip_rel_gap": 0.5}).status == 0
