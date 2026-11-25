"""Write LaTeX inputs for the paper from experiments/results/results.json.

Outputs (paper/generated/): seed_macros.tex, seed_table.tex, comparison_table.tex,
removal_figure.tex.
Every number in these files comes from a directed run; none is typed by hand.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROWS = [
    ("V0-RENEW-EXPIRY", "renewal, withdrawal, expiry at two verifiers"),
    ("V0-HANDOVER", "prepared handover; separation is tight ($\\gamma=1$)"),
    ("V0-SELECTIVE-DELIVERY", "delayed and selective delivery to two verifiers"),
    ("V0-REMOVAL", "hostile holder, withdrawal race, successor"),
    ("V0-ISOLATION", "isolated honest holder; old command delivered late"),
    ("V0-REPLAY-CLOCK", "replay, boundaries, equal-time order, forged evidence"),
    ("V0-SPLIT-RECOVERY", "split epoch-2 vote, stall, epoch-3 recovery"),
    ("ORIG-SPLIT-STALL", "draft rules: split vote stalls service"),
    ("ORIG-SPLIT-RECOVER-E3", "draft rules: same stall, epoch-3 recovery"),
    ("ORIG-DEPUTY-SAME-READING", "draft rules, $F>0$: two issuers at one reading"),
]


def _tt(s: str) -> str:
    return "\\texttt{" + s.replace("_", "\\_") + "}"


def _by_id(results: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in results}


def _m(r: dict, path: str):
    cur = r.get("metrics", {})
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


ROOT = Path(__file__).resolve().parent.parent


def _trace_events(r: dict) -> list[dict]:
    """The events of a stored trace (header first)."""
    path = ROOT / r["trace"]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _removal_timeline(r: dict) -> dict[str, int]:
    """Instants of the hostile-holder scenario, read from its trace."""
    evs = _trace_events(r)
    head = evs[0]
    marks = {e["mark"]: e["t"] for e in evs if e["ev"] == "note" and "mark" in e}
    valid = {e["msg_id"] for e in evs if e["ev"] == "store" and e.get("valid")}
    certs = [e for e in evs if e["ev"] == "cert" and e["msg_id"] in valid]
    old_ends = [
        c["msg"]["end"]
        for c in certs
        if c["msg"]["type"] == "renewal" and c["msg"]["epoch"] == 1
    ]
    starts = [c["msg"]["start"] for c in certs if c["msg"]["type"] == "grant"]
    p = head["params"]
    return {
        "RemovalCompromise": next(e["t"] for e in evs if e["ev"] == "compromise"),
        "RemovalDetection": marks["detection"],
        "RemovalDecision": marks["decision"],
        "RemovalFirstWithdraw": min(e["t"] for e in evs if e["ev"] == "withdraw"),
        "RemovalLastValidEnd": max(old_ends),
        "RemovalSuccessorStart": min(starts),
        "RemovalBound": _m(r, "t_w.e1") + p["H"] + 2 * p["eps"],
        "RemovalBoundAfterTW": p["H"] + 2 * p["eps"],
        "RemovalSuccessorFirst": min(
            v for k, v in _m(r, "first_accept").items() if not k.startswith("e1:")
        ),
        "SeedN": p["n"],
        "SeedF": p["f"],
        "SeedQ": p["q"],
        "SeedH": p["H"],
        "SeedG": p["g"],
        "SeedEps": p["eps"],
        "SeedGamma": p["g"] - 2 * p["eps"],
    }


def _isolation_schedule(r: dict) -> dict[str, int]:
    """Renewal cadence (Delta), collection time (delta) and the guaranteed window of the
    isolation scenario, derived from its trace: a request made at holder-local time c
    asks for the end c + H - 2 eps, so its real start is end - H + 2 eps - offset."""
    evs = _trace_events(r)
    head = evs[0]
    p, off = head["params"], head["clocks"]
    holder = head["genesis"]["msg"]["holder"]
    t0 = next(
        e["t"] for e in evs if e["ev"] == "note" and e.get("mark") == "outage-start"
    )
    officers = set(head["officers"])

    def quorate(e: dict) -> bool:  # q distinct configured signers (as in the checker)
        by = {x["by"] for x in e["signatures"] if x["kind"] == "genuine"}
        return len(by & officers) >= p["q"]

    reqs = sorted(
        (e["msg"]["end"] - p["H"] + 2 * p["eps"] - off[holder], e["t"])
        for e in evs
        if e["ev"] == "cert" and e["msg"]["type"] == "renewal" and quorate(e)
    )
    gaps = {b[0] - a[0] for a, b in zip(reqs, reqs[1:], strict=False)}
    collect = {done - start for start, done in reqs}
    if len(gaps) != 1 or len(collect) != 1:
        raise ValueError("isolation scenario: renewal cadence is not uniform")
    big_delta, small_delta = gaps.pop(), collect.pop()
    return {
        "IsolationOutage": t0,
        "IsolationDelta": big_delta,
        "IsolationCollect": small_delta,
        "IsolationWindowEnd": t0 + p["H"] - big_delta - small_delta - 4 * p["eps"],
        "IsolationWindowLength": p["H"] - big_delta - small_delta - 4 * p["eps"],
        "IsolationFreshSpan": _m(r, "latest_created_accepted.e1:A") - t0,
    }


def _removal_figure(r: dict) -> str:
    """TikZ timeline of the hostile-holder scenario; every coordinate is from its trace."""
    evs = _trace_events(r)
    p = evs[0]["params"]
    marks = {e["mark"]: e["t"] for e in evs if e["ev"] == "note" and "mark" in e}
    t_c = next(e["t"] for e in evs if e["ev"] == "compromise")
    t_w = _m(r, "t_w.e1")
    bound = t_w + p["H"] + 2 * p["eps"]
    rows = {"e1": 0.95, "e2": 0.45}
    shape = {"V1": "circle (1.7pt)", "V2": "+(-1.6pt,-1.6pt) rectangle +(1.6pt,1.6pt)"}
    end = 10 * (max(a[0] for a in _m(r, "accepts")) // 10 + 2)
    lines = [
        "% Generated by experiments/report.py from the trace of V0-REMOVAL.",
        "% Do not edit by hand.",
        "\\begin{tikzpicture}[x=0.040cm,y=1cm,font=\\scriptsize,>=Stealth]",
        f"  \\draw[->,ink] (0,0) -- ({end},0) node[anchor=north east,yshift=-9pt] {{real time}};",
        "  \\foreach \\x in {0,50,...," + str(end - 10) + "} "
        "{\\draw[ink] (\\x,0.04) -- (\\x,-0.04) node[below] {\\x};}",
        f"  \\node[left] at (0,{rows['e1']}) {{$A$, epoch 1}};",
        f"  \\node[left] at (0,{rows['e2']}) {{$C$, epoch 2}};",
    ]
    for t, label, y in (
        (t_c, "compromise", 1.55),
        (marks["decision"], "decision", 1.3),
    ):
        lines.append(
            f"  \\draw[dashed,ink!60] ({t},0) -- ({t},{y - 0.05}) "
            f"node[above,inner sep=1pt] {{{label}}};"
        )
    lines.append(
        f"  \\draw[warn,thick] ({t_w},0) -- ({t_w},1.25);"
        f" \\node[warn,anchor=south east,inner sep=1pt] at ({t_w},1.0) {{$t_W$}};"
    )
    lines.append(
        f"  \\draw[decorate,decoration={{brace,amplitude=3pt}},warn] "
        f"({t_w},1.22) -- ({bound},1.22) "
        f"node[midway,above=2pt,inner sep=1pt] {{$H + 2\\varepsilon$}};"
    )
    lines.append(f"  \\draw[warn,thick] ({bound},0) -- ({bound},1.25);")
    for t, at, key, _local, _created in _m(r, "accepts"):
        y = (rows["e1"] if key.startswith("e1:") else rows["e2"]) + (
            0.09 if at == "V1" else -0.09
        )
        color = "accept" if key.startswith("e1:") else "fence"
        lines.append(f"  \\fill[{color}] ({t},{y}) {shape[at]};")
    lines.append("\\end{tikzpicture}")
    return "\n".join(lines) + "\n"


def write_tex(results: list[dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    R = _by_id(results)
    kinds = {}
    for r in results:
        kinds.setdefault(r["kind"], []).append(r)
    neg = kinds.get("negative", [])
    ctl = kinds.get("control", [])
    digest = hashlib.sha256(
        json.dumps([(r["id"], r.get("trace_sha256")) for r in results]).encode()
    ).hexdigest()

    def gap(a: str, b: str, key_a: str, key_b: str):
        x, y = R.get(a), R.get(b)
        if not x or not y:
            return None
        return _m(y, f"first_accept.{key_b}") - _m(x, f"last_accept.{key_a}")

    rem = R["V0-REMOVAL"]
    iso = R["V0-ISOLATION"]
    macros = {
        "SeedScenarioCount": len(results),
        "SeedPassCount": sum(r["status"] == "pass" for r in results),
        "SeedPositiveCount": len(kinds.get("positive", [])),
        "SeedWitnessCount": len(kinds.get("witness", [])),
        "SeedNegativeCount": len(neg),
        "SeedNegativeDetected": sum(r["status"] == "pass" for r in neg),
        "SeedControlClean": sum(r["status"] == "pass" and not r["codes"] for r in ctl),
        "SeedComparisonCount": len(kinds.get("comparison", [])),
        "SeedAcceptCount": sum(_m(r, "accepted") or 0 for r in results),
        "SeedResultsDigest": digest[:12],
        "RemovalTW": _m(rem, "t_w.e1"),
        "RemovalLastHostile": _m(rem, "last_hostile_accept"),
        "RemovalAfterTW": _m(rem, "last_hostile_accept") - _m(rem, "t_w.e1"),
        "IsolationLastFresh": _m(iso, "latest_created_accepted.e1:A"),
        "HandoverGap": gap("V0-HANDOVER", "V0-HANDOVER", "e1:A", "e2:B"),
        **_removal_timeline(rem),
        **_isolation_schedule(iso),
    }
    lines = [
        "% Generated by experiments/report.py from experiments/results/results.json.",
        "% Do not edit by hand.",
    ]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    (out / "seed_macros.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rows = []
    for sid, what in ROWS:
        r = R[sid]
        codes = (
            ", ".join(c.replace("-TWO-ISSUERS", "") for c in r.get("codes", []))
            or "none"
        )
        ok = "yes" if r["status"] == "pass" else "\\textbf{NO}"
        rows.append(f"{_tt(sid)} & {what} & {_m(r, 'accepted')} & {codes} & {ok} \\\\")
    rows.append("\\midrule")
    rows.append(
        f"6 \\texttt{{NC-*}} & broken rule variants (one guard removed each) & "
        f"--- & expected code & {macros['SeedNegativeDetected']}/{len(neg)} \\\\"
    )
    rows.append(
        f"6 \\texttt{{*-CONTROL}} & the same events with the \\texttt{{seed-v0}} rules "
        f"& --- & none & {macros['SeedControlClean']}/{len(ctl)} \\\\"
    )
    table = [
        "% Generated by experiments/report.py. Do not edit by hand.",
        "\\begin{tabular}{@{}l>{\\raggedright\\arraybackslash}p{0.33\\linewidth}rll@{}}",
        "\\toprule",
        "Scenario & What it exercises & Acc. & Violations found & Met \\\\",
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
    ]
    (out / "seed_table.tex").write_text("\n".join(table) + "\n", encoding="utf-8")

    def cell_handover(pid: str, key_a="A", key_b="B"):
        r = R.get(f"CMP-HANDOVER-{pid}")
        if r is None:
            return "not run"
        if "SEPARATION" in r.get("codes", []):
            return "overlap"
        return f"gap {_m(r, f'first_accept.{key_b}') - _m(r, f'last_accept.{key_a}')}"

    def cell_removal(pid: str, key: str):
        r = R.get(f"CMP-REMOVAL-{pid}")
        if r is None:
            return "not run"
        p = _trace_events(r)[0]["params"]
        # The candidate bound: H + 2 eps for credentials, W + 2 eps for orders.
        bound = (p["W"] if p.get("W") else p["H"]) + 2 * p["eps"]
        return f"{_m(r, 'last_hostile_accept') - _m(r, f't_w.{key}')} ($\\le {bound}$)"

    def cell_isolation(pid: str, key: str):
        r = R.get(f"CMP-ISOLATION-{pid}")
        if r is None:
            return "not run"
        outage = next(
            e["t"]
            for e in _trace_events(r)
            if e["ev"] == "note" and e.get("mark") == "outage-start"
        )
        last = _m(r, f"latest_created_accepted.{key}")
        if last is None or last < outage:
            return "none"
        return f"{last - outage}"

    # The stall window is the one the seed-v0 split scenario expects to be empty.
    (lo, hi) = R["CMP-SPLIT-SAME-HOLDER-SEED-V0"]["expect"]["no_accept_between"][0]

    def cell_split(pid: str):
        out_ = []
        for name in ("SAME-HOLDER", "TWO-HOLDERS"):
            r = R.get(f"CMP-SPLIT-{name}-{pid}")
            if r is None:
                out_.append("---")
                continue
            times = [a[0] for a in _m(r, "accepts")]
            out_.append("continues" if any(lo <= t <= hi for t in times) else "stalls")
        return " / ".join(out_)

    crow = [
        (
            "\\texttt{seed-v0}",
            cell_handover("SEED-V0", "e1:A", "e2:B"),
            cell_removal("SEED-V0", "e1"),
            cell_isolation("SEED-V0", "e1:A"),
            cell_split("SEED-V0"),
        ),
        (
            "\\texttt{xl}",
            cell_handover("XL"),
            cell_removal("XL", "A"),
            cell_isolation("XL", "A"),
            cell_split("XL"),
        ),
        (
            "\\texttt{tc}, no wait",
            cell_handover("TC-NAIVE"),
            cell_removal("TC", "A"),
            cell_isolation("TC", "A"),
            "not run",
        ),
        (
            "\\texttt{tc}, wait",
            cell_handover("TC-WAIT"),
            "as above",
            "as above",
            "not run",
        ),
        (
            f"\\texttt{{qo-w}}, $W={_trace_events(R['CMP-REMOVAL-QO-W'])[0]['params']['W']}$",
            "not run",
            cell_removal("QO-W", "A"),
            cell_isolation("QO-W", "A"),
            "not run",
        ),
    ]
    ctable = [
        "% Generated by experiments/report.py. Do not edit by hand.",
        "\\begin{tabular}{@{}lllll@{}}",
        "\\toprule",
        "Mechanism & Handover & After $t_W$ & Isolated & Split: same / two \\\\",
        "\\midrule",
        *[" & ".join(r) + " \\\\" for r in crow],
        "\\bottomrule",
        "\\end{tabular}",
    ]
    (out / "removal_figure.tex").write_text(_removal_figure(rem), encoding="utf-8")
    (out / "comparison_table.tex").write_text(
        "\n".join(ctable) + "\n", encoding="utf-8"
    )
