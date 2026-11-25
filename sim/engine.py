"""Deterministic execution of a directed scenario.

A scenario lists events with an explicit real time ``t`` in non-decreasing order. Events
with equal ``t`` run in list order; the trace records that order as ``step`` (scenario
event index) and ``seq`` (trace record index). Nothing is random.

The adversary is the scenario author: the scenario decides which signatures are
requested, which certificates are assembled from the signatures that exist, and what
is delivered to whom and when. The engine applies the rules of the selected protocol to
every honest signer and verifier and records the outcome. A compromised officer's key
signs anything the scenario asks it to sign.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass

from mandate.auth import Certificate, make_auth
from mandate.kernel import RULESETS, MandateProtocol, Params
from mandate.messages import Command, Grant, Lease, Order, Renewal
from mandate.store import FileStore, MemoryStore

from .baselines import make_baseline

MESSAGE_TYPES = {"grant": Grant, "renewal": Renewal, "lease": Lease, "order": Order}


class ScenarioError(Exception):
    """The scenario itself is malformed. Never a protocol outcome."""


def build_message(scope: str, spec: dict):
    spec = dict(spec)
    cls = MESSAGE_TYPES[spec.pop("type")]
    return cls(scope=scope, **spec)


def build_protocol(sc: dict, p: Params):
    if sc["rules"] in RULESETS:
        g = sc["genesis"]
        genesis = Grant(
            scope=sc["scope"],
            epoch=1,
            holder=g["holder"],
            start=g["start"],
            deputy=g.get("deputy"),
        )
        return MandateProtocol(RULESETS[sc["rules"]], p, genesis)
    return make_baseline(sc["rules"], p, sc["params"].get("W"))


def canonical(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def trace_digest(trace: list[dict]) -> str:
    h = hashlib.sha256()
    for rec in trace:
        h.update(canonical(rec).encode() + b"\n")
    return h.hexdigest()


@dataclass
class Agent:
    state: object
    store: MemoryStore
    up: bool = True
    dirty: bool = False  # state changed but not durable (broken variant only)


class Engine:
    def __init__(self, sc: dict, auth_mode: str = "symbolic", store_dir=None):
        """store_dir: if given, each signing agent keeps its durable state in a real file
        (mandate.store.FileStore: write, fsync, rename, fsync directory)."""
        self.sc = sc
        prm = sc["params"]
        self.p = Params(
            n=prm["n"],
            f=prm["f"],
            H=prm["H"],
            g=prm["g"],
            eps=prm["eps"],
            F=prm.get("F", 0),
        )
        self.proto = build_protocol(sc, self.p)
        self.officers = list(sc["officers"])
        if len(set(self.officers)) != self.p.n:
            raise ScenarioError("the officer list must have n distinct names")
        self.verifier_names = list(sc["verifiers"])
        self.offsets = dict(sc["clocks"])
        for party in self.officers + self.verifier_names:
            if party not in self.offsets:
                raise ScenarioError(f"no clock offset for {party}")
        if any(abs(o) > self.p.eps for o in self.offsets.values()):
            raise ScenarioError("a clock offset exceeds eps")
        self.compromised = set(sc.get("byzantine", []))
        if len(self.compromised) > self.p.f:
            raise ScenarioError("more Byzantine officers than f")
        self.auth = make_auth(auth_mode, self.officers)
        self.agents: dict[str, Agent] = {}
        for u in self.officers:
            if u not in self.compromised:
                st = self.proto.new_signer(sc.get("signer_init", {}).get(u, {}))
                initial = self.proto.durable(st)
                store = (
                    MemoryStore(initial)
                    if store_dir is None
                    else FileStore(f"{store_dir}/{sc['id']}-{u}.json", initial)
                )
                self.agents[u] = Agent(st, store)
        self.vstate = {v: self.proto.new_verifier() for v in self.verifier_names}
        self.messages = {
            k: build_message(sc["scope"], s) for k, s in sc.get("messages", {}).items()
        }
        self.pool: dict[tuple[str, str], bytes] = {}
        self.certs: dict[str, Certificate] = {}
        self.commands: dict[str, tuple] = {}
        self.trace: list[dict] = []
        self.now = 0
        self.step = -1

    # ------------------------------------------------------------------ helpers
    def clock(self, party: str, t: int) -> int:
        return t + self.offsets[party]

    def emit(self, ev: str, **kw) -> None:
        self.trace.append(
            {"seq": len(self.trace), "step": self.step, "t": self.now, "ev": ev, **kw}
        )

    def header(self) -> dict:
        prm = self.sc["params"]
        genesis = getattr(self.proto, "genesis", None)
        return {
            "ev": "header",
            "scenario": self.sc["id"],
            "kind": self.sc["kind"],
            "rules": self.sc["rules"],
            "family": self.proto.family,
            "params": {
                "n": self.p.n,
                "f": self.p.f,
                "q": self.p.q,
                "H": self.p.H,
                "g": self.p.g,
                "eps": self.p.eps,
                "F": self.p.F,
                "W": prm.get("W"),
            },
            "officers": self.officers,
            "byzantine": sorted(self.sc.get("byzantine", [])),
            "verifiers": self.verifier_names,
            "clocks": self.offsets,
            "scope": self.sc["scope"],
            "genesis": None
            if genesis is None
            else {"msg_id": genesis.msg_id(), "msg": genesis.describe()},
        }

    def _agent(self, u: str) -> Agent:
        if u not in self.agents:
            raise ScenarioError(f"{u} has no honest signing agent")
        return self.agents[u]

    def _flush(self, a: Agent) -> None:
        if a.dirty:
            a.store.commit(self.proto.durable(a.state))
            a.dirty = False

    def _valid(self, cert: Certificate, at_verifier: bool) -> bool:
        if at_verifier and not self.proto.distinct_signers:  # broken variant
            ok = sum(
                1
                for s, sig in cert.sigs
                if s in self.auth.officers and self.auth.verify(s, cert.msg, sig)
            )
            return ok >= self.p.q
        return cert.is_valid(self.auth, self.p.q)

    # ------------------------------------------------------------------ operations
    def op_sign(self, e: dict) -> None:
        m = self.messages[e["msg"]]
        u, mid = e["by"], m.msg_id()
        local = self.clock(u, self.now)
        if u in self.compromised:
            self.pool[(mid, u)] = self.auth.sign(u, m)
            self.emit(
                "sign", by=u, msg_id=mid, msg=m.describe(), local=local, adversary=True
            )
            return
        a = self._agent(u)
        if not a.up:
            self.emit(
                "refuse", by=u, msg_id=mid, msg=m.describe(), local=local, reason="down"
            )
            return
        self._flush(a)
        reason = self.proto.check_sign(a.state, m, local)
        if reason:
            self.emit(
                "refuse", by=u, msg_id=mid, msg=m.describe(), local=local, reason=reason
            )
            return
        notes = self.proto.apply_sign(a.state, m)
        if self.proto.commit_before_release:
            a.store.commit(
                self.proto.durable(a.state)
            )  # durable before the signature leaves
        else:
            a.dirty = True
        self.pool[(mid, u)] = self.auth.sign(u, m)
        self.emit(
            "sign", by=u, msg_id=mid, msg=m.describe(), local=local, adversary=False
        )
        for note in notes:
            note = dict(note)
            self.emit(note.pop("ev"), by=u, **note)

    def op_assemble(self, e: dict) -> None:
        m = self.messages[e["msg"]]
        mid = m.msg_id()
        sigs, listed = [], []
        for u in e["sigs"]:
            if (mid, u) in self.pool:
                sigs.append((u, self.pool[(mid, u)]))
                listed.append({"by": u, "kind": "genuine"})
            elif not e.get("allow_missing"):
                raise ScenarioError(f"{u} has not signed {e['msg']}")
        for u, times in sorted(e.get("dup", {}).items()):
            if (mid, u) not in self.pool:
                raise ScenarioError(f"cannot duplicate a signature {u} never made")
            for _ in range(times):
                sigs.append((u, self.pool[(mid, u)]))
                listed.append({"by": u, "kind": "duplicate"})
        for u in e.get("cross_scope", []):
            other = dataclasses.replace(m, scope=m.scope + "/other")
            sigs.append((u, self.auth.sign(u, other)))
            listed.append({"by": u, "kind": "cross-scope"})
        self.certs[e["cert"]] = Certificate(m, tuple(sigs))
        self.emit(
            "cert", cert=e["cert"], msg_id=mid, msg=m.describe(), signatures=listed
        )

    def _deliver(self, to: str, label: str) -> None:
        cert = self.certs[label]
        mid = cert.msg.msg_id()
        if to in self.vstate:
            ok = self._valid(cert, at_verifier=True)
            if ok:
                self.proto.store(self.vstate[to], cert.msg)
            self.emit("store", at=to, cert=label, msg_id=mid, valid=ok)
            return
        if to in self.compromised:
            self.emit(
                "store", at=to, cert=label, msg_id=mid, valid=None, note="adversary"
            )
            return
        a = self._agent(to)
        if not a.up:
            self.emit("store", at=to, cert=label, msg_id=mid, valid=None, note="down")
            return
        ok = self._valid(cert, at_verifier=False)
        self.emit("store", at=to, cert=label, msg_id=mid, valid=ok)
        if ok:
            self._flush(a)
            notes = self.proto.learn(a.state, cert.msg)
            if notes:
                a.store.commit(self.proto.durable(a.state))
            for note in notes:
                note = dict(note)
                self.emit(note.pop("ev"), by=to, **note)

    def op_deliver(self, e: dict) -> None:
        for label in e["certs"]:
            self._deliver(e["to"], label)

    def _present(self, v: str, cmd: Command, sig: bytes, created: int) -> None:
        tau = self.clock(v, self.now)
        desc = {
            "epoch": cmd.epoch,
            "holder": cmd.holder,
            "cid": cmd.cid,
            "payload": cmd.payload,
            "created": created,
        }
        if not self.auth.verify(cmd.holder, cmd, sig):
            self.emit("reject", at=v, local=tau, cmd=desc, reason="bad-signature")
            return
        reason, rule, evidence = self.proto.check_command(self.vstate[v], cmd, tau, ())
        if reason:
            self.emit("reject", at=v, local=tau, cmd=desc, reason=reason)
            return
        self.proto.commit(
            self.vstate[v], cmd, rule, evidence
        )  # durable log, then actuator
        self.emit(
            "accept",
            at=v,
            local=tau,
            cmd=desc,
            rule=rule,
            evidence=[{"msg_id": x.msg_id(), "msg": x.describe()} for x in evidence],
        )

    def op_command(self, e: dict) -> None:
        by, v = e["by"], e["to"]
        label = e.get("label", e["cid"])
        created = e.get("created", self.now)
        if label in self.commands:
            raise ScenarioError(f"command label {label} reused; use op 'replay'")
        if created > self.now:
            raise ScenarioError("a command cannot be delivered before it is created")
        cmd = Command(
            scope=self.sc["scope"],
            epoch=e.get("epoch"),
            holder=by,
            cid=e["cid"],
            payload=e.get("payload", "op"),
        )
        sig = self.auth.sign(
            by, cmd
        )  # the holder signs alone; holders follow no signer rule
        if e.get("forge_holder_sig"):
            sig = self.auth.sign(
                by, dataclasses.replace(cmd, scope=cmd.scope + "/other")
            )
        self.commands[label] = (cmd, sig, created)
        for cert in e.get("attach", []):
            self._deliver(v, cert)
        self._present(v, cmd, sig, created)

    def op_replay(self, e: dict) -> None:
        cmd, sig, created = self.commands[e["command"]]
        self.emit("redeliver", at=e["to"], cid=cmd.cid)
        self._present(e["to"], cmd, sig, created)

    def op_withdraw(self, e: dict) -> None:
        a = self._agent(e["by"])
        if e["by"] in self.compromised:
            raise ScenarioError("a compromised officer's withdrawal has no meaning")
        self._flush(a)
        target = {k: e[k] for k in ("epoch", "holder") if k in e}
        info = self.proto.withdraw(a.state, target)
        a.store.commit(self.proto.durable(a.state))
        self.emit("withdraw", by=e["by"], **info)

    def op_consent(self, e: dict) -> None:
        a = self._agent(e["by"])
        self._flush(a)
        self.proto.set_consent(a.state, e["holder"], e["value"])
        a.store.commit(self.proto.durable(a.state))
        self.emit("consent", by=e["by"], holder=e["holder"], value=e["value"])

    def op_compromise(self, e: dict) -> None:
        who = e["who"]
        if who in self.compromised:
            raise ScenarioError(f"{who} is already compromised")
        self.compromised.add(who)
        if len(self.compromised) > self.p.f:
            raise ScenarioError("the run exceeds the fault budget f")
        self.emit("compromise", who=who)

    def op_crash(self, e: dict) -> None:
        a = self._agent(e["who"])
        a.up, a.state, a.dirty = False, None, False  # volatile state is lost
        self.emit("crash", who=e["who"])

    def op_restart(self, e: dict) -> None:
        a = self._agent(e["who"])
        durable = a.store.load()
        a.state, a.up = self.proto.restore_signer(durable), True
        self.emit("restart", who=e["who"], durable=durable)

    def op_note(self, e: dict) -> None:
        self.emit("note", text=e["text"], mark=e.get("mark"))

    # ------------------------------------------------------------------ run
    def run(self) -> list[dict]:
        self.trace = [self.header()]
        last = None
        for i, e in enumerate(self.sc["events"]):
            if last is not None and e["t"] < last:
                raise ScenarioError(f"event {i} is earlier than event {i - 1}")
            self.now, self.step, last = e["t"], i, e["t"]
            handler = getattr(self, "op_" + e["op"], None)
            if handler is None:
                raise ScenarioError(f"unknown operation {e['op']}")
            handler(e)
        return self.trace


def run_scenario(sc: dict, auth_mode: str = "symbolic", store_dir=None) -> list[dict]:
    return Engine(sc, auth_mode, store_dir).run()
