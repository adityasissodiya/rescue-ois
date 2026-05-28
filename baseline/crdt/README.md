# CRDT-LWW Baseline

Minimal Hanssen-style operation-based LWW Element Set baseline for the NCA paper evaluation.

The service models elements by immutable UUID and accepts ADD/UPD and DEL operations with
system-clock timestamps. Replicas converge by exchanging operation logs; last timestamp wins,
with `replica_id` and `op_id` used only as deterministic tie breakers.
