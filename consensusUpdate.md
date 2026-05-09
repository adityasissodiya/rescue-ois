# consensusUpdate.md — paper changes derived from two consensus reports

Hand-off for Claude Code working on the NCA 2026 paper repo. Goal: integrate
genuinely-relevant findings from two Consensus literature-review reports into
the `main.tex` (or whatever the paper source file is called) and the
bibliography file. **Do not** treat this as a citation-padding exercise;
every change below has a stated reason.

**Source documents:** the original consensus report on offline-first
edge/mobile information systems for emergency response (covered in §1–§3
below), and a second report on offline-capable emergency command and control
which adds two genuinely useful references on verified replication
(integrated in §2.3.1). Davidson 1985 from the second report is already cited
in the paper as ref [29] — no action needed there. Most of the second
report's connectivity/UAV/mesh entries duplicate or sit below the paper's
stated architectural scope and are listed in §3.

---

## 0. Pre-flight

Before editing, please verify the following in the repo and adjust as needed:

1. Identify the paper source file (likely `paper/main.tex` or
   `paper/paper.tex`). Confirm bibliography style (IEEEtran given NCA venue).
2. Identify the `.bib` file (likely `paper/refs.bib` or similar). Note the
   citation-key convention used by existing entries — match it exactly when
   adding new ones. The keys I propose below (`jahanian2022conice`,
   `sagor2024distressnetng`, etc.) should be normalized to your convention.
3. Cross-check whether any of the proposed BibTeX entries are **already
   present** in the bibliography but uncited. If they are, reuse the existing
   key rather than adding a duplicate.
4. The numbered citation references in this document (`[N]`) are placeholders.
   You will need to map each to a `\cite{key}` once the bib entries are in.

