# Makefile — Green Capital Gap
# CLAUDE.md §11. Every stage is idempotent: it is gated on a stamp file whose
# prerequisites are the configs and source modules it actually depends on, so a
# re-run with unchanged inputs does no work. `make all` on a warm cache finishes
# in under three minutes.

# Prefer the project venv so the targets work without manual activation.
VENV    := .venv
PY      := $(shell [ -x $(VENV)/bin/python ] && echo $(VENV)/bin/python || echo python3)
PIP     := $(shell command -v uv >/dev/null 2>&1 && echo "uv pip" || echo "$(PY) -m pip")
# The kaggle CLI lives in the venv; put it on PATH for the ingest stage.
export PATH := $(CURDIR)/$(VENV)/bin:$(PATH)
STAMPS  := .stamps
CONFIGS := config/pipeline.yaml config/green_lexicon.yaml config/blocs.yaml

SRC_CORE    := src/gcg/config.py src/gcg/io.py
SRC_INGEST  := $(wildcard src/gcg/ingest/*.py)
SRC_CLASS   := $(wildcard src/gcg/classify/*.py)
SRC_TRANS   := $(wildcard src/gcg/transform/*.py)
SRC_ANALYSIS:= $(wildcard src/gcg/analysis/*.py)
SRC_VIZ     := $(wildcard src/gcg/viz/*.py)
SRC_REPORT  := $(wildcard src/gcg/report/*.py)

DEALS       := data/processed/deals.parquet
FINDINGS    := outputs/findings.json
REPORT_PDF  := report/report.pdf

.PHONY: all install data features analysis figures report test lint clean help
.DEFAULT_GOAL := help

help:
	@echo "Green Capital Gap — build targets"
	@echo "  make install    install dependencies (editable)"
	@echo "  make data       download + checksum + cache to data/raw, write MANIFEST"
	@echo "  make features   clean, classify, join, deflate -> $(DEALS)"
	@echo "  make analysis   H1-H5 + robustness -> outputs/tables, $(FINDINGS)"
	@echo "  make figures    render every figure -> outputs/figures"
	@echo "  make report     substitute placeholders, render -> $(REPORT_PDF)"
	@echo "  make test       pytest"
	@echo "  make lint       ruff check"
	@echo "  make all        data features analysis figures report"
	@echo "  make clean      wipe interim/processed/outputs/stamps, KEEP raw"

all: report

# ---------------------------------------------------------------------------
install: $(STAMPS)/install
$(STAMPS)/install: pyproject.toml
	@[ -d $(VENV) ] || uv venv --python 3.11 $(VENV)
	VIRTUAL_ENV=$(CURDIR)/$(VENV) $(PIP) install -e ".[dev,kaggle]"
	@mkdir -p $(STAMPS) && touch $@

# ---------------------------------------------------------------------------
# data — downloads are cached by SHA256 and never re-fetched. A checksum
# mismatch fails loudly. A missing dataset stops the build and asks the user;
# nothing is ever substituted or simulated (CLAUDE.md §2.1).
data: $(STAMPS)/data
$(STAMPS)/data: $(CONFIGS) $(SRC_CORE) $(SRC_INGEST)
	$(PY) -m gcg.ingest.run
	@mkdir -p $(STAMPS) && touch $@

# ---------------------------------------------------------------------------
features: $(DEALS)
$(DEALS): $(STAMPS)/data $(CONFIGS) $(SRC_CLASS) $(SRC_TRANS) | test-classifier
	$(PY) -m gcg.transform.deals

# The classifier must pass its tests before anything downstream runs
# (CLAUDE.md §6).
.PHONY: test-classifier
test-classifier:
	$(PY) -m pytest tests/test_green_classifier.py tests/test_blocs.py tests/test_deflate.py

# ---------------------------------------------------------------------------
analysis: $(FINDINGS)
$(FINDINGS): $(DEALS) $(CONFIGS) $(SRC_ANALYSIS) $(SRC_REPORT)
	$(PY) -m gcg.analysis.descriptives
	$(PY) -m gcg.analysis.run
	$(PY) -m gcg.analysis.robustness
	$(PY) -m gcg.report.findings

# ---------------------------------------------------------------------------
figures: $(STAMPS)/figures
$(STAMPS)/figures: $(FINDINGS) $(SRC_VIZ) $(CONFIGS)
	$(PY) -m gcg.viz.figures
	@mkdir -p $(STAMPS) && touch $@

# ---------------------------------------------------------------------------
# report — fails loudly on any unresolved {{placeholder}} (CLAUDE.md §2.2).
report: $(REPORT_PDF)
$(REPORT_PDF): $(FINDINGS) $(STAMPS)/figures report/report.md $(SRC_REPORT)
	$(PY) -m gcg.report.render

# ---------------------------------------------------------------------------
test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

# ---------------------------------------------------------------------------
# clean keeps data/raw so a rebuild does not re-download.
clean:
	rm -rf data/interim/* data/processed/* outputs/figures/* outputs/tables/* $(STAMPS)/*
	rm -f $(FINDINGS) $(REPORT_PDF) report/report.rendered.md logs/build.log
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	@touch data/interim/.gitkeep data/processed/.gitkeep \
	       outputs/figures/.gitkeep outputs/tables/.gitkeep $(STAMPS)/.gitkeep
	@echo "clean: interim, processed, outputs and stamps wiped. data/raw kept."
