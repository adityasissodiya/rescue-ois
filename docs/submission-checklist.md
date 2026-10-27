# Reference Material Checklist

> **Historical.** Written for the anonymized archive of a double-blind submission of
> the prototype paper. The paper drafts now name their authors; reuse this only if a
> venue asks for an anonymized artifact again.

- [ ] Working tree is clean before creating the reference-material archive.
- [ ] Archive excludes `.git/`, local remotes, branch names, and commit history.
- [ ] Archive excludes generated runtime outputs under `artifacts/`.
- [ ] Smoke run completed if a fresh wiring check is needed.
- [ ] Formal Python tests pass, with real-stack tests skipped unless explicitly enabled.
- [ ] TLA+ strict configs verify and weak configs fail with the expected counterexamples if TLC is rerun.
- [ ] Android/tablet package namespace remains neutral (`org.review.rescueois`).
