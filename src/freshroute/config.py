"""Tunables (ARCHITECTURE.md section 19). Coefficients not listed here come from the dataset.

Source tags: [doc] = research doc, [team] = team assumption.
"""

Q10_DEFAULT = 2.0  # [doc] unverified convention; per-commodity value in data wins
DISPATCH_HOUR = 5  # [team] A-02; scenario.json dispatch_hour overrides
LAMBDA_SPOIL = 1.0  # [team]
EPS_FEFO = 1.0  # [team] INR*h/kg
OVERSHIP_SLACK = 0.05  # [team]
PHI_BALANCE = 0.5  # [team]
MAX_UPLIFT = 0.5  # [team] A-11
MILP_TIME_LIMIT_S = 30  # [doc]
MIP_REL_GAP = 0.01  # [team]
AGG_RSL_BUCKET_H = 6  # [team]
PENALTY_MULT = 10  # [team] x max price
DISCOUNT_RISK_BREAKS = (0.10, 0.30, 0.50)  # [doc]
DISCOUNT_TIERS_PCT = (0, 10, 20, 35)  # [doc]
DISCOUNT_TIME_TRIGGER_H = 24  # [doc]
MC_N = 200  # [doc]
MC_N_FALLBACK = 50  # [doc]
NEWSVENDOR_CLAMP = (0.05, 0.95)  # [team]
NEWSVENDOR_MARKDOWN_REF = 0.20  # [team]
DEFAULT_SEED = 42  # [doc]
FLOAT_TOL = 1e-6  # [team] kg and h comparisons
SCHEMA_VERSION = 1  # DATABASE.md section 1
