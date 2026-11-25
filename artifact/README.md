# Artifact: ending command authority at disconnected devices (working seed)

This is the anonymous review export of a **working research seed**. It is not a finished
system and not a submission. The specification, code and paper were drafted with an AI
assistant, and no person has reviewed the arguments. All times in the traces are
synthetic integers: nothing here measures a real system.

## Contents

| Path | What it is |
|---|---|
| `paper/main-anon.pdf` | The paper (review build), with its sources in `paper/` |
| `spec/protocol.md` | Normative rules of `seed-v0`, its properties and what it does not guarantee |
| `src/mandate/` | Rule kernel: signer rules O1 to O3, verifier rule D1, canonical encoding, symbolic and Ed25519 signatures (fixture keys for tests only), durable store |
| `sim/` | Deterministic scenario simulator, comparison mechanisms `tc`, `xl`, `qo-w` |
| `experiments/` | Directed scenarios, the independent trace checker, the runner, generated results (`results/`: traces, `results.json`, `manifest.json`) |
| `tests/` | Tests; `tests/README.md` lists the deliberately broken variants |
| `spec/tla/` | Bounded TLA+ model, configurations, run script and the logs of our run |
| `research/` | Positioning record, claim ledger (`claims.csv`) and roadmap with open questions |

## Reproduce

Requires Python 3.12 and, for the optional model check, Java and network access to
download the pinned TLA+ tools.

```bash
make venv          # hash-checked dependencies from requirements/seed.lock
make seed          # lint, tests, all directed scenarios; exits nonzero on any failure
make tla-tools     # optional: pinned tla2tools.jar (SHA-256 checked)
make tla           # optional: bounded model, 9 to 14 minutes in our runs; checks outcomes
make paper-anon    # optional: rebuild the PDF (TeX Live with IEEEtran)
```

`make seed` rewrites `experiments/results/` and `paper/generated/`. Traces are
deterministic: a rerun gives byte-identical traces, and their digests are in
`experiments/results/manifest.json`. In this export the manifest's Git commit is
withheld for anonymity. The results were produced from an uncommitted working tree, and
the manifest says so.

## Licence

Apache License 2.0 (`LICENSE`). Third-party papers are cited, not included.
