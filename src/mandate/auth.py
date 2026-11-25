"""Authentication modes and certificate validity (spec/protocol.md, s. 5).

Two explicit modes:

* ``symbolic``: a signature is a tag that binds the signer to the message digest. It is
  NOT cryptography: unforgeability is modelled by construction (only the simulator's
  honest-signer path and the adversary's compromised-key path call ``sign``).
* ``ed25519``: real Ed25519 signatures (pyca/cryptography) over the canonical bytes.

Keys in ``ed25519`` mode come from ``fixture_private_key``: deterministic, PUBLIC keys
for tests and simulations only. They must never protect anything.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from .messages import Message


class SymbolicAuth:
    mode = "symbolic"

    def __init__(self, officers: Iterable[str]):
        self.officers = frozenset(officers)

    def sign(self, officer: str, msg: Message) -> bytes:
        if officer not in self.officers:
            raise KeyError(officer)
        return (
            b"sym:"
            + officer.encode()
            + b":"
            + hashlib.sha256(msg.canonical_bytes()).digest()
        )

    def verify(self, officer: str, msg: Message, sig: bytes) -> bool:
        return officer in self.officers and sig == self.sign(officer, msg)


def fixture_private_key(officer: str):
    """TEST/SIMULATION ONLY. A deterministic Ed25519 key derived from a public label."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    seed = hashlib.sha256(b"mandate-seed fixture key v0|" + officer.encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


class Ed25519Auth:
    mode = "ed25519"

    def __init__(self, officers: Iterable[str]):
        self.officers = frozenset(officers)
        self._private = {o: fixture_private_key(o) for o in sorted(self.officers)}
        self._public = {o: k.public_key() for o, k in self._private.items()}

    def sign(self, officer: str, msg: Message) -> bytes:
        return self._private[officer].sign(msg.canonical_bytes())

    def verify(self, officer: str, msg: Message, sig: bytes) -> bool:
        from cryptography.exceptions import InvalidSignature

        key = self._public.get(officer)
        if key is None:
            return False
        try:
            key.verify(sig, msg.canonical_bytes())
        except InvalidSignature:
            return False
        return True


def make_auth(mode: str, officers: Iterable[str]):
    if mode == "symbolic":
        return SymbolicAuth(officers)
    if mode == "ed25519":
        return Ed25519Auth(officers)
    raise ValueError(f"unknown auth mode {mode!r}")


@dataclass(frozen=True)
class Certificate:
    """A message with a list of (signer, signature) pairs as it travels on the wire.
    The list may contain duplicates, unknown signers and bad signatures."""

    msg: Message
    sigs: tuple[tuple[str, bytes], ...]

    def valid_signers(self, auth) -> frozenset[str]:
        """Distinct configured officers whose signature verifies. Each officer counts once."""
        return frozenset(
            s
            for s, sig in self.sigs
            if s in auth.officers and auth.verify(s, self.msg, sig)
        )

    def is_valid(self, auth, q: int) -> bool:
        return len(self.valid_signers(auth)) >= q
