"""LaTeX macros and table rows for the paper, generated from results/.

Every number the paper quotes from the testbed comes from here, so that each one traces
to a CSV, a filter and a statistic (written to TESTBED_TRACE.md alongside). Tables are
written as rows only; the paper's section files hold the table environment and header.
"""

from __future__ import annotations

import statistics
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .report import Row, load, where

SEC = r"\,s"


@dataclass(frozen=True)
class Macro:
    name: str
    experiment: str
    select: dict
    stat: str  # "median", "max", "min", "count", "n", or "median_min"/"median_max"
    column: str = ""
    pred: Callable[[Row], bool] | None = None  # for "count" and "frac", and a filter
    unit: str = ""
    note: str = ""
    only: Callable[[Row], bool] | None = field(default=None)
    group_by: str = ""  # for median_min/median_max: the range of per-group medians

    def rows(self, data: dict[str, list[Row]]) -> list[Row]:
        rs = where(data[self.experiment], **self.select)
        return [r for r in rs if self.only(r)] if self.only else rs

    def value(self, data: dict[str, list[Row]]) -> str:
        rs = self.rows(data)
        if not rs:
            raise ValueError(f"{self.name}: no rows for {self.select}")
        if self.stat == "n":
            return str(len(rs))
        if self.stat == "count":
            return str(sum(1 for r in rs if self.pred(r)))
        if self.stat in ("median_min", "median_max"):
            groups: dict[object, list] = {}
            for r in rs:
                if r.get(self.column) is not None:
                    groups.setdefault(r[self.group_by], []).append(r[self.column])
            meds = [statistics.median(v) for v in groups.values()]
            x = min(meds) if self.stat == "median_min" else max(meds)
            return _fmt(x) + self.unit
        xs = [r[self.column] for r in rs if r.get(self.column) is not None]
        if not xs:
            return "--"
        x = {"median": statistics.median, "max": max, "min": min}[self.stat](xs)
        return _fmt(x) + self.unit


def _fmt(x: float) -> str:
    """Integers above 10 (half up), two significant digits below."""
    if abs(x) >= 10 or float(x).is_integer():
        n = int(abs(x) + 0.5) * (1 if x >= 0 else -1)
        return f"{n:,}".replace(",", "{,}")
    return f"{x:.2g}"


def _fault(name: str) -> dict:
    return {"fault": name}


PA_FIT = {"case": "P-A", "a_state": "alive"}
RELAY = "S4: stale heartbeat via relay"
RELAY_ACK = "S4: stale heartbeat via relay, acknowledged T'"
SIGNED = "S3: P-B, A fit, no voice; takeover effective when signed"
ACCEPTED = "S3: P-B, A fit, no voice; takeover effective when accepted"


def _s4_flapping(r: Row) -> bool:
    return r["timeout"] - r["primary_timeout"] >= 5 and r["handover_to_s_after"] is None


