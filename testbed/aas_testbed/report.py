"""REPORT.md from the experiment CSVs.

The report has no prose conclusions of its own: it states each claim of the paper and
the model document as a predicate, and counts the runs in which it holds. FINDINGS.md
interprets the numbers.
"""

from __future__ import annotations

import csv
import statistics
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .experiments import FAULTS, QUESTIONS
from .policies import POLICIES

Row = dict[str, object]


def _parse(v: str) -> object:
    if v == "":
        return None
    if v in ("True", "False"):
        return v == "True"
    try:
        f = float(v)
    except ValueError:
        return v
    return int(f) if f.is_integer() and "." not in v else f


def load(out: Path, name: str) -> list[Row]:
    path = out / f"{name}.csv"
    if not path.exists():
        return []
    with path.open() as f:
        return [{k: _parse(v) for k, v in row.items()} for row in csv.DictReader(f)]


def where(rows: Iterable[Row], **eq) -> list[Row]:
    return [r for r in rows if all(r.get(k) == v for k, v in eq.items())]


def med(rows: list[Row], key: str) -> float | None:
    xs = [r[key] for r in rows if r.get(key) is not None]
    return statistics.median(xs) if xs else None


def frac(rows: list[Row], pred: Callable[[Row], bool]) -> str:
    if not rows:
        return "-"
    return f"{sum(1 for r in rows if pred(r))}/{len(rows)}"


def fmt(x: object) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.0f}" if abs(x) >= 10 else f"{x:.2g}"
    return str(x)


