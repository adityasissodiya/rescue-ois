# Reference Material Checklist

- [ ] Working tree is clean before creating the reference-material archive.
- [ ] Archive excludes `.git/`, local remotes, branch names, and commit history.
- [ ] Archive excludes generated runtime outputs under `artifacts/`.
- [ ] Smoke run completed if a fresh wiring check is needed.
- [ ] Formal Python tests pass, with real-stack tests skipped unless explicitly enabled.
- [ ] TLA+ strict configs verify and weak configs fail with the expected counterexamples if TLC is rerun.
- [ ] Android/tablet package namespace remains neutral (`org.review.rescueois`).
