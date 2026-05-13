# NCA 2026 Decisions

Submission deadline: 19 June 2026 AoE.
Today: 12 May 2026.
Working window: ~5.5 weeks. Schedule below uses that window with proper buffer
rather than crash-program compression.

1. Submission target: Y. Regular paper, 8 pages base, willing to pay for both
   extras (10-page effective ceiling). Primary topic framing is Network
   Architectures & Protocols; secondary framing is Applications, Prototypes &
   Experiences.

2. Authorship: confirmed out of band. Author names, affiliations,
   acknowledgements, repository URLs, and institution-identifying artifact
   metadata must stay out of the double-blind manuscript and any reviewer-facing
   bundle. Camera-ready metadata is handled only after acceptance.

3. Safety property strategy: C (both).
   Primary: TLA+ specification with `NoTwoWriters` invariant checked by TLC
   over a bounded model (3 vehicles, MaxSeq = 5, full partition powerset).
   Secondary: Hypothesis property tests covering `event_seq` monotonicity,
   `client_event_id` idempotency, and no-double-promotion under arbitrary
   partition / heal / promotion schedules. Both feed section 6.
   Hard fallback to A only: if a TLC-checked model is not green by end of day
   Mon 1 June 2026, drop the Hypothesis layer and ship A alone.
   Hard fallback to B only: if no TLC-checked model exists by end of day
   Sun 7 June 2026, switch to B exclusively and do not look back.

4. Baseline: Raft-measured and contextual.
   Use hashicorp/raft (Go) wrapped behind a thin journal interface, deployed
   as a 3-node cluster across the existing Docker Compose topology. Treat it as
   a quorum-progress illustration only, not a workflow-equivalent latency or
   correctness baseline.

5. Schedule with cut-over dates:
   - Phase 1 (IEEE migration, anonymisation, bib expansion, skeleton):
     ends Wed 13 May 2026.
   - Phase 2 (real measurements via unified harness, >=30 runs/cell):
     ends Wed 27 May 2026.
   - Phase 3 (safety property, Path C):
     ends Sun 7 June 2026.
   - Phase 4 (Raft baseline + section 2/section 6 rewrite + comparison table):
     ends Sun 14 June 2026.
   - Phase 5 (internal review + tightening + preflight):
     ends Tue 16 June 2026.
   - Submission target: Wed 17 June 2026, 23:59 local. Do not aim later.

6. Trigger dates:
   - Plan D (skip submission, retarget to a later systems or crisis-informatics venue):
     trigger Wed 27 May 2026 if Phase 2 has not produced >=1 non-null
     measurement per scenario.
   - Plan B (downgrade to Short Paper, 4 pages, if NCA 2026 reintroduces
     the category): trigger Sun 7 June 2026 if Phase 3 has produced
     neither a TLC-checked model nor a passing Hypothesis corpus.
   Both acknowledged as real options, not hedges.

7. Anonymisation branch `nca2026-submission`: Y. Created from the current
   `main` HEAD before Phase 1 execution.
