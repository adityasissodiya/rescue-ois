"""Canonical encoding, Ed25519 mode with fixture keys, distinct signers, durable state."""

from __future__ import annotations

import dataclasses

import pytest

from mandate.auth import Certificate, Ed25519Auth, SymbolicAuth, fixture_private_key
from mandate.kernel import SEED_V0, MandateProtocol, Params, check_grant
from mandate.messages import Grant, Renewal
from mandate.store import FileStore

OFFICERS = ["A", "B", "C", "D"]
P = Params(n=4, f=1, H=100, g=3, eps=1)


def test_canonical_encoding_is_stable_and_domain_separated():
    r = Renewal(scope="feeder-7", epoch=1, end=98)
    assert r.canonical_bytes() == (
        b"mandate-seed/v0\x00renewal\x00feeder-7\x00"
        b'{"end":98,"epoch":1,"scope":"feeder-7"}'
    )
    g = Grant(scope="feeder-7", epoch=1, holder="A", start=98)
    assert g.canonical_bytes() != r.canonical_bytes()
    assert (
        dataclasses.replace(r, scope="feeder-8").canonical_bytes()
        != r.canonical_bytes()
    )


def test_encoding_rejects_non_integer_fields():
    with pytest.raises(TypeError):
        Renewal(scope="s", epoch=1, end=98.5).canonical_bytes()
    with pytest.raises(TypeError):
        Renewal(scope="s", epoch=True, end=98).canonical_bytes()


@pytest.mark.parametrize("auth_cls", [SymbolicAuth, Ed25519Auth])
def test_signatures_bind_signer_type_and_scope(auth_cls):
    auth = auth_cls(OFFICERS)
    r = Renewal(scope="s", epoch=1, end=98)
    sig = auth.sign("A", r)
    assert auth.verify("A", r, sig)
    assert not auth.verify("B", r, sig)
    assert not auth.verify("A", dataclasses.replace(r, scope="t"), sig)
    assert not auth.verify("A", dataclasses.replace(r, end=99), sig)
    assert not auth.verify("E", r, sig)


def test_ed25519_signatures_are_real_and_keys_are_fixtures():
    auth = Ed25519Auth(OFFICERS)
    r = Renewal(scope="s", epoch=1, end=98)
    sig = auth.sign("A", r)
    assert len(sig) == 64
    pub = fixture_private_key("A").public_key()
    pub.verify(sig, r.canonical_bytes())  # raises if invalid
    assert (
        fixture_private_key("A").private_bytes_raw()
        == fixture_private_key("A").private_bytes_raw()
    )


@pytest.mark.parametrize("auth_cls", [SymbolicAuth, Ed25519Auth])
def test_validity_counts_distinct_configured_signers(auth_cls):
    auth = auth_cls(OFFICERS)
    r = Renewal(scope="s", epoch=1, end=98)
    d = auth.sign("D", r)
    assert not Certificate(r, (("D", d),) * 3).is_valid(auth, 3)
    good = tuple((u, auth.sign(u, r)) for u in "ABC")
    assert Certificate(r, good).is_valid(auth, 3)
    other = dataclasses.replace(r, scope="other")
    mixed = (("A", auth.sign("A", r)), ("B", auth.sign("B", other)), ("D", d))
    assert not Certificate(r, mixed).is_valid(auth, 3)


def test_file_store_survives_reopen_and_restart_refuses_double_vote(tmp_path):
    genesis = Grant(scope="s", epoch=1, holder="A", start=0)
    proto = MandateProtocol(SEED_V0, P, genesis)
    st = proto.new_signer({"consents": ["B", "C"], "max_end": 98})
    store = FileStore(tmp_path / "A.json", proto.durable(st))
    g_b = Grant(scope="s", epoch=2, holder="B", start=101)
    assert proto.check_sign(st, g_b, 50) is None
    proto.apply_sign(st, g_b)
    store.commit(proto.durable(st))  # durable before the signature is released
    reopened = FileStore(tmp_path / "A.json")
    restarted = proto.restore_signer(reopened.load())
    assert restarted.epoch == 2
    g_c = Grant(scope="s", epoch=2, holder="C", start=101)
    assert check_grant(SEED_V0, P, restarted, g_c, 52) == "epoch-not-higher"
    assert not (tmp_path / "A.json.tmp").exists()