If anything in the pre-flight reveals a structural assumption I made that's
wrong (e.g. there's a separate `related-work.tex` partial), apply the changes
to wherever the corresponding text actually lives.

---

## 1. New bibliography entries to add

Add the following to the `.bib` file. Adjust keys to repo convention. **Check
for duplicates first.**

```bibtex
@article{jahanian2022conice,
  author    = {Jahanian, Mahdi and Ramakrishnan, K. K.},
  title     = {{CoNICE}: Consensus in Intermittently-Connected Environments
               by Exploiting Naming With Application to Emergency Response},
  journal   = {IEEE/ACM Transactions on Networking},
  volume    = {30},
  number    = {4},
  pages     = {1926--1939},
  year      = {2022},
  doi       = {10.1109/TNET.2022.3156101}
}

@article{sagor2024distressnetng,
  author    = {Sagor, M. F. H. and Haroon, A. and Stoleru, R. and Bhunia, S.
               and Altaweel, A. and Chao, M. and Jin, L. and Maurice, M.
               and Blalock, R.},
  title     = {{DistressNet-NG}: A Resilient Data Storage and Sharing
               Framework for Mobile Edge Computing in Cyber-Physical Systems},
  journal   = {ACM Transactions on Cyber-Physical Systems},
  volume    = {8},
  number    = {1},
  pages     = {1--31},
  year      = {2024},
  doi       = {10.1145/3639057}
}

@inproceedings{hanssen2025emergency,
  author    = {Hanssen, {\O}ystein},
  title     = {Data Replication for Distributed Emergency Management Systems},
  booktitle = {Norsk IKT-konferanse for forskning og utdanning (NIK)},
  year      = {2025},
  doi       = {10.5324/b816jf45}
}

@article{tran2021ndn,
  author    = {Tran, Manh and Kim, Younghan},
  title     = {Named Data Networking Based Disaster Response Support System
               over Edge Computing Infrastructure},
  journal   = {Electronics},
  volume    = {10},
  number    = {3},
  pages     = {335},
  year      = {2021},
  doi       = {10.3390/electronics10030335}
}

@article{li2017vehicleassist,
  author    = {Li, Peng and Miyazaki, Toshiaki and Wang, Kun and Guo, Song
               and Zhuang, Weihua},
  title     = {Vehicle-Assist Resilient Information and Network System for
               Disaster Management},
  journal   = {IEEE Transactions on Emerging Topics in Computing},
  volume    = {5},
  number    = {3},
  pages     = {438--448},
  year      = {2017},
  doi       = {10.1109/TETC.2017.2693286}
}

@inproceedings{haroon2022edgecoord,
  author    = {Haroon, A. and Sagor, M. and Maurice, M. and Jin, L.
               and Stoleru, R. and Blalock, R.},
  title     = {On Edge Coordination in Highly Dynamic Cyber-Physical
               Systems for Emergency Response},
  booktitle = {2022 Workshop on Cyber Physical Systems for Emergency
               Response (CPS-ER)},
  pages     = {7--12},
  year      = {2022},
  doi       = {10.1109/CPS-ER56134.2022.00008}
}

@article{aboualola2023edgesurvey,
  author    = {Aboualola, M. and Abualsaud, K. and Khattab, T. and Zorba, N.
               and Hassanein, H.},
  title     = {Edge Technologies for Disaster Management: A Survey of
               Social Media and Artificial Intelligence Integration},
  journal   = {IEEE Access},
  volume    = {11},
  pages     = {73782--73802},
  year      = {2023},
  doi       = {10.1109/ACCESS.2023.3293035}
}

@article{alwakeel2025edgefog,
  author    = {Alwakeel, A.},
  title     = {Adaptive edge-fog healthcare networks: a novel framework
               for emergency response management},
  journal   = {Journal of Cloud Computing},
  volume    = {14},
  year      = {2025},
  doi       = {10.1186/s13677-025-00784-3}
}

@article{pothineni2024offlinefirst,
  author    = {Pothineni, S.},
  title     = {Offline-First Mobile Architecture: Enhancing Usability and
               Resilience in Mobile Systems},
  journal   = {Journal of Artificial Intelligence General Science (JAIGS)},
  year      = {2024},
  doi       = {10.60087/jaigs.v7i01.387}
}

@article{sciullo2020locate,
  author    = {Sciullo, L. and Trotta, A. and Felice, M.},
  title     = {Design and performance evaluation of a {LoRa}-based mobile
               emergency management system ({LOCATE})},
  journal   = {Ad Hoc Networks},
  volume    = {96},
  year      = {2020},
  doi       = {10.1016/j.adhoc.2019.101993}
}

@article{gomes2017verifyingsec,
  author    = {Gomes, Victor B. F. and Kleppmann, Martin and
               Mulligan, Dominic P. and Beresford, Alastair R.},
  title     = {Verifying strong eventual consistency in distributed systems},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {1},
  number    = {OOPSLA},
  pages     = {1--28},
  year      = {2017},
  doi       = {10.1145/3133933}
}

@article{lewchenko2025boltonsc,
  author    = {Lewchenko, Nicholas V. and Kaki, Gowtham and Chang, Bor-Yuh Evan},
  title     = {Bolt-On Strong Consistency: Specification, Implementation, and
               Verification},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {9},
  number    = {OOPSLA},
  pages     = {1604--1631},
  year      = {2025},
  doi       = {10.1145/3720502}
}
```

Verify each DOI resolves before committing. If any fail to resolve in the
final compile, the consensus report is the primary source for the metadata,
re-check from there.

---

## 2. Section-by-section edits

### 2.1 Section I (Introduction)

**Locate** the paragraph beginning *"No existing replication pattern satisfies
this combination of requirements."*

**Why change it:** the current paragraph cites general consensus / multi-primary
/ CRDT work, but does not engage with the closest existing work that is
explicitly aimed at emergency-response intermittent connectivity (CoNICE).
A reviewer familiar with the field will flag this as a missed comparison.

**Edit:** insert a new sentence after the consensus sentence
(`Consensus-based state-machine replication [14]--[16] is unavailable...`)
and before the multi-primary sentence.

Insert this sentence:

> Adaptations explicitly aimed at intermittently-connected emergency-response
> settings, such as CoNICE's hierarchical-naming consensus
> \cite{jahanian2022conice}, retain agreement semantics that bind every commit
> to a quorum the operational profile in Section~\ref{sec:setting} cannot
> reliably assemble.

(Adjust the section reference label to whatever your `\label{}` uses for the
operational-setting subsection.)

**Optional supporting edit** in the same paragraph: change

> No existing replication pattern satisfies this combination of requirements.

to

> No existing replication pattern satisfies this combination of requirements,
> and the gap is reflected in the wider literature: recent systematic reviews
> of offline-first and edge-based emergency-response systems explicitly note
> the lack of head-to-head empirical comparisons between replication designs
> in disaster scenarios \cite{aboualola2023edgesurvey}.

This second edit also serves Section VI's framing — see §2.5 below.

---

### 2.2 Section II.A (Replication and State-Machine Replication)

**Locate** the paragraph ending with the Tango sentence:

> Tango is especially relevant because it builds distributed data structures
> over a shared log and then materializes application views from that log [24].

**Why change it:** II.A currently lists generic SMR work but never names
the closest single work that targets your operational profile. CoNICE
deserves an explicit half-paragraph because it is what a reviewer will
ask "why isn't this enough?" about.

**Edit:** add the following paragraph (or extend the existing one) **before**
the paragraph beginning *"The Rescue OIS incident journal follows the
shared-log/materialized-state pattern..."*:

> Closer to the operational profile of this paper, CoNICE
> \cite{jahanian2022conice} explicitly adapts consensus to
> intermittently-connected environments for emergency response, using
> hierarchical naming and epidemic propagation to extend agreement under
> partitions. The architectural distinction is structural rather than
> incremental: CoNICE preserves consensus semantics across all participants
> and therefore inherits the quorum-progress requirement when partitions
> isolate enough nodes. The architecture in this paper diverges by encoding
> authority operationally — at the dispatched command vehicle — rather than
> via voting, trading automatic failover for guaranteed write availability
> at the designated principal under arbitrary partition. Section~\ref{sec:eval}
> reports the empirical consequence of this choice against a Raft baseline
> on the same emulation.

Adjust label `\ref{sec:eval}` to your evaluation-section label.

---

### 2.3 Section II.B (Local-First and CRDT-Based Replication)

**Locate** the paragraph beginning *"Local-first systems prioritize local
availability..."*

**Why change it:** the existing list of references is general distributed
systems work. Hanssen 2025 is the directly-on-topic CRDT-for-emergency-
management paper, and not citing it is awkward when your II.B argument is
specifically *why CRDTs don't fit incident state in emergency response*.

**Edit:** insert this sentence **after** the Almeida delta-CRDT sentence
(`...including efficient delta-based variants [19].`) and **before** the
Köhler/Haas/Jannes sentence about invariants:

> Hanssen \cite{hanssen2025emergency} applies CRDT-based replication directly
> to distributed emergency-management systems, demonstrating strong eventual
> consistency under intermittent connectivity for naturally mergeable state.
> Mobile offline-first patterns more broadly are surveyed by Pothineni
> \cite{pothineni2024offlinefirst}, who emphasises durable outboxes and
> opportunistic synchronisation as the dominant design idiom.

The existing argument that follows ("Those techniques are valuable for
naturally mergeable state, but the incident journal contains ordered,
authority-bearing events...") still stands and now lands harder, because
Hanssen is exactly the kind of paper where the question "but why not just
CRDT it?" is most naturally asked.

#### 2.3.1 Section II.B — verification lineage (from second consensus report)

**Locate** the sentence in II.B reading:

> Recent work focuses on preserving application-level invariants and
> verifying safety properties in replicated settings [20], [21], [25].

**Why change it:** the [20]/[21]/[25] cluster is application-level invariant
work that builds on a prior line of mechanized SEC verification, but the
paper does not cite that upstream work. Gomes et al. 2017 is the canonical
verified-CRDT-SEC paper and naturally precedes the cluster. Lewchenko et
al. 2025 is the most recent extension of that line into bolt-on strong
consistency over weaker stores, which is conceptually adjacent to layering
authoritative ordering (the journal) above eventually-consistent caches
(the responder/tablet tiers).

**Edit:** rewrite the sentence as

> Mechanized verification of strong eventual consistency for replicated
> data was established by Gomes et al.\ \cite{gomes2017verifyingsec};
> recent work extends this line to preserving application-level invariants
> in replicated settings \cite{...,...,...} and to bolt-on strong
> consistency layered over weaker stores \cite{lewchenko2025boltonsc}.

(Replace the `\cite{...,...,...}` with the existing keys for refs [20],
[21], [25].) The Lewchenko cite is **optional** — drop it if you're tight
on space; Gomes is the higher-priority addition because it grounds the
existing cluster.

**Optional follow-on:** Section VI.D (formal safety verification) currently
introduces the TLA+ work without situating it in any prior verification
literature. If you want to thread the needle, a single sentence at the
start of VI.D — *"Mechanized verification of replication safety properties
has a substantial prior literature, e.g.\ \cite{gomes2017verifyingsec}; the
property of interest in this paper is the single-writer authority invariant
rather than commutativity-based SEC."* — connects the contribution to the
lineage without overclaiming. Skip this if VI.D is already at length
budget.

---

### 2.4 Section II.C (Edge Computing and Intermittent Connectivity)

**Locate** the entire subsection.

**Why change it:** this subsection is the thinnest of the three and
currently cites only Wang/Kumbhar/Hoyhtya for general public-safety
comms, Zimbelman for the field-mesh measurement that motivates your
fault model, and CRIMP. The consensus report provides several
emergency-edge systems papers that share your problem space directly.
Citing zero of them is conspicuous.

**Recommended edit** — extend the subsection with a second paragraph
positioning the architecture against emergency-edge systems work
specifically:

> A growing line of work designs full edge/fog systems for emergency
> response. Sagor et al.'s DistressNet-NG \cite{sagor2024distressnetng}
> proposes a resilient data storage and sharing framework for mobile edge
> computing in cyber-physical systems; the tier structure overlaps with the
> present architecture but the framework does not impose a single-writer
> authority model for ordered command state. Tran and Kim
> \cite{tran2021ndn} build a Named Data Networking layer over edge
> infrastructure for disaster response, taking a content-centric rather
> than authority-centric position. Alwakeel \cite{alwakeel2025edgefog}
> reports adaptive edge-fog frameworks for emergency response with
> documented latency and reliability improvements over cloud-only models.
> Haroon et al. \cite{haroon2022edgecoord} examine edge coordination
> specifically in highly dynamic cyber-physical systems for emergency
> response. Li et al. \cite{li2017vehicleassist} use vehicles as resilient
> compute and routing nodes in disaster scenarios — adjacent to this
> paper's vehicle-edge tier, but without a command/responder split or an
> authoritative incident journal. Aboualola et al.
> \cite{aboualola2023edgesurvey} survey edge technologies for disaster
> management more broadly, and Sciullo et al.'s LOCATE
> \cite{sciullo2020locate} evaluates a LoRa-based mobile emergency
> management system. None of these works addresses the specific combination
> of an authoritative ordered incident journal, durable forward-only field
> submissions, and explicit manual command promotion that requirements
> R1--R3 demand.

**Optional rename:** consider renaming II.C from *"Edge Computing and
Intermittent Connectivity"* to *"Emergency-Response Edge Systems and
Intermittent Connectivity"* to reflect the expanded scope. Only do this if
it doesn't break a `\label`/`\ref` chain elsewhere.

---

### 2.5 Section VI (Evaluation) — Raft comparison framing

**Locate** the paragraph in Section VI.E that begins *"We do not present
Raft as a workflow-equivalent alternative."*

**Why change it:** the current text is honest about what the comparison
*isn't*, but never frames what the comparison *is*. The consensus literature
explicitly calls out the absence of head-to-head replication-design
comparisons in emergency-response settings as an open gap. Naming this
strengthens the contribution claim without overreach.

**Edit:** add the following sentence at the **end** of the existing paragraph
(after `...we leave to future work.`):

> Recent systematic reviews of offline-first emergency-response systems
> identify the absence of direct empirical comparisons between replication
> designs in disaster-relevant settings as an open gap
> \cite{aboualola2023edgesurvey}; the comparison reported here addresses
> that gap in emulation, with the field-realistic version remaining future
> work in line with the limitations stated in Section~\ref{sec:limits}.

Adjust label `\ref{sec:limits}` to your limitations-subsection label.

---

### 2.6 Section VII.B (Limitations) — minor

**Optional addition** to the existing limitations bullet list. Add at the
end:

> the comparison against alternative replication designs is currently a
> single Raft baseline; broader head-to-head evaluation against
> intermittent-connectivity-adapted consensus (e.g.\
> \cite{jahanian2022conice}) and CRDT-based emergency-management
> replication (e.g.\ \cite{hanssen2025emergency}) remains future work.

This converts a critique into a stated future-work hook and makes the
two new "competitor" citations earn their keep.

---

## 3. Changes I considered and rejected

For honesty / your reading: the consensus reports together contain roughly
65 distinct references. The following appeared but I did **not** include
them, with reasons.

### From the first consensus report

- **Zhang et al. 2025** (IoT public safety alerts), **Sakano et al. 2025**
  (portable edge for first responders), **Colosi et al. 2023**
  (EDGEmergency cloud-edge platform), **Wang et al. 2020** (edge
  intelligence for cognitive emergency networks): all reasonable papers,
  but adding more "edge-for-emergency" entries to II.C past the six already
  proposed is citation inflation. Pick at most one or two more if Section
  II.C is still felt to be thin after the edits in §2.4.
- **Khamaisi et al. 2025**, **Macaraeg et al. 2020** (LoRa mesh / off-grid
  comms): your fault model is justified by Zimbelman 2022 already, which
  is a stronger field-measurement paper than either of these. Don't dilute.
- **Tan et al. 2017** (mobile crisis informatics review): too old and too
  general for this paper's framing.
- **Kangana et al. 2025** (flood-app review), **Behrooz \& Ilbeigi 2024**
  (mobile localization), **Peng et al. 2025** / **Azfar et al. 2025**
  (UAV/AAV edge computing), **Altaweel et al. 2022** (RSock routing),
  **d'Oro et al. 2019** (modeling emergency edge), **Xu et al. 2023**
  (wireless distributed consensus for AVs): all tangential to the offline-
  first authority-bearing-state problem this paper actually solves.

### From the second consensus report

- **Davidson et al. 1985** (consistency in partitioned networks): **already
  cited as ref [29]** in the paper. No action needed.
- **Li 2017**, **Haroon 2022**: already proposed for inclusion above (§1
  and §2.4). The second report reinforces both as central, which is mild
  positive evidence for keeping them in.
- **Wang 2020**, **Zhang 2025**, **Peng 2025**: appeared in both reports
  but rejected in the first-report rationale above. Two AI-generated
  literature reviews citing the same tangential paper is not a strong
  signal — both reports hit similar topic queries and overlap is
  expected. Position unchanged.
- **Lohokare 2021**, **Hirushan 2022**, **Silva 2022**, **Sutradhar 2025**,
  **Cruz 2019**, **Xu 2020 (UAV-MEC)**, **C. 2019**, **Wang 2023**: all
  network-layer / connectivity / UAV work. The paper explicitly states
  *"the architectural contribution here is above the transport layer"*
  (Section II.C, last paragraph). Citing more transport-layer papers
  would muddy that scope claim.
- **Michael et al. 2017** ("Recovering Shared Objects Without Stable
  Storage"): interesting work on diskless crash-recovery, but the paper's
  storage model is durable Postgres with a forward-only outbox. The
  shared-objects-without-stable-storage problem is a different setting
  (in-memory replicated state machines without disks); the analogy
  doesn't carry usefully.

If a reviewer specifically asks for any of these, the bib entries are easy
to add later. Don't preemptively widen scope.

---

## 4. Sanity-check pass after edits

After applying all of §2 above, please:

1. Recompile the paper end-to-end and confirm no broken citations
   (`Citation 'xxx' undefined`) and no broken `\ref{}`s introduced by the
   inserted text.
2. Run `bibtool` or equivalent to detect duplicate keys, unused entries, and
   inconsistent author formatting.
3. Confirm the page count after the additions. Section II grows by roughly
   one paragraph in II.A, one sentence in II.B (Hanssen/Pothineni), one
   rewritten sentence in II.B (Gomes/Lewchenko verification lineage), and
   one paragraph in II.C; VI.E and VII.B each grow by one sentence-or-bullet,
   and VI.D optionally grows by one sentence. Estimated impact:
   approximately +0.7–0.9 pages depending on your IEEE template column-fill.
   If this pushes you over the page limit, the most compressible additions
   are (in order): the optional VI.D verification-lineage sentence (§2.3.1),
   the optional Lewchenko cite (§2.3.1), the optional limitations bullet in
   §2.6, the optional intro sentence in §2.1, and one or two of the
   lower-priority citations in the §2.4 paragraph (Sciullo, Aboualola
   survey can drop without losing the argument).
4. Re-check the `\cite{}` cluster ranges (`[14]--[16]`, `[18]--[21]`) in the
   intro paragraph, since adding `\cite{jahanian2022conice}` may shift the
   numbering of bracketed groups. Re-tighten any list ranges that no longer
   match.

---

## 5. Out of scope for this update

The consensus report does **not** provide material that affects:

- The TLA+ specification or property-test corpus.
- The implementation in the prototype repo (FastAPI, Kotlin, Compose,
  Docker, Ansible). No code changes flow from this update.
- The architectural design itself — the report validates the design space
  positioning, it does not suggest re-design.
- The Phase-2 / Phase-3 / Phase-4 evaluation methodology.

If you find yourself touching files outside `paper/` while applying this
update, stop and re-check — the change is bibliography + related work + a
few framing sentences, nothing more.
