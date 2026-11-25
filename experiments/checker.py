"""Independent acceptance-trace checker.

This module deliberately imports nothing from ``src/mandate`` or ``sim/``. It reads a
trace (a header record and event records) and checks properties stated in terms of
verifier acceptance events and real time (spec/protocol.md, s. 10):

  PARAMS                    q = ceil((n + f + 1) / 2) and g > 2 eps
  CLOCK                     every local reading equals real time plus the party's offset,
                            and every offset is within eps
  INVALID-EVIDENCE          an acceptance cites a certificate that the verifier did not
                            receive with q distinct signers who signed that exact message
                            before delivery, or whose window or holder does not match
  REPLAY                    one verifier accepts the same (epoch, holder, cid) twice
  GRANT-UNIQUENESS          two different grants of one epoch each have q distinct signers
  SEPARATION                acceptances of different issuers less than gamma = g - 2 eps
                            apart in real time (at any verifiers). This is pairwise: an
                            overlap of two holders' authority is visible only if the trace
                            has acceptances of both within gamma. EPOCH-ORDER is stronger.
  EPOCH-ORDER               an acceptance of epoch j > k less than gamma after one of k
  SAME-READING-TWO-ISSUERS  one verifier accepts two issuers at one clock reading
  WITHDRAWAL-EXPIRY         an acceptance of epoch k (holder h) later than
                            t_W + H + 2 eps (orders: t_W + W + 2 eps), where t_W is the
                            instant n - q + 1 never-compromised signers have withdrawn
                            from (or advanced past) k

What it cannot check: cryptographic validity of signatures (it trusts the trace's record
of who signed which message id; tests/test_crypto.py covers signatures), and anything the
trace does not record.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def load_trace(path: str | Path) -> tuple[dict, list[dict]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    recs = [json.loads(x) for x in lines if x.strip()]
    if not recs or recs[0].get("ev") != "header":
        raise ValueError(f"{path}: first record is not a header")
    return recs[0], recs[1:]


def _key(family: str, cmd: dict) -> str:
    return f"e{cmd['epoch']}:{cmd['holder']}" if family == "mandate" else cmd["holder"]


def check(header: dict, events: list[dict]) -> dict:
    P = header["params"]
    n, f, q, H, g, eps = P["n"], P["f"], P["q"], P["H"], P["g"], P["eps"]
    F, W = P.get("F") or 0, P.get("W")
    family = header["family"]
    officers = set(header["officers"])
    offsets = header["clocks"]
    gamma = g - 2 * eps
    violations: list[dict] = []

    def bad(code: str, **detail) -> None:
        violations.append({"code": code, **detail})

    if q != math.ceil((n + f + 1) / 2) or n < 3 * f + 1 or g <= 2 * eps:
        bad("PARAMS", n=n, f=f, q=q, g=g, eps=eps)

    events = sorted(events, key=lambda e: e["seq"])
    for a, b in zip(events, events[1:], strict=False):
        if b["t"] < a["t"]:
            bad("TRACE-ORDER", seq=b["seq"])

    # ---------------------------------------------------------------- who signed what
    compromised_at: dict[str, float] = {u: -math.inf for u in header["byzantine"]}
    signed: dict[str, dict[str, int]] = defaultdict(dict)  # msg_id -> signer -> seq
    msgs: dict[str, dict] = {}
    certs: dict[str, dict] = {}
    for e in events:
        if e["ev"] == "compromise":
            compromised_at.setdefault(e["who"], e["t"])
        elif e["ev"] == "sign":
            if e["by"] in officers:
                signed[e["msg_id"]].setdefault(e["by"], e["seq"])
            msgs[e["msg_id"]] = e["msg"]
        elif e["ev"] == "cert":
            certs[e["cert"]] = e
            msgs[e["msg_id"]] = e["msg"]
    never_compromised = officers - set(compromised_at)

    def quorum_before(msg_id: str, signers: list[str], seq: int) -> bool:
        ok = {
            s
            for s in signers
            if s in officers and signed[msg_id].get(s, math.inf) < seq
        }
        return len(ok) >= q

    genesis_id = header["genesis"]["msg_id"] if header.get("genesis") else None
    if header.get("genesis"):
        msgs[genesis_id] = header["genesis"]["msg"]

    # verifier deliveries: (verifier, msg_id) -> list of (seq, cert label)
    delivered: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for e in events:
        if e["ev"] == "store" and e.get("valid") and e["at"] in header["verifiers"]:
            delivered[(e["at"], e["msg_id"])].append((e["seq"], e["cert"]))

    # ---------------------------------------------------------------- acceptances
    accepts = [e for e in events if e["ev"] == "accept"]
    for e in accepts:
        off = offsets.get(e["at"])
        if off is None or abs(off) > eps or e["local"] != e["t"] + off:
            bad("CLOCK", seq=e["seq"], at=e["at"])
    for e in events:
        if e["ev"] in ("sign", "refuse", "reject") and "local" in e:
            party = e.get("at") or e.get("by")
            off = offsets.get(party)
            if off is None or abs(off) > eps or e["local"] != e["t"] + off:
                bad("CLOCK", seq=e["seq"], party=party)

    for e in accepts:
        cmd, tau = e["cmd"], e["local"]
        ev = {x["msg"]["type"]: x for x in e["evidence"]}
        for x in e["evidence"]:
            mid = x["msg_id"]
            if mid == genesis_id:
                continue
            ok = any(
                quorum_before(mid, [s["by"] for s in certs[label]["signatures"]], dseq)
                for dseq, label in delivered.get((e["at"], mid), [])
                if dseq < e["seq"]
            )
            if not ok:
                bad(
                    "INVALID-EVIDENCE",
                    seq=e["seq"],
                    why="no quorum-signed delivery",
                    msg_id=mid,
                )
        why = None
        if family == "mandate":
            gr, rn = ev.get("grant"), ev.get("renewal")
            if gr is None or rn is None:
                why = "missing grant or renewal"
            else:
                gm, rm = gr["msg"], rn["msg"]
                if not (gm["epoch"] == rm["epoch"] == cmd["epoch"]):
                    why = "epoch mismatch"
                elif e["rule"] == "D1":
                    if gm["holder"] != cmd["holder"]:
                        why = "issuer is not the holder"
                    elif not (gm["start"] <= tau <= rm["end"]):
                        why = "outside [start, end]"
                elif e["rule"] == "D2":
                    if gm.get("deputy") != cmd["holder"]:
                        why = "issuer is not the deputy"
                    elif not (gm["start"] <= tau and rm["end"] < tau <= rm["end"] + F):
                        why = "outside the fallback interval"
                else:
                    why = f"unknown rule {e['rule']}"
        elif family == "lease":
            ls = ev.get("lease")
            if ls is None or ls["msg"]["holder"] != cmd["holder"]:
                why = "no lease for the issuer"
            elif not (ls["msg"]["start"] <= tau <= ls["msg"]["end"]):
                why = "outside [start, end]"
        elif family == "order":
            od = ev.get("order")
            if od is None or any(
                od["msg"][k] != cmd[k] for k in ("holder", "cid", "payload")
            ):
                why = "no matching order"
            elif not (od["msg"]["start"] <= tau <= od["msg"]["end"]):
                why = "outside [start, end]"
        if why:
            bad("INVALID-EVIDENCE", seq=e["seq"], why=why)

    seen = Counter(
        (e["at"], e["cmd"]["epoch"], e["cmd"]["holder"], e["cmd"]["cid"])
        for e in accepts
    )
    for k, c in seen.items():
        if c > 1:
            bad("REPLAY", at=k[0], cid=k[3], count=c)

    # ---------------------------------------------------------------- grant uniqueness
    valid_grants: dict[int, set[str]] = defaultdict(set)
    valid_renewals: set[str] = set()
    for mid, by in signed.items():
        m = msgs.get(mid, {})
        if m.get("type") == "grant":
            valid_grants[m["epoch"]]  # report epochs whose proposals never reached q
        if len(by) >= q:
            if m.get("type") == "grant":
                valid_grants[m["epoch"]].add(mid)
            elif m.get("type") in ("renewal", "lease", "order"):
                valid_renewals.add(mid)
    if family == "mandate":
        for k, ids in valid_grants.items():
            if len(ids) > 1:
                bad("GRANT-UNIQUENESS", epoch=k, grants=sorted(ids))

    # ---------------------------------------------------------------- separation
    for i, a in enumerate(accepts):
        for b in accepts[i + 1 :]:
            if (
                a["cmd"]["holder"] != b["cmd"]["holder"]
                and abs(b["t"] - a["t"]) < gamma
            ):
                bad(
                    "SEPARATION",
                    first=a["seq"],
                    second=b["seq"],
                    gap=abs(b["t"] - a["t"]),
                )
            if (
                a["at"] == b["at"]
                and a["local"] == b["local"]
                and a["cmd"]["holder"] != b["cmd"]["holder"]
            ):
                bad(
                    "SAME-READING-TWO-ISSUERS",
                    at=a["at"],
                    local=a["local"],
                    seqs=[a["seq"], b["seq"]],
                )
            if family == "mandate" and a["cmd"]["epoch"] != b["cmd"]["epoch"]:
                lo, hi = (a, b) if a["cmd"]["epoch"] < b["cmd"]["epoch"] else (b, a)
                if hi["t"] - lo["t"] < gamma:
                    bad(
                        "EPOCH-ORDER",
                        lower=lo["seq"],
                        higher=hi["seq"],
                        gap=hi["t"] - lo["t"],
                    )

    # ---------------------------------------------------------------- withdrawal-to-expiry
    threshold = n - q + 1
    t_w: dict[str, int] = {}
    if family == "mandate":
        out: dict[int, dict[str, int]] = defaultdict(dict)  # epoch -> signer -> time
        epochs = {e["cmd"]["epoch"] for e in accepts}
        for e in events:
            if e["ev"] == "withdraw" and e["by"] in never_compromised:
                out[e["epoch"]].setdefault(e["by"], e["t"])
            elif e["ev"] == "advance" and e["by"] in never_compromised:
                for k in epochs:
                    if k < e["to"]:
                        out[k].setdefault(e["by"], e["t"])
        for k, times in out.items():
            if len(times) >= threshold:
                t_w[f"e{k}"] = sorted(times.values())[threshold - 1]
        for e in accepts:
            tw = t_w.get(f"e{e['cmd']['epoch']}")
            if tw is None:
                continue
            limit = tw + H + 2 * eps + (F if e["rule"] == "D2" else 0)
            if e["t"] > limit:
                bad("WITHDRAWAL-EXPIRY", seq=e["seq"], t=e["t"], limit=limit)
    else:
        horizon = W if family == "order" else H
        state: dict[str, dict[str, bool]] = defaultdict(
            dict
        )  # holder -> signer -> withdrawn
        reached: dict[str, int] = {}
        ended: dict[str, int] = {}
        for e in events:
            h, val = None, None
            if e["ev"] == "withdraw" and e["by"] in never_compromised:
                h, val = e["holder"], True
            elif e["ev"] == "consent" and e["by"] in never_compromised:
                h, val = e["holder"], not e["value"]
            if h is None:
                continue
            state[h][e["by"]] = val
            count = sum(state[h].values())
            if count >= threshold and h not in reached:
                reached[h] = e["t"]
            elif count < threshold and h in reached and h not in ended:
                ended[h] = e["t"]  # consent restored: the property window ends here
        t_w.update(reached)
        for e in accepts:
            h = e["cmd"]["holder"]
            if h in reached and e["t"] > reached[h] + horizon + 2 * eps:
                if h not in ended or e["t"] <= ended[h]:
                    bad(
                        "WITHDRAWAL-EXPIRY",
                        seq=e["seq"],
                        t=e["t"],
                        limit=reached[h] + horizon + 2 * eps,
                    )

    # ---------------------------------------------------------------- metrics
    ordered = sorted(accepts, key=lambda e: (e["t"], e["seq"]))
    keys = [_key(family, e["cmd"]) for e in ordered]
    successions = sum(1 for x, y in zip(keys, keys[1:], strict=False) if x != y)
    first, last, latest_created = {}, {}, {}
    for e, k in zip(ordered, keys, strict=True):
        first.setdefault(k, e["t"])
        last[k] = e["t"]
        latest_created[k] = max(latest_created.get(k, -math.inf), e["cmd"]["created"])
    boundary = 0
    for e in accepts:
        for x in e["evidence"]:
            m = x["msg"]
            if e["local"] in (m.get("start"), m.get("end")):
                boundary += 1
                break
    hostile = [
        e
        for e in accepts
        if e["cmd"]["holder"] in compromised_at
        and e["cmd"]["created"] >= compromised_at[e["cmd"]["holder"]]
    ]
    metrics = {
        "accepted": len(accepts),
        "accepted_by_key": dict(Counter(keys)),
        "rejected_by_reason": dict(
            Counter(e["reason"] for e in events if e["ev"] == "reject")
        ),
        "refusals": dict(
            Counter(f"{e['by']}:{e['reason']}" for e in events if e["ev"] == "refuse")
        ),
        "successions": successions,
        "boundary_accepts": boundary,
        "valid_renewals": len(valid_renewals),
        "valid_grants_by_epoch": {
            str(k): len(v) for k, v in sorted(valid_grants.items())
        },
        "withdrawals": sum(
            1
            for e in events
            if e["ev"] == "withdraw" or (e["ev"] == "consent" and not e["value"])
        ),
        "first_accept": first,
        "last_accept": last,
        "latest_created_accepted": latest_created,
        "t_w": t_w,
        "hostile_accepts": len(hostile),
        "last_hostile_accept": max((e["t"] for e in hostile), default=None),
        "accepts": [
            [e["t"], e["at"], k, e["local"], e["cmd"]["created"]]
            for e, k in zip(ordered, keys, strict=True)
        ],
    }
    return {
        "violations": violations,
        "codes": sorted({v["code"] for v in violations}),
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Check acceptance traces (JSON lines).")
    ap.add_argument("traces", nargs="+")
    args = ap.parse_args(argv)
    worst = 0
    for path in args.traces:
        header, events = load_trace(path)
        res = check(header, events)
        print(
            f"{header['scenario']}: {res['metrics']['accepted']} accepted, "
            f"violations: {', '.join(res['codes']) or 'none'}"
        )
        worst = max(worst, 1 if res["codes"] else 0)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
