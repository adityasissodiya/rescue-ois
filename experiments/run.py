"""Run every directed scenario, check every trace independently, write results.

    PYTHONPATH=src:. python -m experiments.run [--out experiments/results] [--tex paper/generated]

For each scenario: run in symbolic mode, write the trace, check the written trace with
experiments/checker.py, evaluate the scenario's expectations, then run again with real
Ed25519 signatures (fixture keys) and require a byte-identical trace. Exit status is
non-zero if any scenario fails its expectations, raises, or differs between modes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from pathlib import Path

from experiments.checker import check, load_trace
from experiments.expect import evaluate
from experiments.scenarios import all_scenarios
from sim.engine import canonical, run_scenario, trace_digest

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    "spec/protocol.md",
    "src/mandate",
    "sim",
    "experiments",
    "requirements/seed.lock",
]

METRICS = {
    "accepted": "number of verifier acceptance events",
    "successions": "changes of authority key (epoch and holder, or holder) between "
    "consecutive acceptances in real-time order",
    "boundary_accepts": "acceptances whose local reading equals the start or end time of "
    "the evidence used",
    "t_w": "real time at which n - q + 1 never-compromised signers had withdrawn from (or "
    "advanced past) the epoch, or withdrawn consent from the holder",
    "last_hostile_accept": "latest real time of an acceptance of a command created by a "
    "holder after that holder was compromised",
    "latest_created_accepted": "latest creation time among accepted commands",
    "codes": "violation codes reported by experiments/checker.py",
}


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_digest() -> tuple[str, list[list[str]]]:
    files = []
    for rel in SOURCES:
        p = ROOT / rel
        paths = (
            [p]
            if p.is_file()
            else sorted(
                x
                for x in p.rglob("*")
                if x.is_file()
                and "__pycache__" not in x.parts
                and "results" not in x.parts
            )
        )
        for x in paths:
            files.append(
                [str(x.relative_to(ROOT)), hashlib.sha256(x.read_bytes()).hexdigest()]
            )
    h = hashlib.sha256("".join(f"{a} {b}\n" for a, b in files).encode()).hexdigest()
    return h, files


def run_all(out: Path) -> tuple[list[dict], bool]:
    traces = out / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    results, ok = [], True
    for sc in all_scenarios():
        rec = {
            "id": sc["id"],
            "kind": sc["kind"],
            "rules": sc["rules"],
            "title": sc["title"],
            "expect": sc["expect"],
            "config_sha256": hashlib.sha256(canonical(sc).encode()).hexdigest(),
        }
        try:
            trace = run_scenario(sc, "symbolic")
            path = traces / f"{sc['id']}.jsonl"
            path.write_text(
                "".join(canonical(r) + "\n" for r in trace), encoding="utf-8"
            )
            header, events = load_trace(path)
            res = check(header, events)
            fails = evaluate(sc["expect"], res)
            crypto = trace_digest(run_scenario(sc, "ed25519"))
            if crypto != trace_digest(trace):
                fails.append("ed25519 trace differs from the symbolic trace")
            rec.update(
                status="pass" if not fails else "fail",
                failures=fails,
                codes=res["codes"],
                violations=res["violations"],
                metrics=res["metrics"],
                trace=str(path.relative_to(ROOT))
                if path.is_relative_to(ROOT)
                else str(path),
                trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                ed25519_identical=crypto == trace_digest(trace),
            )
        except Exception as exc:  # an infrastructure error is never a pass
            rec.update(
                status="error",
                failures=[f"{type(exc).__name__}: {exc}"],
                traceback=traceback.format_exc(),
            )
        ok = ok and rec["status"] == "pass"
        results.append(rec)
    return results, ok


def manifest(results: list[dict]) -> dict:
    digest, files = source_digest()
    status = _git("status", "--porcelain=v1", "--untracked-files=all", "--", *SOURCES)
    try:
        import cryptography

        crypto_version = cryptography.__version__
    except ImportError:  # pragma: no cover
        crypto_version = None
    return {
        "what": "Directed runs of the Mandate seed and comparison mechanisms",
        "timing": "All times are synthetic integer units chosen for the scenarios; nothing "
        "was measured on a system.",
        "randomness": "none: every run is deterministic; no seeds are used",
        "git_head": _git("rev-parse", "HEAD"),
        "git_seed_sources_dirty": None if status is None else bool(status),
        "git_seed_sources_status": None if status is None else status.splitlines(),
        "source_tree_sha256": digest,
        "source_files": files,
        "python": platform.python_version(),
        "cryptography": crypto_version,
        "auth_modes": ["symbolic", "ed25519 (fixture keys; traces must be identical)"],
        "metric_definitions": METRICS,
        "scenarios": [
            {
                k: r.get(k)
                for k in (
                    "id",
                    "kind",
                    "rules",
                    "status",
                    "config_sha256",
                    "trace",
                    "trace_sha256",
                    "ed25519_identical",
                )
            }
            for r in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "results"))
    ap.add_argument("--tex", default=str(ROOT / "paper" / "generated"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    results, ok = run_all(out)
    (out / "results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "manifest.json").write_text(
        json.dumps(manifest(results), indent=1) + "\n", encoding="utf-8"
    )
    from experiments.report import write_tex

    write_tex(results, Path(args.tex))
    width = max(len(r["id"]) for r in results)
    for r in results:
        print(
            f"{r['id']:<{width}}  {r['kind']:<10} {r['status']:<5} "
            f"codes={','.join(r.get('codes', [])) or '-'}"
        )
        for f in r.get("failures", []):
            print(f"    ! {f}")
    n_pass = sum(r["status"] == "pass" for r in results)
    print(f"{n_pass}/{len(results)} scenarios meet their expectations")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
