 ## 1. Claim-to-script Traceability Matrix

  No Makefile/justfile exists in the repo inventory. README commands exist only for evaluate-pilot.py, evaluate-command-local-partition.py, Raft, formal TLA+, and table/plot
  generation (README.md:130-137, README.md:191-196).

  ┌─────────────────────────────────┬──────────────────┬───────────┬────────────┬───────────────────────────────────────────────────┬─────────┬─────────────────────────────────┐
  │ evaluation cell                 │ driving          │ endpoint  │ input      │ exact CLI command found in Makefile/justfile/     │ precise │ R/M map                         │
  │                                 │ script(s) (path) │ or DB     │ fixture(s) │ README                                            │ claim   │                                 │
  │                                 │                  │ path      │ -> output  │                                                   │         │                                 │
  │                                 │                  │ exercised │ JSONL      │                                                   │         │                                 │
  ├─────────────────────────────────┼──────────────────┼───────────┼────────────┼───────────────────────────────────────────────────┼─────────┼─────────────────────────────────┤
  │ V-A setup                       │ scripts/dev-     │ Docker    │ no         │ ./scripts/dev-up.sh; ./scripts/run-               │ single- │ R1/R2/R3 support; all M support │
  │                                 │ up.sh:24-47,     │ bridge    │ fixture;   │ migrations.sh; ./scripts/run-migrations.sh edge   │ host    │                                 │
  │                                 │ scripts/run-     │ rescue-   │ harness    │ (README.md:130-133)                               │ emulati │                                 │
  │                                 │ migrations.sh,   │ ois-net;  │ JSONL      │                                                   │ on      │                                 │
  │                                 │ scripts/inject-  │ Postgres  │ under      │                                                   │ source  │                                 │
  │                                 │ partition.sh:21- │ core/edge │ paper/     │                                                   │ of      │                                 │
  │                                 │ 66               │           │ data/      │                                                   │ measure │                                 │
  │                                 │                  │           │            │                                                   │ ments   │                                 │
  │ V-B phase A                     │ scripts/         │ POST /    │ synthetic  │ none found                                        │ current │ R3; M2/M4                       │
  │                                 │ evaluate-fenced- │ accept/   │ command_no │                                                   │ epoch   │                                 │
  │                                 │ promotion.py:run │ event-    │ te ->      │                                                   │ traffic │                                 │
  │                                 │ _one (221-266)   │ batch;    │ paper/     │                                                   │ commits │                                 │
  │                                 │                  │ incident. │ data/      │                                                   │         │                                 │
  │                                 │                  │ journal,  │ eval_fence │                                                   │         │                                 │
  │                                 │                  │ incident. │ d_promotio │                                                   │         │                                 │
  │                                 │                  │ state     │ n.jsonl A  │                                                   │         │                                 │
  │                                 │                  │           │ attempts   │                                                   │         │                                 │
  │                                 │                  │           │ (2-21,     │                                                   │         │                                 │
  │                                 │                  │           │ repeated   │                                                   │         │                                 │
  │                                 │                  │           │ to 265)    │                                                   │         │                                 │
  │ V-B phase B                     │ scripts/         │ same      │ stale      │ none found                                        │ stale   │ R3; M4                          │
  │                                 │ evaluate-fenced- │ endpoint  │ epoch      │                                                   │ epoch   │                                 │
  │                                 │ promotion.py:ins │ with      │ attempts   │                                                   │ rejecte │                                 │
  │                                 │ tall_new_epoch   │ stale X-  │ -> paper/  │                                                   │ d       │                                 │
  │                                 │ (110-134),       │ Command-  │ data/      │                                                   │ before  │                                 │
  │                                 │ run_one (267-    │ Epoch     │ eval_fence │                                                   │ journal │                                 │
  │                                 │ 273)             │           │ d_promotio │                                                   │ write   │                                 │
  │                                 │                  │           │ n.jsonl:22 │                                                   │         │                                 │
  │                                 │                  │           │ -41,       │                                                   │         │                                 │
  │                                 │                  │           │ repeated   │                                                   │         │                                 │
  │ V-B phase C                     │ scripts/         │ same      │ new epoch  │ none found                                        │ post-   │ R3; M2/M4                       │
  │                                 │ evaluate-fenced- │ endpoint  │ attempts   │                                                   │ promoti │                                 │
  │                                 │ promotion.py:run │ with new  │ -> paper/  │                                                   │ on      │                                 │
  │                                 │ _one (274-292)   │ epoch     │ data/      │                                                   │ epoch   │                                 │
  │                                 │                  │           │ eval_fence │                                                   │ remains │                                 │
  │                                 │                  │           │ d_promotio │                                                   │ writabl │                                 │
  │                                 │                  │           │ n.jsonl:42 │                                                   │ e, no   │                                 │
  │                                 │                  │           │ -61,       │                                                   │ duplica │                                 │
  │                                 │                  │           │ repeated;  │                                                   │ te seq  │                                 │
  │                                 │                  │           │ summaries  │                                                   │ across  │                                 │
  │                                 │                  │           │ 62, 306    │                                                   │ epochs  │                                 │
  │ V-B strict TLA+                 │ formal/tla/      │ TLC model │ cfg/log -> │ java -jar "$TLA_TOOLS_JAR" ...                    │ strict  │ R3; M4                          │
  │                                 │ RescueOIS_large. │ state     │ formal/    │ RescueOIS_strict.cfg RescueOIS.tla                │ promoti │                                 │
  │                                 │ cfg:4-8, formal/ │ space     │ tla/       │ (README.md:193)                                   │ on      │                                 │
  │                                 │ tla/RUNS.md:17   │           │ RUNS.md,   │                                                   │ preserv │                                 │
  │                                 │                  │           │ paper/     │                                                   │ es six  │                                 │
  │                                 │                  │           │ tables/    │                                                   │ safety  │                                 │
  │                                 │                  │           │ tab_falsif │                                                   │ invaria │                                 │
  │                                 │                  │           │ ication_co │                                                   │ nts     │                                 │
  │                                 │                  │           │ st.tex:2   │                                                   │         │                                 │
  │ V-B weak SingleAuthority        │ formal/tla/      │ TLC weak  │ cfg/log -> │ README weak command (README.md:194)               │ unfence │ R3; M4                          │
  │                                 │ RescueOIS_weak.c │ model     │ RUNS.md:27 │                                                   │ d       │                                 │
  │                                 │ fg:4-17          │           │ ,          │                                                   │ promoti │                                 │
  │                                 │                  │           │ weak_count │                                                   │ on      │                                 │
  │                                 │                  │           │ erexample. │                                                   │ admits  │                                 │
  │                                 │                  │           │ md:5-18    │                                                   │ split   │                                 │
  │                                 │                  │           │            │                                                   │ authori │                                 │
  │                                 │                  │           │            │                                                   │ ty      │                                 │
  │ V-B weak EpochAuthorityCoupling │ formal/tla/      │ TLC weak  │ cfg/log -> │ none found                                        │ weak    │ R3; M4                          │
  │                                 │ RescueOIS_weak_e │ model     │ RUNS.md:28 │                                                   │ promoti │                                 │
  │                                 │ poch.cfg:10-17   │           │ ,          │                                                   │ on      │                                 │
  │                                 │                  │           │ weak_count │                                                   │ leaves  │                                 │
  │                                 │                  │           │ erexample. │                                                   │ two     │                                 │
  │                                 │                  │           │ md:19-31   │                                                   │ authori │                                 │
  │                                 │                  │           │            │                                                   │ ties at │                                 │
  │                                 │                  │           │            │                                                   │ same    │                                 │
  │                                 │                  │           │            │                                                   │ epoch   │                                 │
  │ V-B weak NoForkedJournal        │ formal/tla/      │ TLC weak  │ cfg/log -> │ java ... RescueOIS_weak_journal.cfg ...           │ weak    │ R3; M2/M4                       │
  │                                 │ RescueOIS_weak_j │ model     │ RUNS.md:29 │ (README.md:195)                                   │ promoti │                                 │
  │                                 │ ournal.cfg:10-16 │           │ ,          │                                                   │ on can  │                                 │
  │                                 │                  │           │ weak_count │                                                   │ fork    │                                 │
  │                                 │                  │           │ erexample. │                                                   │ event_s │                                 │
  │                                 │                  │           │ md:33-47   │                                                   │ eq      │                                 │
  │ V-C responder isolation         │ scripts/         │ direct    │ synthetic  │ python3 scripts/evaluate-command-local-           │ command │ R1/R3; M1/M2                    │
  │                                 │ evaluate-        │ command   │ 20 command │ partition.py (README.md:135)                      │ commits │                                 │
  │                                 │ command-local-   │ POST /    │ notes ->   │                                                   │ while   │                                 │
  │                                 │ partition.py:run │ accept/   │ paper/     │                                                   │ respond │                                 │
  │                                 │ _experiment      │ event-    │ data/      │                                                   │ er      │                                 │
  │                                 │ (309-494)        │ batch;    │ eval_comma │                                                   │ syncd   │                                 │
  │                                 │                  │ incident. │ nd_local_p │                                                   │ isolate │                                 │
  │                                 │                  │ journal   │ artition.j │                                                   │ d       │                                 │
  │                                 │                  │           │ sonl:1-22  │                                                   │         │                                 │
  │ V-C throughput                  │ scripts/         │ actually  │ 1000       │ python3 scripts/evaluate-pilot.py (README.md:134) │ seriali │ R2/R3; M2/M3                    │
  │                                 │ evaluate-        │ responder │ synthetic  │                                                   │ zation- │                                 │
  │                                 │ pilot.py:scenari │ POST /    │ submission │                                                   │ point   │                                 │
  │                                 │ o_throughput     │ api/      │ s ->       │                                                   │ through │                                 │
  │                                 │ (228-283)        │ events,   │ paper/     │                                                   │ put,    │                                 │
  │                                 │                  │ then      │ data/      │                                                   │ not     │                                 │
  │                                 │                  │ command   │ eval_metri │                                                   │ protoco │                                 │
  │                                 │                  │ journal   │ cs.jsonl:3 │                                                   │ l limit │                                 │
  │                                 │                  │ polling   │ 01-330     │                                                   │         │                                 │
  │ V-D qd1                         │ scripts/         │ responder │ synthetic  │ python3 scripts/evaluate-pilot.py                 │ durable │ R2; M3/M2                       │
  │                                 │ evaluate-        │ /api/     │ qd1 ->     │                                                   │ outbox  │                                 │
  │                                 │ pilot.py:scenari │ events -> │ eval_metri │                                                   │ propaga │                                 │
  │                                 │ o_propagation    │ outbox.de │ cs.jsonl:1 │                                                   │ tion    │                                 │
  │                                 │ (125-171)        │ vice_outb │ 21-150     │                                                   │         │                                 │
  │                                 │                  │ ox ->     │            │                                                   │         │                                 │
  │                                 │                  │ command / │            │                                                   │         │                                 │
  │                                 │                  │ accept/   │            │                                                   │         │                                 │
  │                                 │                  │ event-    │            │                                                   │         │                                 │
  │                                 │                  │ batch ->  │            │                                                   │         │                                 │
  │                                 │                  │ incident. │            │                                                   │         │                                 │
  │                                 │                  │ journal   │            │                                                   │         │                                 │
  │ V-D qd10                        │ same             │ same      │ qd10 ->    │ same                                              │ same    │ R2; M3/M2                       │
  │                                 │                  │           │ eval_metri │                                                   │         │                                 │
  │                                 │                  │           │ cs.jsonl:1 │                                                   │         │                                 │
  │                                 │                  │           │ 51-180     │                                                   │         │                                 │
  │ V-D qd100                       │ same             │ same      │ qd100 ->   │ same                                              │ batchin │ R2; M3/M2                       │
  │                                 │                  │           │ eval_metri │                                                   │ g/      │                                 │
  │                                 │                  │           │ cs.jsonl:1 │                                                   │ backlog │                                 │
  │                                 │                  │           │ 81-210     │                                                   │ behavio │                                 │
  │                                 │                  │           │            │                                                   │ r       │                                 │
  │ V-D duplicate replay            │ scripts/         │ /api/     │ 50 ids x 5 │ same                                              │ replay  │ R2; M2/M3                       │
  │                                 │ evaluate-        │ events;   │ replays -> │                                                   │ does    │                                 │
  │                                 │ pilot.py:scenari │ journal_c │ eval_metri │                                                   │ not     │                                 │
  │                                 │ o_idempotency    │ lient_eve │ cs.jsonl:3 │                                                   │ create  │                                 │
  │                                 │ (286-330)        │ nt_id     │ 31-360     │                                                   │ extra   │                                 │
  │                                 │                  │           │            │                                                   │ journal │                                 │
  │                                 │                  │           │            │                                                   │ rows    │                                 │
  │ V-D netem stressed qd1          │ scripts/         │ same path │ synthetic  │ none found                                        │ impaire │ R2; M3                          │
  │                                 │ evaluate-netem-  │ under tc  │ qd1 ->     │                                                   │ d mesh  │                                 │
  │                                 │ propagation.py:m │           │ eval_netem │                                                   │ propaga │                                 │
  │                                 │ easure_cell      │           │ _propagati │                                                   │ tion    │                                 │
  │                                 │ (169-207)        │           │ on.jsonl:2 │                                                   │ complet │                                 │
  │                                 │                  │           │ -21        │                                                   │ es      │                                 │
  │ V-D netem stressed qd10         │ same             │ same      │ qd10 ->    │ none found                                        │ same    │ R2; M3                          │
  │                                 │                  │           │ eval_netem │                                                   │         │                                 │
  │                                 │                  │           │ _propagati │                                                   │         │                                 │
  │                                 │                  │           │ on.jsonl:2 │                                                   │         │                                 │
  │                                 │                  │           │ 3-42       │                                                   │         │                                 │
  │ V-D netem degraded qd1          │ same             │ same      │ qd1 ->     │ none found                                        │ same    │ R2; M3                          │
  │                                 │                  │           │ eval_netem │                                                   │         │                                 │
  │                                 │                  │           │ _propagati │                                                   │         │                                 │
  │                                 │                  │           │ on.jsonl:4 │                                                   │         │                                 │
  │                                 │                  │           │ 4-63       │                                                   │         │                                 │
  │ V-D netem degraded qd10         │ same             │ same      │ qd10 ->    │ none found                                        │ same    │ R2; M3                          │
  │                                 │                  │           │ eval_netem │                                                   │         │                                 │
  │                                 │                  │           │ _propagati │                                                   │         │                                 │
  │                                 │                  │           │ on.jsonl:6 │                                                   │         │                                 │
  │                                 │                  │           │ 5-84       │                                                   │         │                                 │
  │ V-E CRDT field profile cells    │ baseline/        │ /ops/     │ qd/profile │ none found                                        │ LWW     │ contrasts R3; not M             │
  │                                 │ scripts/         │ edit, /   │ cells ->   │                                                   │ anti-   │                                 │
  │                                 │ evaluate-crdt-   │ sync/     │ paper/     │                                                   │ entropy │                                 │
  │                                 │ baseline.py:scen │ pull, /   │ data/      │                                                   │ propaga │                                 │
  │                                 │ ario_field_propa │ sync/     │ eval_crdt_ │                                                   │ tion    │                                 │
  │                                 │ gation (170-242) │ push, /   │ baseline.j │                                                   │ compari │                                 │
  │                                 │                  │ state     │ sonl:2-187 │                                                   │ son     │                                 │
  │ V-E concurrent status           │ baseline/        │ /ops/     │ 30 runs -> │ none found                                        │ LWW     │ R3 contrast                     │
  │                                 │ scripts/         │ edit,     │ eval_crdt_ │                                                   │ loses   │                                 │
  │                                 │ evaluate-crdt-   │ full_sync │ baseline.j │                                                   │ authori │                                 │
  │                                 │ baseline.py:scen │           │ sonl:188-  │                                                   │ ty-     │                                 │
  │                                 │ ario_concurrent_ │           │ 217        │                                                   │ bearing │                                 │
  │                                 │ conflict (245-   │           │            │                                                   │ conflic │                                 │
  │                                 │ 285)             │           │            │                                                   │ t info  │                                 │
  │ V-E delete/update               │ baseline/        │ /ops/     │ 30 runs -> │ none found                                        │ LWW can │ R3 contrast                     │
  │                                 │ scripts/         │ delete, / │ eval_crdt_ │                                                   │ resurre │                                 │
  │                                 │ evaluate-crdt-   │ ops/edit, │ baseline.j │                                                   │ ct      │                                 │
  │                                 │ baseline.py:scen │ full_sync │ sonl:218-  │                                                   │ deleted │                                 │
  │                                 │ ario_delete_resu │           │ 247        │                                                   │ element │                                 │
  │                                 │ rrection (288-   │           │            │                                                   │         │                                 │
  │                                 │ 323)             │           │            │                                                   │         │                                 │
  │ V-E CRDT throughput             │ baseline/        │ local /   │ 30 runs -> │ none found                                        │ CRDT    │ R3 contrast                     │
  │                                 │ scripts/         │ ops/edit  │ eval_crdt_ │                                                   │ local-  │                                 │
  │                                 │ evaluate-crdt-   │ on        │ baseline.j │                                                   │ accept  │                                 │
  │                                 │ baseline.py:scen │ replicas  │ sonl:248-  │                                                   │ availab │                                 │
  │                                 │ ario_throughput  │ a/b/c     │ 278        │                                                   │ ility   │                                 │
  │                                 │ (326-376)        │           │            │                                                   │ tradeof │                                 │
  │                                 │                  │           │            │                                                   │ f       │                                 │
  │ V-E CRDT 60s convergence        │ baseline/        │ no real   │ n=10 ->    │ none found                                        │ all-    │ R3 contrast                     │
  │                                 │ scripts/         │ network   │ paper/     │                                                   │ replica │                                 │
  │                                 │ evaluate-crdt-   │ partition │ data/      │                                                   │ consist │                                 │
  │                                 │ baseline.py:scen │ ; sleep   │ eval_crdt_ │                                                   │ ency    │                                 │
  │                                 │ ario_convergence │ then      │ partition_ │                                                   │ after   │                                 │
  │                                 │ _after_partition │ full_sync │ n10.jsonl: │                                                   │ anti-   │                                 │
  │                                 │ (379-418)        │           │ 18-27      │                                                   │ entropy │                                 │
  │ V-F WAN 1s                      │ scripts/         │ inject-   │ partition  │ python3 scripts/evaluate-pilot.py                 │ command │ R1 support path; M2             │
  │                                 │ evaluate-        │ partition │ 1s ->      │                                                   │ -to-    │                                 │
  │                                 │ pilot.py:scenari │ .sh wan;  │ eval_metri │                                                   │ core    │                                 │
  │                                 │ o_recovery (174- │ then core │ cs.jsonl:2 │                                                   │ recover │                                 │
  │                                 │ 225)             │ master.in │ 11-240     │                                                   │ y after │                                 │
  │                                 │                  │ cident_ev │            │                                                   │ heal    │                                 │
  │                                 │                  │ ents      │            │                                                   │         │                                 │
  │                                 │                  │ polling   │            │                                                   │         │                                 │
  │ V-F WAN 10s                     │ same             │ same      │ partition  │ same                                              │ same    │ R1 support path; M2             │
  │                                 │                  │           │ 10s ->     │                                                   │         │                                 │
  │                                 │                  │           │ eval_metri │                                                   │         │                                 │
  │                                 │                  │           │ cs.jsonl:2 │                                                   │         │                                 │
  │                                 │                  │           │ 41-270     │                                                   │         │                                 │
  │ V-F WAN 60s                     │ same             │ same      │ partition  │ same                                              │ same    │ R1 support path; M2             │
  │                                 │                  │           │ 60s ->     │                                                   │         │                                 │
  │                                 │                  │           │ eval_metri │                                                   │         │                                 │
  │                                 │                  │           │ cs.jsonl:2 │                                                   │         │                                 │
  │                                 │                  │           │ 71-300     │                                                   │         │                                 │
  └─────────────────────────────────┴──────────────────┴───────────┴────────────┴───────────────────────────────────────────────────┴─────────┴─────────────────────────────────┘

  ## 2. Parameter Provenance

  ┌────────────────────────────────┬───────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────┐
  │ parameter                      │ source                                                            │ classification                                                         │
  ├────────────────────────────────┼───────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ n=30 default                   │ scripts/evaluate-pilot.py:33 RUNS_PER_CELL = ... "30"; paper      │ arbitrary default; no code/doc justification                           │
  │                                │ paper/sections/06_evaluation.tex:11-13                            │                                                                        │
  │ promotion n=300, 100 per phase │ script defaults --n 5, --writes-per-phase 20 at scripts/evaluate- │ arbitrary default; data confirms 5 x 20 x 3                            │
  │                                │ fenced-promotion.py:338-339; generated macros paper/data/         │                                                                        │
  │                                │ promotion_summary.tex:2-3                                         │                                                                        │
  │ queue depths 1,10,100          │ scripts/evaluate-pilot.py:128; CRDT baseline/scripts/evaluate-    │ arbitrary default                                                      │
  │                                │ crdt-baseline.py:172                                              │                                                                        │
  │ WAN partitions 1,10,60         │ scripts/evaluate-pilot.py:177                                     │ arbitrary default                                                      │
  │ command-isolation partition 10 │ scripts/evaluate-command-local-partition.py:507                   │ arbitrary default                                                      │
  │ netem profiles                 │ comment/citations scripts/evaluate-netem-propagation.py:10-13;    │ principled by citation comment; exact mapping not further justified    │
  │                                │ constants PROFILES at 64-75; command tc qdisc replace dev eth0    │                                                                        │
  │                                │ root netem delay <delay> <jitter> loss <loss> at 111-116          │                                                                        │
  │ 1000 saturation                │ scripts/evaluate-pilot.py:234 n = 1000                            │ arbitrary default; also not direct command endpoint                    │
  │ duplicate shape 50 x 5         │ scripts/evaluate-pilot.py:292-305, 323-325                        │ arbitrary default                                                      │
  │ A->B boundary                  │ install_new_epoch() inserts incident.command_epoch, restarts      │ mechanistic; no operator confirm                                       │
  │                                │ syncd at scripts/evaluate-fenced-promotion.py:110-134; called at  │                                                                        │
  │                                │ 267-268                                                           │                                                                        │
  │ B->C boundary                  │ harness switches request header from baseline epoch to new_epoch  │ mechanistic; no second epoch bump                                      │
  │                                │ at scripts/evaluate-fenced-promotion.py:270-276                   │                                                                        │
  │ TLA+ V=3,J=7,C=7,P=3           │ formal/tla/RescueOIS_large.cfg:4-8; run result formal/tla/        │ partly principled: C=J rationale appears for scaling in RUNS.md:19;    │
  │                                │ RUNS.md:17                                                        │ exact 7/3 bound is a tractable model bound, not domain-derived         │
  └────────────────────────────────┴───────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────┘

  ## 3. Latency-Explaining Configuration

  - qd <= 10 floor: responder push loop uses POLL_INTERVAL_S = 0.25 and sleeps POLL_INTERVAL_S * 4 after an empty poll (edge/syncd/src/push.py:28, 121-135). A newly inserted
    outbox row can wait about 1.0s. One batch covers qd 1/10 because BATCH_SIZE = 50 (push.py:29, outbox.fetch_unforwarded at edge/syncd/src/outbox.py:11-21).
  - qd100 rise: qd100 needs two push batches (BATCH_SIZE = 50) and pays the post-success sleep 0.25s between batches (push.py:135), plus 100 sequential tablet-facing POSTs in
    the harness (scripts/evaluate-pilot.py:132-143). Observed median delta is 1224.0 - 946.3 = 277.7ms.
  - WAN recovery call graph: scenario_recovery() (scripts/evaluate-pilot.py:174-225) -> inject-partition.sh wan disconnects edge-cmd-syncd-1 (scripts/inject-partition.sh:21-24,
    55-62) -> responder post_event() inserts outbox (edge/ops-api/src/routes/api.py:34-60) -> push.run() forwards (edge/syncd/src/push.py:114-135) -> accept_event_batch()
    journals (edge/syncd/src/accept.py:128-235) -> command forward.run() (edge/syncd/src/forward.py:93-111) -> _forward_once() posts /sync/journal-batch (forward.py:30-87) ->
    core post_journal_batch() (core/sync-api/src/routes/sync.py:78-126).
  - WAN timeout: asyncpg pool has command_timeout=10.0 at edge/syncd/src/db.py:19-21. No explicit “broken-connection-discard branch” exists in repo code; that is an inference
    from asyncpg/pool behavior. In-repo recovery branches are forward.run() exception handlers at edge/syncd/src/forward.py:102-110 and retry sleep at 111.
  - Phase B cheap path: accept_event_batch() calls validate_request_epoch() before get_pool() (edge/syncd/src/accept.py:148-156). Stale traffic skips pool acquire, transaction,
    incident.state insert, FOR UPDATE, idempotency lookup, event_seq increment, incident.journal insert, and state update (accept.py:161-228).
  - Throughput bottleneck: the reported throughput harness posts 1000 events to responder /api/events, not direct command /accept/event-batch (scripts/evaluate-pilot.py:247).
    Code-implied floor is 20 push batches for 1000 events at BATCH_SIZE = 50 plus 19 sleeps of 0.25s = 4.75s before command DB cost. Command accept itself serializes same-
    incident writes through SELECT ... FOR UPDATE (edge/syncd/src/accept.py:176-183) and uses asyncpg pool max_size=8 (edge/syncd/src/db.py:20).

  ## 4. CRDT Baseline Comparability Audit

  - Family: operation-based LWW Element Set. Source: baseline/crdt/crdt_lww.py:1-7, class LWWElementSet at 110-205.
  - Clock: physical wall clock time_ns(), defaulted in Operation.new() (baseline/crdt/crdt_lww.py:13, 64-82) and replica.edit/delete() (baseline/crdt/replica.py:48-66).
    Tie-breakers: replica_id, op_id (crdt_lww.py:20-31).
  - Replicas/topology: four FastAPI processes a, b, c, core (baseline/docker-compose.yml:4-38); three writers for throughput (baseline/scripts/evaluate-crdt-baseline.py:327-
    338).
  - Anti-entropy: no background schedule. Harness manually calls pull_ops() and push_ops() (baseline/scripts/evaluate-crdt-baseline.py:110-128). Field propagation loops every
    0.02s (187-197); partition convergence does one full_sync() after sleep (395-398).
  - Netem diff: AAL applies same profile to two syncd containers (scripts/evaluate-netem-propagation.py:57-61, 102-118); CRDT applies same profile constants to all four CRDT
    containers (baseline/scripts/evaluate-crdt-baseline.py:43-46, 141-150). AAL sleeps 0.5s after applying (evaluate-netem-propagation.py:303-306); CRDT sleeps 0.2s and excludes
    local edit time (evaluate-crdt-baseline.py:182-220).
  - Alignment: not exact. AAL no-netem qd 1/10/100 n=30; AAL netem qd 1/10 n=20. CRDT netem qd 1/10/100 n=30. AAL WAN partitions 1/10/60 n=30; CRDT table uses only 60s n=10 from
    eval_crdt_partition_n10.jsonl.
  - Convergence meaning: CRDT time_to_all_replicas_consistent_ms measures elapsed time for full_sync(["a","b","c","core"]) after partition sleep, then digest equality (baseline/
    scripts/evaluate-crdt-baseline.py:395-406). It is all-replica visibility after a harness-triggered anti-entropy round, not first-replica visibility.
  - Asymmetries: CRDT is in-memory, no durable DB/outbox, no authority check, local write time excluded for field propagation, no actual Docker partition in convergence; AAL
    includes Postgres/outbox/polling. CRDT netem impairs more containers, but workload is easier on durability and authority.

  ## 5. Formal-Method <-> Service-Path Correspondence

  ┌───────────────────────────┬────────────────────────────────┬───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
  │ invariant                 │                     TLA+ lines │ meaning                                               │ runtime witness                                        │
  ├───────────────────────────┼────────────────────────────────┼───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ TypeOK                    │ formal/tla/RescueOIS.tla:71-83 │ variables stay in declared domains and partition is   │ no direct service-path counterpart                     │
  │                           │                                │ symmetric/irreflexive                                 │                                                        │
  │ SingleAuthority           │                        198-201 │ at most one vehicle holds write authority             │ model only; service path single-edge promotion does    │
  │                           │                                │                                                       │ not prove cross-edge authority                         │
  │ EpochAuthorityCoupling    │                        203-209 │ at most one authority per epoch                       │ V-B stale rejection: eval_fenced_promotion.jsonl:22-   │
  │                           │                                │                                                       │ 41; accept guard edge/syncd/src/accept.py:78-103       │
  │ DurabilityAcrossPromotion │                        211-215 │ recorded epoch snapshots remain prefixes of current   │ partial witness: V-B summaries                         │
  │                           │                                │ journal                                               │ eval_fenced_promotion.jsonl:62 show epoch seq          │
  │                           │                                │                                                       │ contiguity; no snapshot table in service               │
  │ NoForkedJournal           │                        217-225 │ no duplicate event_seq positions in journal           │ V-C summary eval_command_local_partition.jsonl:22; V-B │
  │                           │                                │                                                       │ duplicate_seqs_across_epochs=0 at                      │
  │                           │                                │                                                       │ eval_fenced_promotion.jsonl:62                         │
  │ LocalIdempotency          │                        227-232 │ no duplicate client_event_id in journal               │ V-D duplicate replay eval_metrics.jsonl:331-360; DB    │
  │                           │                                │                                                       │ index edge/db/                                         │
  │                           │                                │                                                       │ migrations/004_idempotency_and_sync_state.sql:21-22    │
  │ SingleCommand             │                        234-238 │ at most one command-role vehicle                      │ no service-path counterpart; Compose can run multiple  │
  │                           │                                │                                                       │ command roles                                          │
  └───────────────────────────┴────────────────────────────────┴───────────────────────────────────────────────────────┴────────────────────────────────────────────────────────┘

  Strict vs weak: weak cfgs set StrictPromotion = FALSE (formal/tla/RescueOIS_weak.cfg:8). Mechanically, PromoteWeak() keeps unreachable old authorities and does not allocate a
  new epoch (formal/tla/RescueOIS.tla:131-144), unlike PromoteStrict() which requires connectivity to current commands, sets authority' = {v}, increments currentEpoch, and
  snapshots the journal (146-162). weak_epoch suppresses SingleAuthority to expose EpochAuthorityCoupling (formal/tla/RescueOIS_weak_epoch.cfg:10-17); weak_journal suppresses
  authority/epoch invariants to expose NoForkedJournal (formal/tla/RescueOIS_weak_journal.cfg:10-16).

  Hypothesis mapping: formal/python/tests/test_no_two_writers.py:46-71 mirrors SingleAuthority, NoForkedJournal, LocalIdempotency, SingleCommand; weak counterexample at 78-96.
  test_idempotency.py:16-21 mirrors LocalIdempotency. test_seq_monotonicity.py:13-20 mirrors dense sequencing, a runtime analogue of no fork/gaps but not a named TLA+ invariant.

  ## 6. Non-Claims Grounded in Code

  - Concurrent status semantic rejection: absent in edge/syncd/src/accept.py:accept_event_batch. Guard would go after SELECT ... FOR UPDATE (176-184) and before seq += 1/journal
    insert (197-215). edge/ops-api/src/incident.py:append_event is still TODO (9-16).
  - Delete/update race guard: same insertion point; no tombstone/status semantics exist in IncomingEvent beyond raw event_type/payload (edge/syncd/src/accept.py:106-114).
  - Tablet stub vs Android: stub only emits synthetic HTTP POSTs (scripts/tablet-stub.py:21-48) with synthetic user_id. Android has TODOs for Room/outbox/retry (tablet/app/src/
    main/kotlin/.../SyncManager.kt:9-21), empty Room entities (AppDatabase.kt:9-17), MapLibre TODOs (MapLibreWrapper.kt:7-10), and UI TODOs (IncidentScreen.kt:8-10).
  - Operator confirm: promote-responder.sh asks for previous command id and yes (scripts/promote-responder.sh:47-70), inserts local command_epoch (79-82), flips EDGE_ROLE (84).
    No token, cert identity, multi-operator UX, or durable audit API; target token model is only in docs/adr/0004-promotion-authority-model.md:24-28.
  - Single-host emulation: scripts/dev-up.sh:14-18 creates one external Docker bridge; all Compose stacks attach to it (core/docker-compose.yml:3-6, edge/docker-compose.yml:3-
    6). Partitions are Docker network disconnects (scripts/inject-partition.sh:55-62).
  - mTLS/WireGuard overhead: eval paths use HTTP URLs (scripts/dev-up.sh:33, 42; harness constants evaluate-pilot.py:36-37). Nginx TLS/mTLS is placeholder/commented (edge/nginx/
    nginx.conf:33-43); WireGuard is templates only (edge/wireguard/wg0-edge.conf.template:5-14, core/wireguard/wg0-core.conf.template:5-17).

  ## 7. R1 / R2 / R3 Evidence Map

  ┌──────────────────────────────────┬──────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┬───────────────────────────────────┐
  │ requirement                      │ code artifacts                   │ evidence cells                  │ evidence boundary               │ gap-closing proposal              │
  ├──────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
  │ R1 offline operation             │ local edge services edge/docker- │ V-C responder isolation; V-F    │ no Android offline validation;  │ scripts/evaluate-offline-tier-    │
  │                                  │ compose.yml; command local DB/   │ recovery                        │ V-F actually disconnects        │ operation.py, scenario            │
  │                                  │ journal edge/syncd/src/          │                                 │ command syncd from the only     │ offline_cached_services:          │
  │                                  │ accept.py; core backfill edge/   │                                 │ bridge, not just core           │ partition core, exercise /api/    │
  │                                  │ syncd/src/forward.py             │                                 │                                 │ bootstrap, /api/search, /tiles,   │
  │                                  │                                  │                                 │                                 │ command accept; JSONL fields      │
  │                                  │                                  │                                 │                                 │ tier, operation,                  │
  │                                  │                                  │                                 │                                 │ partition_target, success,        │
  │                                  │                                  │                                 │                                 │ latency_ms; runtime ~5 min        │
  │ R2 durable forward-only          │ outbox insert edge/ops-api/src/  │ V-D qd, duplicate, netem        │ no restart/crash durability;    │ scripts/evaluate-outbox-crash-    │
  │ submission                       │ routes/api.py:34-60;             │                                 │ xfail crash tests edge/syncd/   │ restart.py, scenario              │
  │                                  │ outbox.device_outbox; push/mark  │                                 │ tests/                          │ partition_restart_replay:         │
  │                                  │ edge/syncd/src/push.py:49-108,   │                                 │ test_partition_and_boundary_vis │ partition mesh, POST 30, restart  │
  │                                  │ outbox.py:38-49; idempotency     │                                 │ ibility.py:319-340              │ responder services, heal; fields  │
  │                                  │ index 004_idempotency...sql:12-  │                                 │                                 │ accepted_local,                   │
  │                                  │ 22                               │                                 │                                 │ outbox_before_restart,            │
  │                                  │                                  │                                 │                                 │ journal_after_heal, duplicates,   │
  │                                  │                                  │                                 │                                 │ forwarded_after_restart; runtime  │
  │                                  │                                  │                                 │                                 │ ~3-6 min                          │
  │ R3 attributable command          │ incident.command_epoch migration │ V-B, V-C, formal weak/strict    │ no authenticated commander      │ scripts/evaluate-cross-edge-      │
  │ authority                        │ 005_command_epoch.sql:12-35;     │                                 │ identity; no cross-edge         │ promotion.py, scenario            │
  │                                  │ epoch guard edge/syncd/src/      │                                 │ promotion race; promote-        │ two_command_epoch_fence: start 2  │
  │                                  │ accept.py:78-103; formal TLA+    │                                 │ responder.sh host-level         │ command candidates, promote with  │
  │                                  │ invariants                       │                                 │ confirmation only               │ token fixture, replay stale       │
  │                                  │                                  │                                 │                                 │ writes; fields old_epoch,         │
  │                                  │                                  │                                 │                                 │ new_epoch, old_status,            │
  │                                  │                                  │                                 │                                 │ new_status, operator_subject,     │
  │                                  │                                  │                                 │                                 │ journal_epoch_counts; runtime ~5- │
  │                                  │                                  │                                 │                                 │ 10 min                            │
  └──────────────────────────────────┴──────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┴───────────────────────────────────┘

  ## 8. Proposed Narrative Spine for Section V-A

  - We measure stale-epoch rejection because the paper claims fenced promotion preserves command authority in §IV-M4; the measurement is well-defined because the code rejects
    mismatched X-Command-Epoch before DB work (edge/syncd/src/accept.py:validate_request_epoch).
  - We measure direct command commits during responder isolation because the paper claims authority-bearing writes are linearized at the command edge in §IV-M1/M2; the
    measurement is well-defined because the code assigns event_seq inside one transaction (edge/syncd/src/accept.py:accept_event_batch).
  - We measure outbox propagation because the paper claims responder submissions are durable and forward-only in §IV-M3; the measurement is well-defined because the code inserts
    before local ACK and marks forwarded only after command ACK (edge/ops-api/src/routes/api.py:post_event, edge/syncd/src/outbox.py:mark_forwarded).
  - We measure duplicate replay because the paper claims idempotent submission in §IV-M2/M3; the measurement is well-defined because the code enforces client_event_id uniqueness
    at outbox and journal (edge/db/migrations/004_idempotency_and_sync_state.sql).
  - We measure CRDT-LWW because the paper claims CRDT merge cannot encode command authority in §II/§V-E; the measurement is well-defined because the baseline applies physical-
    clock LWW operations (baseline/crdt/crdt_lww.py:Operation.new).
  - We measure command-to-core recovery because the paper claims backhaul recovery is a support-path property in §IV partition behavior; the measurement is well-defined because
    the code forwards committed journal slices to /sync/journal-batch (edge/syncd/src/forward.py:_forward_once).

  ## 9. Inconsistency Log

  - V-A says three responder-role edge nodes (paper/sections/06_evaluation.tex:8-10), but scripts/dev-up.sh defaults to RESPONDERS=1 (13) and evaluate-command-local-
    partition.py:start_stack forces RESPONDERS=1 (89-95). JSONL does not record responder count.
  - V-F prose scopes “command-core WAN recovery only” and says responder-command paths remain available (paper/sections/06_evaluation.tex:181-185), but inject-partition.sh wan
    disconnects edge-cmd-syncd-1 from the only Docker bridge (scripts/inject-partition.sh:21-24, 55-62), cutting it off from core, responders, and Postgres.
  - Throughput prose/table labels command journal serialization (paper/sections/06_evaluation.tex:107-110, tab_evaluation.tex:13-14), but scenario_throughput() submits to
    responder /api/events (scripts/evaluate-pilot.py:247), so the result includes responder ops-api, outbox, push batching, and polling.
  - V-C prose says p95 7.1 ms (paper/sections/06_evaluation.tex:106-107); generated table correctly says median/max 2.75/7.06 ms (paper/tables/tab_evaluation.tex:17). JSONL
    summary p95 is 3.39996105 (paper/data/eval_command_local_partition.jsonl:22).
  - Paper says field submissions propagate “exactly-once” (paper/sections/06_evaluation.tex:115-116); protocol and code are at-least-once delivery with command-edge dedup
    (paper/sections/04_synchronization_protocol.tex:54-55, edge/syncd/src/push.py:89-95, edge/syncd/src/accept.py:187-195).
  - Data/script drift: current evaluate-command-local-partition.py writes scenario command_accept_path_during_responder_syncd_isolation (331, 422, 487), but checked JSONL uses
    command_local_responder_isolation (paper/data/eval_command_local_partition.jsonl:1-22).
  - Stale docs: docs/architecture/sync-protocol.md:62, docs/adr/0004-promotion-authority-model.md:7-9, and xfail tests edge/syncd/tests/
    test_partition_and_boundary_visibility.py:295-316 say durable command epoch/stale rejection are not implemented; code and paper now implement the service-level guard (edge/
    syncd/src/accept.py:78-103).
  - Promotion script is not full fenced promotion: it warns split-brain if prior command is reachable (scripts/promote-responder.sh:9-11) and inserts only local epoch (79-84).
    Paper’s V-B service check is single-edge, which §VI discloses (paper/sections/07_discussion.tex:47-53).
  - CRDT “partition” convergence is not an actual network partition; the harness sleeps for partition_s and then calls full_sync() (baseline/scripts/evaluate-crdt-
    baseline.py:392-398).
  - CRDT comparison is not exactly same workload: CRDT field propagation includes qd100 under netem and n=30 (baseline/scripts/evaluate-crdt-baseline.py:170-242); AAL netem uses
    qd1/10 and n=20 (scripts/evaluate-netem-propagation.py:229-236). CRDT partition table uses only 60s n=10 (paper/data/eval_crdt_partition_n10.jsonl:18-27), while AAL WAN uses
    1/10/60 n=30.
  - Migration comment says “Seed epoch 0” (edge/db/migrations/005_command_epoch.sql:22), but BIGSERIAL insert without explicit id seeds epoch 1 (25-26); the harness assumes
    baseline epoch 1 (scripts/evaluate-fenced-promotion.py:223-225).
  - Netem numeric values match: paper 80ms +/- 30ms, 2% and 200ms +/- 80ms, 8% (paper/sections/06_evaluation.tex:123-130) match AAL constants (scripts/evaluate-netem-
    propagation.py:64-75).
  - Warm-up exclusion confirmed: JSONL run 0 marks warmup_run (paper/data/eval_metrics.jsonl:301), and table generation excludes run_index == 0 (paper/scripts/
    generate_tables.py:90-), yielding n=29ables.tex:14 promotionMedianB generation exists: paper/scripts/plot_promotion_cdf.py:137154paper/data/promotion.tex; broken.

