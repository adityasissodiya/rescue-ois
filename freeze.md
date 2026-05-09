 freeze.md — Rescue OIS paper integration + 60s recovery investigation

    State of paper edits (DONE, committed-ready)

    All consensus update edits + reviewer-feedback edits applied. Paper compiles clean at 9 pages, no undefined refs.

    - paper/refs.bib: 13 new entries added (jahanian2022conice, sagor2024distressnetng, hanssen2025emergency, tran2021ndn, li2017vehicleassist, haroon2022edgecoord, aboualola2023edgesurvey, alwakeel2025edgefog, pothineni2024offlinefirst,
     sciullo2020locate, gomes2017verifyingsec, lewchenko2025boltonsc).
    - sections/01_introduction.tex: gap paragraph extended with Aboualola survey + CoNICE; "a recent systematic review" (singular).
    - sections/02_related_work.tex: §II.A CoNICE paragraph; obsolete "next phase of NCA submission work" sentence DELETED; §II.B Hanssen/Pothineni + Gomes/Lewchenko verification lineage rewrite; §II.C emergency-edge systems paragraph;
    tightened II.C closing redundancy; R1–R3 forward ref replaced with \ref{sec:requirements}.
    - sections/06_evaluation.tex: §VI.D bounds-justification sentence; §VI.D scope clarification on idempotency vs crash injection; §VI.E n-voter generalization sentence; §VI.E open-gap framing sentence (aboualola2023edgesurvey); Table
    III footnote ("by architecture, not measured").
    - sections/07_discussion.tex: limitations bullet for CoNICE/Hanssen future work.

    State of #1 — HTTP-client fix (UNRESOLVED, blocked)

    The 60s WAN-recovery cell still measures ~46–50s after multiple attempted fixes. The paper's framing that this is a simple HTTP-client artefact is wrong — the actual root cause is deeper and not yet identified.

    Code changes made to edge/syncd/src/{push,forward}.py

    - Removed long-lived httpx.AsyncClient reuse; create fresh httpx.AsyncClient per _forward_once/_push_once call.
    - Added asyncio.wait_for(..., timeout=17.0) (forward) / 12.0 (push) wrapping client.post, re-raising as httpx.ReadTimeout.
    - Tried httpx.Limits(max_keepalive_connections=0) (didn't help, since superseded by per-call client).
    - Added explicit httpx.Timeout(connect=5, read=10/15, write=5, pool=5).
    - Dockerfile: added ENV PYTHONUNBUFFERED=1 (was masking some logs).
    - Added trace logger.info calls at every step of _forward_once to find the hang.

    Smoke results across 5 attempts (RUNS_PER_CELL=2)

    ┌────────────────────────────┬────────────┬─────────────┬─────────────┐
    │          Attempt           │  1s cell   │  10s cell   │  60s cell   │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ baseline (paper)           │ ~728ms p50 │ ~3390ms p50 │ ~49.7s p95  │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ v1 (reset on RequestError) │ 818–2490   │ 3666–3746   │ 37771–44899 │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ v2 (+wait_for)             │ 724–2102   │ 3666–3712   │ 48355–49918 │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ v3 (+no keepalive)         │ 833–850    │ 3448–3878   │ 45935–47892 │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ v4 (+PYTHONUNBUFFERED)     │ 881–2775   │ 3476–3716   │ 49555–50063 │
    ├────────────────────────────┼────────────┼─────────────┼─────────────┤
    │ v5 (fresh client per call) │ 2153–2170  │ 3588–3650   │ 45920–48982 │
    └────────────────────────────┴────────────┴─────────────┴─────────────┘

    Diagnosis so far                                                                                                                                                                                                                       
                                                                                                                   
    cmd-syncd is only on rescue-ois-net (not on edge-cmd_default). When inject-partition.sh wan 60 does docker network disconnect rescue-ois-net edge-cmd-syncd-1, cmd-syncd loses access to BOTH:
    - core (sync-api.core) — expected                                                                                                                                                                                 
    - its own local Postgres (postgres.edge-cmd) — also on rescue-ois-net                                                                                                                         
                                                                                                                              
    After partition resolves at T=60s:                                                                                                                                                                                
    - Responder push to cmd-syncd recovers within ~1s (push DNS errors fire ~3/s during partition, success right at heal).                                                                        
    - cmd-syncd accept commits the 20 events to journal at T=60.5s.                                                           
    - cmd-syncd forward to core does NOT happen until T=109s — 49s gap with zero log lines from forward.py, even with PYTHONUNBUFFERED=1.
    - Core sync-api shows the request actually arrived at T=109s (so it's not the eval poller missing it).                                                                                        
                                                                                                                                         
    asyncio.wait_for(timeout=17.0) is silently NOT firing during this 49s window. No transport-error log lines fire either. Best guess: stale asyncpg pool connection to local Postgres (since postgres.edge-cmd was unreachable during
    partition) — pool.acquire() or conn.fetch() is hanging without raising, and asyncio cancellation isn't propagating through asyncpg's native socket reads.                                     
                                                                                                                                                                                                                                       
    Next steps to try when picking up                                                                                                                        
                                                                                                                                                                                                  
    1. Confirm hypothesis: tracing logger.info lines were just added to _forward_once (entering / got pool / acquired conn / last_acked / posting). Rebuild cmd-syncd, run scripts/_one_60s.py, look at docker logs edge-cmd-syncd-1 — find
    which trace line is the LAST one before the 49s gap. That tells us if it hangs on pool.acquire(), get_kv(), conn.fetch(), or client.post().              
    2. If asyncpg is the culprit: recreate the pool on transport errors, or set asyncpg.create_pool(command_timeout=10) so queries time out, or close stale connections via pool.expire_connections() periodically.                        
    3. Or — change the fault model: add cmd-syncd to edge-cmd_default in edge/docker-compose.yml so it can always reach its local postgres regardless of rescue-ois-net partitioning. This better matches the real deployment (a vehicle's
    syncd never loses its own DB just because the WAN drops).                                                                                                                                                      
    4. Or — accept and revise the paper: the artefact is NOT just the long-lived httpx.AsyncClient claimed in §VI.B. Update §VI.B to describe what's actually happening (probably asyncpg pool stale-connection issue OR docker-compose    
    network co-location bug), keep the monotonicity-in-partition-duration claim.                                                                                                                                                       
                                                                                                                                                                                                                                       
    Active scratch files / state                                                                                                                                                                                                           
                                                                                                                                                                                                                                       
    - scripts/_recovery_only.py — runs only scenario_recovery to a separate metrics file. Keep.                                                                                                                                        
    - scripts/_one_60s.py — single 60s iteration with trace logging. Keep.                                                                                                                                                                 
    - paper/data/eval_metrics_recovery_smoke.jsonl — last smoke output. Throw away after #1 resolves.                                                                                                                                  
    - paper/data/eval_metrics_one60s.jsonl — single-iter probe output. Throw away after #1 resolves.                                                                                                                                   
    - consensusUpdate.md (untracked at repo root) — original spec. Either delete or move to docs/archive/ after #1 resolves.                                                                                                               
                                                                                                                                                                                                                                       
    Stack state                                                                                                                                                                                                                        
                                                                                                                                                                                                                                           
    Dev stack is up: core, edge-cmd, edge-resp-1. Verified env vars: EDGE_ROLE=command on edge-cmd-syncd-1, EDGE_ROLE=responder on edge-resp-1-syncd-1. Recreate gotcha: docker compose -p edge-cmd up -d --force-recreate syncd without
    re-passing EDGE_ROLE=command defaults to responder (per compose-yml ${EDGE_ROLE:-responder}), which silently breaks accept with 409.                                                                                               
                                                                                                                                                                                                                                           
    Submission deadline                                                                                                                                                                                                                
                                                                                                                                                                                                                                       
    NCA 2026: 2026-06-19 AoE. ~6 weeks remaining. Paper edits alone are submission-ready; only #1 still open.  