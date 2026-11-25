# Makefile of the review export (copied to the export as Makefile).
# Every target fails with a nonzero status on any error.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PY := .venv/bin/python
RUFF := .venv/bin/ruff
SEED_PY := src/mandate sim experiments tests spec/tla/summarize.py paper/scripts/page_count.py
TLA_JAR := .tools/tla2tools-v1.7.4.jar
TLA_URL := https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
TLA_SHA256 := 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88

.PHONY: help venv lint test experiments seed tla-tools tla paper-anon

help:
	@echo "make venv | seed | lint | test | experiments | tla-tools | tla | paper-anon"

venv:
	python3 -m venv .venv
	.venv/bin/pip install --require-hashes -r requirements/seed.lock

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

paper-anon:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build -jobname=main-anon main-anon.tex
	$(PY) paper/scripts/page_count.py paper/build/main-anon --anonymous