def table(header: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(fmt(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


# -- claims -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    cid: str
    source: str
    text: str
    experiment: str
    select: dict
    holds: Callable[[Row], bool]
    test: str  # the predicate, in words
    only: Callable[[Row], bool] | None = None  # a further filter on the runs
    exists: bool = False  # the claim says something can happen, not that it always does

    def rows(self, data: dict[str, list[Row]]) -> list[Row]:
        rs = where(data.get(self.experiment, []), **self.select)
        return [r for r in rs if self.only(r)] if self.only else rs


def _near(x: object, target: float, tol: float) -> bool:
    return x is not None and abs(float(x) - target) <= tol


L, T, TP, DETECT, CALL, OUTAGE = 90.0, 300.0, 240.0, 120.0, 60.0, 1200.0

CLAIMS = [
    Claim("H1", "Table II, S0", "A keeps recording, without limit", "matrix",
          {"policy": "S0", "case": "P-A", "a_state": "alive"},
          lambda r: r["a_capable_frac"] == 1, "A's device accepts throughout the outage"),
    Claim("H2", "Table II, S0", "Command never moves", "matrix", {"policy": "S0"},
          lambda r: r["successor"] is None, "no one but A ever records"),
    Claim("H3", "Table II, S0", "No command at all if A is incapacitated", "matrix",
          {"policy": "S0", "a_state": "incapacitated"},
          lambda r: r["headless_outage_s"] >= OUTAGE - 2, "nobody records for the outage"),
    Claim("H4", "Table II, S1", "A keeps recording for one lease window L", "matrix",
          {"policy": "S1", "case": "P-A", "a_state": "alive"},
          lambda r: _near(r["a_window_s"], L, 5), "A stops within 5 s of L"),
    Claim("H5", "Table II, S1", "Command moves as soon as B reaches the core", "matrix",
          {"policy": "S1", "case": "P-A"},
          lambda r: r["takeover_in_outage"], "B records during the outage"),
    Claim("H6", "Table II, S1", "(c) fails: two edges overlap for up to L", "matrix",
          {"policy": "S1", "case": "P-A", "a_state": "alive"},
          lambda r: 0 < r["overlap_outage_s"] <= L + 5, "0 < overlap <= L"),
    Claim("H7", "§II-D obs. 2", "In P-B, S1 and S2 cannot move command", "matrix",
          {"case": "P-B"}, lambda r: not r["takeover_in_outage"],
          "no takeover during the outage", only=lambda r: r["policy"] in ("S1", "S2")),
    Claim("H8", "Table II, S2", "(c) holds: one edge at a time", "matrix",
          {"policy": "S2", "case": "P-A"}, lambda r: r["overlap_s"] == 0, "no overlap"),
    Claim("H9", "Table II, S2", "Command moves after L plus a margin", "matrix",
          {"policy": "S2", "case": "P-A"},
          lambda r: r["takeover_delay_s"] is not None and r["takeover_delay_s"] >= L,
          "takeover delay >= L"),
    Claim("H10", "Table II, S3", "Command moves when C is reachable (P-A, A unfit)",
          "matrix", {"policy": "S3", "case": "P-A", "a_state": "incapacitated"},
          lambda r: r["takeover_in_outage"], "B records during the outage"),
    Claim("H11", "§II-D obs. 2", "In P-B, S3 and S4 can still move command", "matrix",
          {"case": "P-B", "a_state": "incapacitated"}, lambda r: r["takeover_in_outage"],
          "B records during the outage (A unfit)",
          only=lambda r: r["policy"] in ("S3", "S4")),
    Claim("H12", "Table II, S3", "(c) holds with a lease on A's side (S3L), any L",
          "lease", {"policy": "S3L", "a_state": "alive, no voice"},
          lambda r: r["overlap_s"] == 0, "no overlap (A fit, does not answer C)"),
    Claim("H13", "Table II, S4", "A keeps recording until its own timeout T'", "matrix",
          {"policy": "S4", "case": "P-A", "a_state": "alive"},
          lambda r: _near(r["a_window_s"], TP, 5), "A stops within 5 s of T'"),
    Claim("H14", "Table II, S4", "Command moves automatically after T", "matrix",
          {"policy": "S4", "case": "P-A"},
          lambda r: _near(r["takeover_delay_s"], T, 5), "takeover within 5 s of T"),
    Claim("H15", "Table II, S4", "(c) holds if T' < T (fixed partitions)", "matrix",
          {"policy": "S4"}, lambda r: r["overlap_s"] == 0, "no overlap"),
    Claim("H16", "Table II, S4", "(c) holds if T' < T (random flapping)", "search",
          {"policy": "S4", "acked": False}, lambda r: r["overlap_s"] == 0, "no overlap",
          only=lambda r: r["timeout"] - r["primary_timeout"] >= 5
          and r["handover_to_s_after"] is None),
    Claim("H16'", "Proposed fix", "As H16, with T' acknowledged", "search",
          {"policy": "S4", "acked": True}, lambda r: r["overlap_s"] == 0, "no overlap",
          only=lambda r: r["timeout"] - r["primary_timeout"] >= 5
          and r["handover_to_s_after"] is None),
    Claim("H17", "Table II, S5", "(c) fails: both record", "matrix",
          {"policy": "S5", "case": "P-A", "a_state": "alive"},
          lambda r: r["overlap_s"] > 0, "overlap > 0"),
    Claim("H18a", "§II-C", "Stopping A early (S2, S4) avoids residuals", "matrix",
          {"case": "P-A", "a_state": "alive"}, lambda r: r["residual"] == 0,
          "no residuals", only=lambda r: r["policy"] in ("S2", "S4")),
    Claim("H18b", "§II-C", "... but not completeness gaps", "matrix",
          {"case": "P-A", "a_state": "alive"}, lambda r: r["missing_at_heal"] > 0,
          "valid decisions missing at the core at heal",
          only=lambda r: r["policy"] in ("S2", "S4"), exists=True),
    Claim("H19", "Model doc §9", "One-way link under S4: A and B both accept", "faults",
          {"policy": "S4"}, lambda r: r["overlap_s"] > 60, "overlap > 60 s",
          only=lambda r: "mute" in r["fault"] or "deaf" in r["fault"]),
    Claim("H19'", "Proposed fix", "S3 in P-B, A fit but silent: no retroactive residuals "
          "when a takeover takes effect on acceptance", "faults", {"policy": "S3"},
          lambda r: r["residual_in_outage"] == 0, "no residual made during the outage",
          only=lambda r: "effective when accepted" in r["fault"]),
    Claim("H20", "Model doc §7", "Every valid decision is eventually settled",
          "settlement", {}, lambda r: r["never_settled"] == 0, "never_settled == 0"),
    Claim("H21", "Model doc §9", "Within the clock bound, in-doubt contains the damage",
          "clock", {"variant": "bounded"}, lambda r: r["misclassified"] == 0,
          "no misclassified decision"),
    Claim("H22", "Model doc §9", "Beyond the clock bound, decisions can be misclassified",
          "clock", {"variant": "A beyond bound"}, lambda r: r["misclassified"] > 0,
          "misclassified > 0", exists=True),
]


def _claims_section(data: dict[str, list[Row]]) -> str:
    rows = []
    for c in CLAIMS:
        rs = c.rows(data)
        if not rs:
            rows.append([c.cid, c.source, c.text, c.test, "-", "not run"])
            continue
        k = sum(1 for r in rs if c.holds(r))
        if c.exists:
            verdict = "holds" if k else "never observed"
        else:
            verdict = "holds" if k == len(rs) else f"fails in {len(rs) - k} runs"
        rows.append([c.cid, c.source, c.text, c.test, f"{k}/{len(rs)}", verdict])
    return ("A universal claim holds only if its test holds in every run; an existential "
            "claim (\"can happen\") holds if it happens in at least one.\n\n"
            + table(["#", "Source", "Claim", "Tested as", "Runs where the test holds",
                     "Verdict"], rows))


# -- sections ---------------------------------------------------------------------------

MATRIX_COLS = [
    ("a_window_s", "A records, s"),
    ("takeover_delay_s", "takeover, s"),
    ("overlap_s", "overlap, s"),
    ("headless_outage_s", "no command, s"),
    ("residual", "residual"),
    ("refused_legit", "refused valid"),
    ("successor_blind", "successor blind"),
    ("missing_at_heal", "missing at core"),
    ("settle_p95_s", "settle p95, s"),
    ("never_settled", "never settled"),
    ("reader_flips_to_residual", "crew flips"),
]


def _matrix_section(rows: list[Row]) -> str:
    parts = []
    for case in ("none", "P-A", "P-B", "P-C"):
        for a in ("alive", "alive, no voice", "incapacitated"):
            sub = where(rows, case=case, a_state=a)
            if not sub:
                continue
            body = []
            for p in POLICIES:
                pr = where(sub, policy=p)
                if pr:
                    body.append([p, len(pr)] + [med(pr, k) for k, _ in MATRIX_COLS])
            parts.append(f"#### {case}, A {a}\n\n"
                         + table(["Policy", "n"] + [h for _, h in MATRIX_COLS], body))
    return "\n\n".join(parts)


def _timeout_section(rows: list[Row]) -> str:
    outages = sorted({r["outage"] for r in rows})
    ts = sorted({r["T"] for r in rows})
    alive = [[t] + [frac(where(rows, T=t, outage=o, a_state="alive"),
                         lambda r: r["needless_takeover"]) for o in outages] for t in ts]
    costs = []
    for t in ts:
        rs = where(rows, T=t, a_state="incapacitated")
        al = where(rows, T=t, a_state="alive", outage=max(outages))
        costs.append([t, med(rs, "takeover_delay_s"), med(al, "refused_legit"),
                      med(al, "successor_blind"), med(al, "settle_p95_s")])
    return ("Needless takeovers (A fit, only cut off), runs with a takeover / runs, by "
            "outage length (columns, s):\n\n"
            + table(["T, s"] + [f"{o:g}" for o in outages], alive)
            + f"\n\nCost of waiting when A is unfit, and of a takeover when A is fit "
              f"(A fit: outage {max(outages):g} s):\n\n"
            + table(["T, s", "takeover delay (A unfit), s", "refused valid (A fit)",
                     "successor blind (A fit)", "settle p95 (A fit), s"], costs))


def _lease_section(rows: list[Row]) -> str:
    body = []
    for p in ("S1", "S2", "S3L"):
        for a in ("alive", "alive, no voice"):
            if p != "S3L" and a != "alive":
                continue  # voice only matters to C
            for lease in sorted({r["L"] for r in rows}):
                cells = [p, a, lease]
                for case in ("P-A", "P-B"):
                    al = where(rows, policy=p, L=lease, case=case, a_state=a)
                    cells += [med(al, "overlap_s"), med(al, "headless_outage_s"),
                              med(al, "residual")]
                body.append(cells)
    return table(["Policy", "A", "L, s", "P-A overlap", "P-A no command", "P-A residual",
                  "P-B overlap", "P-B no command", "P-B residual"], body)


def _detect_section(rows: list[Row]) -> str:
    body = []
    for d in sorted({r["detect"] for r in rows}):
        cells = [d]
        for p in ("S1", "S2"):
            al = where(rows, policy=p, detect=d, a_state="alive")
            cells += [med(al, "overlap_s"), med(al, "residual"), med(al, "takeover_delay_s")]
        body.append(cells)
    return table(["detect, s", "S1 overlap", "S1 residual", "S1 takeover",
                  "S2 overlap", "S2 residual", "S2 takeover"], body)


def _margin_section(rows: list[Row]) -> str:
    combos = sorted({(r["period"], r["eps"]) for r in rows})
    parts = []
    for acked in (False, True):
        sub = where(rows, acked=acked)
        if not sub:
            continue
        body = []
        for m in sorted({r["margin"] for r in sub}):
            body.append([m] + [frac(where(sub, margin=m, period=p, eps=e),
                                    lambda r: r["overlap_s"] > 0) for p, e in combos])
        title = ("T' acknowledged (proposed fix)" if acked
                 else "T' from the last heartbeat heard (the document's rule)")
        parts.append(f"**{title}**\n\n"
                     + table(["T - T', s"] + [f"{p:g} s, eps {e:g}" for p, e in combos],
                             body))
    return ("Runs with any overlap, P-A, adversarial clocks (A behind by eps/2, B ahead "
            "by eps/2). Columns: heartbeat and sync period, eps.\n\n" + "\n\n".join(parts))


def _clock_section(rows: list[Row]) -> str:
    body = []
    for variant in ("bounded", "A beyond bound"):
        sub = where(rows, variant=variant)
        for eps, err in sorted({(r["eps"], r["a_clock_error"]) for r in sub}):
            rs = where(sub, eps=eps, a_clock_error=err)
            body.append([variant, eps, err, len(rs), med(rs, "in_doubt"),
                         sum(r["misclassified"] for r in rs), med(rs, "decisions")])
    return table(["clocks", "eps, s", "A's extra error, s", "n", "in doubt (median)",
                  "misclassified (total)", "decisions (median)"], body)


def _settlement_section(rows: list[Row]) -> str:
    body = []
    for p in ("S1", "S3", "S4"):
        for mode in ("strict", "closing"):
            for lost in (False, True):
                rs = where(rows, policy=p, settlement=mode, a_device_lost=lost)
                body.append([p, mode, "lost" if lost else "kept", len(rs),
                             med(rs, "never_settled"), med(rs, "settle_median_s"),
                             med(rs, "settle_p95_s")])
    return ("A incapacitated in P-A. Medians.\n\n"
            + table(["Policy", "settlement rule", "A's device", "n", "never settled",
                     "settle median, s", "settle p95, s"], body))


FAULT_COLS = [
    ("overlap_s", "overlap, s"), ("headless_outage_s", "no command, s"),
    ("takeover_delay_s", "takeover, s"), ("residual", "residual"),
    ("residual_no_valid_grant", "of which no valid grant"),
    ("conflicting_orders", "conflicting orders"),
    ("reader_flips_to_residual", "crew flips"), ("never_settled", "never settled"),
]


def _faults_section(rows: list[Row]) -> str:
    body = []
    for name in FAULTS:
        rs = where(rows, fault=name)
        if rs:
            body.append([name, len(rs)] + [med(rs, k) for k, _ in FAULT_COLS])
    return table(["Fault", "n"] + [h for _, h in FAULT_COLS], body)


INVARIANTS = [
    ("converged", lambda r: r["converged"], "every device ends with the same records"),
    ("lost", lambda r: r["lost"] == 0, "no accepted decision missing at the core"),
    ("auth_regressions", lambda r: r["auth_regressions"] == 0,
     "no device ever revokes an authoritative verdict"),
    ("misclassified", lambda r: r["misclassified"] == 0,
     "final verdicts match truth (clocks within bound)"),
    ("tradeoff", lambda r: not r["tradeoff_violated"],
     "never (a), (b) and (c) together over the outage"),
]


def _search_section(rows: list[Row]) -> str:
    body = []
    for p in POLICIES:
        for mode in ("strict", "closing"):
            for acked, effect in ((False, "signature"), (True, "signature"),
                                  (False, "acceptance")):
                rs = where(rows, policy=p, settlement=mode, acked=acked, effect=effect)
                if not rs:
                    continue
                variant = "acked" if acked else "accept" if effect == "acceptance" else "-"
                body.append([p, mode, variant, len(rs),
                             frac(rs, lambda r: r["successor"] is not None),
                             frac(rs, lambda r: r["overlap_s"] > 0),
                             sum(r["residual"] for r in rs)]
                            + [frac(rs, lambda r, f=f: not f(r)) for _, f, _ in INVARIANTS])
    bad = [r for r in rows if not all(f(r) for _, f, _ in INVARIANTS)]
    legend = "\n".join(f"- `{n}`: {d}" for n, _, d in INVARIANTS)
    out = (table(["Policy", "settlement", "variant", "n", "with succession", "with overlap",
                  "residuals"] + [f"violates {n}" for n, _, _ in INVARIANTS], body)
           + "\n\nInvariants:\n\n" + legend)
    if bad:
        out += "\n\nViolating runs (reproduce with `search_config(policy, seed, mode)`):\n\n"
        out += "\n".join(f"- {r['policy']} seed {r['seed']} {r['settlement']}" for r in bad[:20])
    return out


INTRO = (
    "Generated by `python -m aas_testbed report` from the CSVs in this directory. "
    "Every number is a median over seeds unless the column says otherwise; `-` means "
    "the event never happened (for example, no takeover). Times are seconds after the "
    "partition begins. Defaults: L = 90 s, T = 300 s, T' = 240 s, outage 1200 s, "
    "operator and C react after 120 s of silence, a voice call takes 60 s, one "
    "decision per minute per commander, heartbeats and gossip every 2 s, eps = 0.2 s, "
    "settlement rule `closing`. FINDINGS.md (one directory up) interprets them."
)


def provenance() -> str:
    """The commit the results were generated from, and whether the tree matched it."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "aas_testbed"],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Code commit: unknown (not a git checkout)."
    state = "with uncommitted changes to aas_testbed/" if dirty else "clean"
    return f"Code commit: `{head}` ({state})."


def write_report(out: Path) -> str:
    data = {name: load(out, name) for name in QUESTIONS}
    sections = [
        "# AAS succession testbed: results",
        INTRO + " " + provenance(),
        "## 1. Claims of the paper and the model document, tested",
        _claims_section(data),
    ]
    blocks = [
        ("matrix", "2. Cost map: policy x partition case", _matrix_section),
        ("timeout", "3. S4: choosing T", _timeout_section),
        ("lease", "4. S1, S2, S3L: choosing L (A fit)", _lease_section),
        ("detect", "5. S1 against S2: operator reaction time (P-A, A fit, L = 90 s)",
         _detect_section),
        ("margin", "6. S4: the margin T - T'", _margin_section),
        ("clock", "7. Clock error and the in-doubt status (S3, A does not answer voice)",
         _clock_section),
        ("settlement", "8. Settlement", _settlement_section),
        ("faults", "9. Faults", _faults_section),
        ("search", "10. Randomized search: invariants under link flapping", _search_section),
    ]
    for name, title, fn in blocks:
        if data.get(name):
            sections += [f"## {title}", f"*{QUESTIONS[name]}*", fn(data[name])]
    text = "\n\n".join(sections) + "\n"
    path = out / "REPORT.md"
    path.write_text(text)
    return f"wrote {path}"