MACROS = [
    # Scale of the runs.
    Macro("tbSeedsPerCell", "matrix", {"policy": "S0", "case": "none", "a_state": "alive"},
          "n", note="seeds per cell of the policy matrix"),
    Macro("tbSearchRuns", "search", {}, "n", note="random-flapping incidents"),
    # Stale heartbeat through a relay (S4), and the acknowledged fix.
    Macro("tbRelayOverlap", "faults", _fault(RELAY), "median", "overlap_s", unit=SEC),
    Macro("tbRelayResidual", "faults", _fault(RELAY), "median", "residual"),
    Macro("tbRelayOverlapAcked", "faults", _fault(RELAY_ACK), "median", "overlap_s",
          unit=SEC),
    Macro("tbFlapOverlapRuns", "search", {"policy": "S4", "acked": False}, "count",
          pred=lambda r: r["overlap_s"] > 0, only=_s4_flapping,
          note="S4 runs with overlap, T - T' >= 5 s, no handover"),
    Macro("tbFlapRuns", "search", {"policy": "S4", "acked": False}, "n", only=_s4_flapping),
    Macro("tbFlapOverlapRunsAcked", "search", {"policy": "S4", "acked": True}, "count",
          pred=lambda r: r["overlap_s"] > 0, only=_s4_flapping),
    Macro("tbFlapRunsAcked", "search", {"policy": "S4", "acked": True}, "n",
          only=_s4_flapping),
    # Settlement.
    Macro("tbStrictLostNeverMin", "settlement", {"settlement": "strict",
          "a_device_lost": True}, "median_min", "never_settled", group_by="policy",
          note="smallest per-policy median"),
    Macro("tbStrictLostNeverMax", "settlement", {"settlement": "strict",
          "a_device_lost": True}, "median_max", "never_settled", group_by="policy",
          note="largest per-policy median"),
    Macro("tbClosingSettlePninetyfive", "settlement", {"settlement": "closing",
          "a_device_lost": True, "policy": "S3"}, "median", "settle_p95_s", unit=SEC),
    Macro("tbSFourSettlePninetyfiveKept", "settlement", {"settlement": "closing",
          "a_device_lost": False, "policy": "S4"}, "median", "settle_p95_s", unit=SEC),
    Macro("tbSFourNeverSettledLost", "settlement", {"settlement": "closing",
          "a_device_lost": True, "policy": "S4"}, "median", "never_settled"),
    # Takeovers that cannot reach the scene.
    Macro("tbSignedResidual", "faults", _fault(SIGNED), "median", "residual"),
    Macro("tbSignedFlips", "faults", _fault(SIGNED), "median", "reader_flips_to_residual"),
    Macro("tbAcceptedResidual", "faults", _fault(ACCEPTED), "median", "residual_in_outage"),
    Macro("tbAcceptedFlips", "faults", _fault(ACCEPTED), "median",
          "reader_flips_to_residual"),
    Macro("tbAcceptedOverlap", "faults", _fault(ACCEPTED), "median", "overlap_s", unit=SEC),
    # Leases renewed at the core, with only the backhaul lost (P-B, A fit).
    Macro("tbPBNoCommand", "matrix", {"policy": "S1", "case": "P-B", "a_state": "alive"},
          "median", "headless_outage_s", unit=SEC),
    Macro("tbPBRefused", "matrix", {"policy": "S1", "case": "P-B", "a_state": "alive"},
          "median", "refused_legit"),
    Macro("tbSThreeLNoCommand", "matrix", {"policy": "S3L", "case": "P-A",
          "a_state": "alive"}, "median", "headless_outage_s", unit=SEC),
    Macro("tbSThreeLOverlapLong", "lease", {"policy": "S3L", "L": 300,
          "case": "P-A", "a_state": "alive, no voice"}, "median", "overlap_s", unit=SEC),
    # S1 against S2: operator reaction time.
    Macro("tbSOneOverlapFast", "detect", {"policy": "S1", "detect": 15,
          "a_state": "alive"}, "median", "overlap_s", unit=SEC),
    # S4 and S5 with A fit, cut off.
    Macro("tbSFourAWindow", "matrix", {"policy": "S4"} | PA_FIT, "median", "a_window_s",
          unit=SEC),
    Macro("tbSFourTakeover", "matrix", {"policy": "S4"} | PA_FIT, "median",
          "takeover_delay_s", unit=SEC),
    Macro("tbSFourGap", "matrix", {"policy": "S4"} | PA_FIT, "median",
          "headless_outage_s", unit=SEC),
    Macro("tbSFiveOverlap", "matrix", {"policy": "S5"} | PA_FIT, "median", "overlap_s",
          unit=SEC),
    Macro("tbSFiveResidual", "matrix", {"policy": "S5"} | PA_FIT, "median", "residual"),
    Macro("tbSThreeSilentOverlap", "matrix", {"policy": "S3", "case": "P-A",
          "a_state": "alive, no voice"}, "median", "overlap_s", unit=SEC),
    Macro("tbSThreeSilentResidual", "matrix", {"policy": "S3", "case": "P-A",
          "a_state": "alive, no voice"}, "median", "residual"),
    # A connected but unfit commander.
    Macro("tbUnfitSOne", "matrix", {"policy": "S1", "case": "none",
          "a_state": "incapacitated"}, "median", "takeover_delay_s", unit=SEC),
    Macro("tbUnfitSThree", "matrix", {"policy": "S3", "case": "none",
          "a_state": "incapacitated"}, "median", "takeover_delay_s", unit=SEC),
    Macro("tbUnfitSFourPerson", "faults",
          _fault("S4: A unfit, device connected (person presence)"), "median",
          "takeover_delay_s", unit=SEC),
    Macro("tbUnfitSFourNoCommand", "faults",
          _fault("S4: A unfit, device connected (device presence)"), "median",
          "headless_outage_s", unit=SEC),
    # One-way links and a handover inside a partition.
    Macro("tbMuteOverlap", "faults", _fault("S4: A mute (receives, cannot send)"),
          "median", "overlap_s", unit=SEC),
    Macro("tbDeafNoCommand", "faults", _fault("S4: A deaf (sends, cannot receive)"),
          "median", "headless_outage_s", unit=SEC),
    Macro("tbHandoverResidual", "faults",
          _fault("S4: P-C, A hands over to S inside the partition"), "median", "residual"),
    Macro("tbHandoverOverlap", "faults",
          _fault("S4: P-C, A hands over to S inside the partition"), "median", "overlap_s",
          unit=SEC),
    # Clocks.
    Macro("tbDoubtTen", "clock", {"variant": "bounded", "eps": 10.0}, "median", "in_doubt"),
    Macro("tbDoubtSixty", "clock", {"variant": "bounded", "eps": 60.0}, "median",
          "in_doubt"),
    # Choosing T.
    Macro("tbBlindSixty", "timeout", {"T": 60, "outage": 2400, "a_state": "alive"},
          "median", "successor_blind"),
    Macro("tbBlindThreeHundred", "timeout", {"T": 300, "outage": 2400, "a_state": "alive"},
          "median", "successor_blind"),
    Macro("tbBlindTwelveHundred", "timeout", {"T": 1200, "outage": 2400,
          "a_state": "alive"}, "median", "successor_blind"),
]


