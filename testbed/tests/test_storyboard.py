"""The model document's storyboard (section 8), replayed: the executable model must tell
the same story as the document where the document is specific."""

from aas_testbed.metrics import decision_table, measure
from aas_testbed.model import Kind
from aas_testbed.policies import make_policy
from aas_testbed.sim import Config, simulate


def _run(policy: str, **kw):
    sim = simulate(Config(policy=make_policy(policy), seed=kw.pop("seed", 1), **kw))
    return sim, measure(sim), decision_table(sim)


def test_figure_a_s4_one_device_at_a_time():
    # Steps 4-7 under S4: A's handheld stops at T' before B activates at T; A's
    # decision made while cut off (d3) is valid and joins the journal on reconnection.
    sim, m, rows = _run("S4", case="P-A")
    assert m["a_window_s"] < m["takeover_delay_s"]
    assert m["overlap_s"] == 0 and m["residual"] == 0
    cut, heal = sim.cfg.t_cut, sim.cfg.t_cut + sim.cfg.outage
    d3 = [r for r in rows if r["signer"] == "A" and cut < r["true_ts"] < heal]
    assert d3, "A made no decision while cut off; pick another seed"
    assert all(r["truth"] == r["final"] == "authoritative" for r in d3)
    srv = sim.devices["SRV"]
    assert all(srv.arrival[r["rid"]] >= heal for r in d3)


def test_figure_b_s3_contradictory_orders_become_residual():
    # Steps 4-7 under S3 with no timeout on A's device, A not answering C: C takes over,
    # A keeps deciding; decisions after the takeover are residual, earlier ones valid.
    sim, m, rows = _run("S3", case="P-A", a_answers_voice=False)
    takeover = next(r for r in sim.acts if r.kind is Kind.TAKEOVER)
    a_rows = [r for r in rows if r["signer"] == "A"]
    late = [r for r in a_rows if r["true_ts"] > takeover.true_ts]
    early = [r for r in a_rows if r["true_ts"] < takeover.true_ts]
    assert late and early
    assert all(r["final"] == "residual" for r in late)
    assert all(r["final"] == "authoritative" for r in early)
    assert all(r["final"] == "authoritative" for r in rows if r["signer"] == "B")
    assert m["overlap_s"] > 0
    # The residuals are shown to B: B's device holds them, labelled.
    b_dev = sim.devices["V2"]
    assert all(b_dev.verdict(b_dev.records[r["rid"]], sim.cfg.eps).status.value
               == "residual" for r in late)


def test_step8_takeover_with_all_links_up():
    _, m, _ = _run("S3", case="none", a_state="incapacitated")
    assert m["successor"] == "B" and m["overlap_s"] == 0 and m["residual"] == 0


def test_step9_pb_only_local_policies_move_command():
    # Everyone loses cellular, the mesh works: the core cannot promote, and A is still
    # heard over the mesh, so nobody needs to move command; decisions stay provisional.
    for p in ("S1", "S2"):
        _, m, _ = _run(p, case="P-B", a_state="incapacitated")
        assert not m["takeover_in_outage"]
    _, m, _ = _run("S4", case="P-B")
    assert m["successor"] is None and m["a_capable_frac"] == 1
    assert m["settle_p95_s"] > 0.5 * 1200 and m["never_settled"] == 0


def test_step10_pc_s4_never_both():
    _, m, _ = _run("S4", case="P-C")
    assert m["successor"] == "B" and m["overlap_s"] == 0
