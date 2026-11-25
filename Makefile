# Commands for the SRDS seed (spec/, src/mandate/, sim/, experiments/, tests/, paper/).
# The legacy prototype and testbed keep their own commands (README.md); nothing here runs
# Docker or the legacy harnesses. Every target fails with a nonzero status on any error.
# Paths are relative, so the repository may live in a directory whose name has spaces.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PY := .venv/bin/python
RUFF := .venv/bin/ruff
SEED_PY := src/mandate sim experiments tests spec/tla/summarize.py paper/scripts/page_count.py artifact/check_export.py
TLA_JAR := .tools/tla2tools-v1.7.4.jar
TLA_URL := https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
TLA_SHA256 := 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
LATEXMK := latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build

.PHONY: help venv lint test experiments seed tla-tools tla paper paper-anon export review-diff

help:
	@echo "make venv         create .venv from requirements/seed.lock (hash-checked)"
	@echo "make seed         lint + tests + all directed scenarios (writes experiments/results, paper/generated)"
	@echo "make lint | test | experiments   the parts of 'make seed'"
	@echo "make tla-tools    download the pinned TLA+ tools jar into .tools/"
	@echo "make tla          optional: bounded TLA+ model (9 to 14 minutes in our runs), logs and paper macros"
	@echo "make paper        author PDF (paper/build/main.pdf) and its main-text page count"
	@echo "make paper-anon   review PDF (paper/build/main-anon.pdf), metadata checked"
	@echo "make export       review export in artifact/out/ (allowlisted, anonymized, checked)"
	@echo "make review-diff  every change against the private pre-seed baseline ref"

venv:
	if command -v uv >/dev/null; then \
	  uv venv --allow-existing .venv --python 3.12 && \
	  uv pip install --python .venv/bin/python --require-hashes -r requirements/seed.lock; \
	else \
	  python3 -m venv .venv && \
	  .venv/bin/pip install --require-hashes -r requirements/seed.lock; \
	fi

lint:
	$(RUFF) check --config ruff-seed.toml $(SEED_PY)
	$(RUFF) format --check --config ruff-seed.toml $(SEED_PY)

test:
	$(PY) -m pytest -c tests/pytest.ini tests

experiments:
	PYTHONPATH=src:. $(PY) -m experiments.run

seed: lint test experiments

tla-tools: $(TLA_JAR)

$(TLA_JAR):
	mkdir -p .tools
	curl -fsSL -o "$@.part" "$(TLA_URL)"
	echo "$(TLA_SHA256)  $@.part" | sha256sum --check --quiet -
	mv "$@.part" "$@"

tla: $(TLA_JAR)
	spec/tla/run_tlc.sh
	$(PY) spec/tla/summarize.py

paper:
	cd paper && $(LATEXMK) main.tex
	$(PY) paper/scripts/page_count.py paper/build/main

paper-anon:
	cd paper && $(LATEXMK) -jobname=main-anon main-anon.tex
	$(PY) paper/scripts/page_count.py paper/build/main-anon --anonymous

export: paper-anon
	artifact/export_review.sh

review-diff:
	artifact/review_diff.sh