# -- tables ---------------------------------------------------------------------------

def _cell(rows: list[Row], column: str) -> str:
    xs = [r[column] for r in rows if r.get(column) is not None]
    if not xs:
        return "--"
    return _fmt(statistics.median(xs))


def _policy_costs(data: dict[str, list[Row]]) -> str:
    m = data["matrix"]
    lines = []
    for p in ("S0", "S1", "S2", "S3", "S3L", "S4", "S5"):
        fit = where(m, policy=p, case="P-A", a_state="alive")
        silent = where(m, policy=p, case="P-A", a_state="alive, no voice")
        pb = where(m, policy=p, case="P-B", a_state="alive")
        unfit = where(m, policy=p, case="P-A", a_state="incapacitated")
        unfit_conn = where(m, policy=p, case="none", a_state="incapacitated")
        cells = [
            _cell(fit, "a_window_s"), _cell(fit, "takeover_delay_s"),
            _cell(fit, "overlap_s"), _cell(silent, "overlap_s"), _cell(silent, "residual"),
            _cell(pb, "headless_outage_s"), _cell(unfit, "takeover_delay_s"),
            _cell(unfit_conn, "takeover_delay_s"),
        ]
        name = p.replace("S3L", "S3+L")
        lines.append(f"{name} & " + " & ".join(cells) + r" \\")
    return "\n".join(lines) + "\n"


FAULT_ROWS = [
    ("S4: stale heartbeat via relay", "S4, stale heartbeat relayed to A"),
    ("S4: stale heartbeat via relay, acknowledged T'", "\\quad same, acknowledged $T'$"),
    ("S3: P-B, A fit, no voice; takeover effective when signed",
     "S3, P-B, takeover effective when signed"),
    ("S3: P-B, A fit, no voice; takeover effective when accepted",
     "\\quad same, effective when accepted"),
    ("S4: A deaf (sends, cannot receive)", "S4, A's device cannot receive"),
    ("S4: A mute (receives, cannot send)", "S4, A's device cannot send"),
    ("S4: P-C, A hands over to S inside the partition", "S4, P-C, A hands over to S"),
    ("S4: A unfit, device connected (device presence)", "S4, A unfit, device connected"),
    ("S4: A unfit, device connected (person presence)",
     "\\quad same, presence of the person"),
    ("S4: A's device ignores T'", "S4, A's device ignores $T'$"),
]


def _faults(data: dict[str, list[Row]]) -> str:
    lines = []
    for key, label in FAULT_ROWS:
        rs = where(data["faults"], fault=key)
        cells = [_cell(rs, c) for c in ("overlap_s", "headless_outage_s", "residual",
                                        "reader_flips_to_residual")]
        lines.append(f"{label} & " + " & ".join(cells) + r" \\")
    return "\n".join(lines) + "\n"


def _commit(path: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short=12", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_latex(results: Path, out: Path) -> list[Path]:
    data = {name: load(results, name) for name in
            ("matrix", "timeout", "lease", "detect", "margin", "clock", "faults",
             "settlement", "search")}
    out.mkdir(parents=True, exist_ok=True)
    report_head = (results / "REPORT.md").read_text().split("Code commit: ")[-1].split(
        "`")[1][:12] if (results / "REPORT.md").exists() else "unknown"
    header = (f"% Generated by `python -m aas_testbed latex` (rescue-ois testbed, exporter "
              f"commit {_commit(results)}),\n% from results generated by commit "
              f"{report_head}. Do not edit; re-run the exporter.\n")

    macros = [header]
    intro = (f"Generated by `python -m aas_testbed latex` from `testbed/results/` "
             f"(results from commit `{report_head}`). Each macro is a statistic over the "
             "rows of one CSV that match the filter.")
    trace = ["# Testbed numbers in the paper", "", intro, "",
             "| Macro | Value | CSV | Filter | Statistic | Runs |", "|---|---|---|---|---|---|"]
    for m in MACROS:
        v = m.value(data)
        macros.append(f"\\newcommand{{\\{m.name}}}{{{v}}}")
        stat = m.stat + (f" of `{m.column}`" if m.column else "")
        if m.group_by:
            stat += f" over `{m.group_by}`"
        filt = ", ".join(f"{k}={v!r}" for k, v in m.select.items()) or "all"
        if m.only is not None or m.note:
            filt += f" ({m.note or 'extra filter in latex.py'})"
        trace.append(f"| `\\{m.name}` | {v} | `{m.experiment}.csv` | {filt} | {stat} | "
                     f"{len(m.rows(data))} |")
    files = {
        "testbed_macros.tex": "\n".join(macros) + "\n",
        "tab_policy_costs.tex": header + _policy_costs(data),
        "tab_faults.tex": header + _faults(data),
        "TESTBED_TRACE.md": "\n".join(trace) + "\n",
    }
    written = []
    for name, text in files.items():
        path = out / name
        path.write_text(text)
        written.append(path)
    return written
