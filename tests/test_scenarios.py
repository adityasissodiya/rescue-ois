"""Directed protocol regressions, original-rule witnesses and negative controls."""

from __future__ import annotations

import hashlib

import pytest

from experiments.checker import check
from experiments.expect import evaluate
from experiments.scenarios import all_scenarios
from sim.engine import ScenarioError, canonical, run_scenario, trace_digest

SCENARIOS = {sc["id"]: sc for sc in all_scenarios()}

# Frozen fixtures of the 11 November 2026 draft rules. A change to the shared kernel or to
# the fixtures that alters these runs must be a deliberate, reviewed change: update the
# digests only together with research/claims.csv and a note in research/migration.md.
ORIG_PINS = {
    "ORIG-SPLIT-STALL": (
        "e7bd040099aedb811a34d016b4a58010dcfb677a40c94a71196f6647824ce466",
        "0c158b07c8ecb37dcf80fe62da1ebdcfe0b422e292037fa88721ba73376f2a6d",
    ),
    "ORIG-SPLIT-RECOVER-E3": (
        "79cb9742dc018f37f9ce7b87276e2e354f7a866c17af98896a5c27984fcf4838",
        "bcb0af78274901b9fc2819ff5ddacc837d204dad120d5bafd83244b08fc8fea3",
    ),
    "ORIG-DEPUTY-SAME-READING": (
        "545f9a55e898e56fe21ab6f521a13ad6b40a294c1919b4243d901bc936734dc1",
        "5ab0a6d4151055dde6f0eee11c02faa94f947601308947c9f4ab1c62da3c5802",
    ),
}


def _run(sid: str, mode: str = "symbolic"):
    trace = run_scenario(SCENARIOS[sid], mode)
    return trace, check(trace[0], trace[1:])


@pytest.mark.parametrize("sid", sorted(SCENARIOS))
def test_scenario_meets_its_expectations(sid):
    _, res = _run(sid)
    assert evaluate(SCENARIOS[sid]["expect"], res) == []


@pytest.mark.parametrize("sid", sorted(SCENARIOS))
def test_ed25519_mode_gives_the_same_trace(sid):
    assert trace_digest(run_scenario(SCENARIOS[sid], "symbolic")) == trace_digest(
        run_scenario(SCENARIOS[sid], "ed25519")
    )


@pytest.mark.parametrize(
    "sid", sorted(s for s, x in SCENARIOS.items() if x["kind"] == "positive")
)
def test_positive_scenarios_are_not_vacuous(sid):
    _, res = _run(sid)
    m = res["metrics"]
    assert res["codes"] == []
    assert m["accepted"] >= 3
    assert m["valid_renewals"] >= 1
    assert m["boundary_accepts"] >= 1 or sid == "V0-SPLIT-RECOVERY"


def test_handover_scenarios_hand_over():
    for sid in (
        "V0-HANDOVER",
        "V0-SELECTIVE-DELIVERY",
        "V0-REMOVAL",
        "V0-SPLIT-RECOVERY",
    ):
        _, res = _run(sid)
        assert len(res["metrics"]["accepted_by_key"]) >= 2, sid


@pytest.mark.parametrize("sid", sorted(ORIG_PINS))
def test_original_rule_fixtures_are_frozen(sid):
    config, trace = ORIG_PINS[sid]
    assert hashlib.sha256(canonical(SCENARIOS[sid]).encode()).hexdigest() == config
    assert trace_digest(run_scenario(SCENARIOS[sid])) == trace


def test_original_split_vote_stalls_without_safety_violation():
    trace, res = _run("ORIG-SPLIT-STALL")
    m = res["metrics"]
    assert res["codes"] == []  # a progress gap, not a separation counterexample
    assert (
        m["valid_grants_by_epoch"]["2"] == 0
    )  # neither epoch-2 proposal reached q = 3
    advanced = {e["by"] for e in trace if e["ev"] == "advance" and e["to"] == 2}
    assert advanced == {"A", "B", "C"}  # every honest signer left epoch 1 on its vote
    for u in "ABC":
        assert m["refusals"][f"{u}:epoch-advanced"] >= 2  # cannot renew epoch 1
        assert m["refusals"][f"{u}:no-valid-grant"] >= 2  # cannot renew epoch 2
    assert m["last_accept"]["e1:A"] == 100 and max(a[0] for a in m["accepts"]) == 100


def test_original_split_vote_recovers_with_coordinated_epoch_3():
    _, res = _run("ORIG-SPLIT-RECOVER-E3")
    assert res["codes"] == []
    assert res["metrics"]["first_accept"]["e3:A"] == 121


def test_deputy_same_reading_witness():
    trace, res = _run("ORIG-DEPUTY-SAME-READING")
    accepts = [e for e in trace if e["ev"] == "accept"]
    same = [e for e in accepts if e["local"] == 110]
    assert [(e["cmd"]["holder"], e["rule"]) for e in same] == [("B", "D2"), ("A", "D1")]
    assert "SAME-READING-TWO-ISSUERS" in res["codes"]


@pytest.mark.parametrize(
    "sid", sorted(s for s, x in SCENARIOS.items() if x["kind"] == "negative")
)
def test_negative_control_finds_the_intended_violation(sid):
    # A negative control passes only if the run completes and the checker reports the
    # expected violation; an exception is an infrastructure failure, not a detection.
    _, res = _run(sid)
    wanted = set(SCENARIOS[sid]["expect"]["violations_include"])
    assert wanted <= set(res["codes"])
    _, twin = _run(sid + "-CONTROL")
    assert twin["codes"] == []


def test_scenario_errors_are_not_outcomes():
    sc = dict(SCENARIOS["V0-RENEW-EXPIRY"])
    sc["events"] = list(reversed(sc["events"]))
    with pytest.raises(ScenarioError):
        run_scenario(sc)


def test_file_store_gives_the_same_trace(tmp_path):
    for sid in ("NC-COMMIT-AFTER-RELEASE-CONTROL", "V0-REMOVAL"):
        assert trace_digest(
            run_scenario(SCENARIOS[sid], store_dir=tmp_path)
        ) == trace_digest(run_scenario(SCENARIOS[sid]))
