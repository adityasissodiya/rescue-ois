# Citation Audit (NCA 2026, Phase 3.3)

Run date: 2026-05-13. Branch: `nca2026-submission`.

## Corrected

| Key | Field | Before | After | Source |
|---|---|---|---|---|
| `sagor2024distressnetng` | `number` | `1` | `3` | DBLP for DOI 10.1145/3639057 |
| `sagor2024distressnetng` | `pages` | `1--31` | `37:1--37:31` | DBLP for DOI 10.1145/3639057 |

ACM landing page (`https://dl.acm.org/doi/10.1145/3639057`) returned HTTP 403 to anonymous fetch; verified against `https://dblp.org/search?q=DistressNet-NG+Sagor` instead. DBLP reports issue 3, pages 37:1-37:31.

## Verified, no change needed

| Key(s) | Where cited | Verdict |
|---|---|---|
| `lamport1998parttime`, `ongaro2014raft`, `katsarakis2020hermes` | `01_introduction.tex` §I para 4 | Used to attribute "strong ordering when a quorum is reachable" -- correct under the original papers' assumptions. The "quorum may not hold during vehicle isolation" clause is the *paper's* setup, not attributed to those refs. No over-claim. |
| `lamport1998parttime`, `ongaro2014raft` | `02_problem_analysis.tex` §II-B "Consensus and state-machine replication" | Attribution "Paxos and Raft provide replicated agreement and ordered logs" is correct. No intermittent-network claim is made on these refs. |
| `ongaro2014raft` | `06_evaluation.tex` §V-F "as Raft requires by design" | Attribution is to the canonical Raft paper for the quorum requirement, which Raft does state by design. Correct. |
| `almeida2014delta` | `01_introduction.tex` and `02_problem_analysis.tex` | Used to attribute "CRDT-based replication is valuable for naturally mergeable state" and "convergence for mergeable replicated state". Both are correct -- the claim is bounded to convergence/SEC, not stronger consistency. |
| `gomes2017verifyingsec` | `02_problem_analysis.tex` §II-B "CRDTs" | Attributed to convergence/SEC. The Gomes et al. result is a formal proof of SEC, which is exactly what is claimed in the text. No over-claim. |

## Notes on prior-art attribution discipline applied during Phase 3

- Phase 3.2 introduced four new citations into II-B and II-D. Each is attached to one specific mechanism or framing (transactional outbox, entity-boundary, single-leader+idempotency-key textbook pattern, RedBlue mixed-consistency split). None of the new citations claim more than its source provides.
- The `vanrenesse2004chain` citation was flagged during an earlier bibtex run as undefined; the entry is present in `refs.bib` and now resolves. No action.

## Items deferred / not in scope

- The bibliography contains entries that are not currently cited from any `.tex` file. Phase 6 page-budget trims may revisit whether to drop unused entries; that is a layout decision, not an attribution issue.
