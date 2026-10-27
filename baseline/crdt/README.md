# CRDT-LWW Baseline

Minimal Hanssen-style operation-based LWW Element Set baseline for the prototype's
evaluation (the CRDT comparison in the WONS draft, branch `paper`). How to run it:
[`docs/prototype.md`](../../docs/prototype.md#re-run-the-crdt-lww-baseline).

The service models elements by immutable UUID and accepts ADD/UPD and DEL operations with
system-clock timestamps. Replicas converge by exchanging operation logs; last timestamp wins,
with `replica_id` and `op_id` used only as deterministic tie breakers.
