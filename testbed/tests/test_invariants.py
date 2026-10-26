"""Invariants over random incidents, and the stale-heartbeat counterexample."""

from dataclasses import replace

import pytest

from aas_testbed.experiments import search_config
from aas_testbed.metrics import measure
from aas_testbed.policies import POLICIES, make_policy
from aas_testbed.sim import Config, simulate


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("mode", ["strict", "closing"])
def test_invariants_under_flapping(policy, mode):
    for seed in range(20_000, 20_004):
        _, cfg = search_config(policy, seed, mode)
        m = measure(simulate(cfg))
        assert m["converged"], seed
        assert m["lost"] == 0, seed
        assert m["auth_regressions"] == 0, seed
        assert m["misclassified"] == 0, seed
        assert not m["tradeoff_violated"], seed


@pytest.mark.parametrize("policy", ["S1", "S3"])
def test_invariants_with_acceptance_effect(policy):
    for seed in range(20_000, 20_004):
        _, cfg = search_config(policy, seed, "closing")
        m = measure(simulate(replace(cfg, effect="acceptance")))
        assert m["converged"] and m["lost"] == 0, seed
        assert m["auth_regressions"] == 0 and m["misclassified"] == 0, seed


def test_takeover_on_acceptance_removes_retroactive_residuals():
    # P-B, A fit but not answering: C's takeover cannot reach the scene. Effective on
    # signature, it turns A's later orders residual after the fact; on acceptance it
    # takes effect only once B's device holds it.
    cfg = Config(policy=make_policy("S3"), case="P-B", a_answers_voice=False, seed=1)
    signed = measure(simulate(cfg))
    accepted = measure(simulate(replace(cfg, effect="acceptance")))
    assert signed["residual"] > 0 and signed["reader_flips_to_residual"] > 0
    assert accepted["residual"] == 0 and accepted["reader_flips_to_residual"] == 0


def test_simulation_is_deterministic():
    cfg = Config(policy=make_policy("S4"), case="P-C", seed=7)
    assert measure(simulate(cfg)) == measure(simulate(replace(cfg)))


def test_stale_heartbeat_reopens_a_and_acknowledged_timeout_does_not():
    cfg = Config(policy=make_policy("S4"), relay_fault=True, seed=3)
    plain = measure(simulate(cfg))
    acked = measure(simulate(replace(cfg, acked=True)))
    assert plain["overlap_s"] > 30
    assert acked["overlap_s"] == 0 and acked["residual"] == 0


def test_strict_settlement_never_settles_without_the_lost_commander():
    base = Config(policy=make_policy("S3"), case="P-A", a_state="incapacitated",
                  a_device_lost=True, seed=2)
    strict = measure(simulate(replace(base, settlement="strict")))
    closing = measure(simulate(replace(base, settlement="closing")))
    assert strict["never_settled"] > 10
    assert closing["never_settled"] <= 1  # A's last decision before the cut
