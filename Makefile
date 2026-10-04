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

PREDIAG     := data/interim/preanalysis_diagnostics.json
LABELS      := data/interim/green_labels.parquet
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
	@echo "  make web        export series, run checks + screenshot capture"
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

# The classifier runs as its own target. It used to be left implicit, so a warm
# tree built and a clean one did not: `make clean && make all` failed looking
# for green_labels.parquet, which nothing in the graph produced.
# Pre-analysis diagnostics (sentinel sweep, censoring, FX, mirror vintage) run
# against the ingested tables and are consumed by findings.py. Same defect as
# the classifier: implicit in a warm tree, absent from a clean one.
$(PREDIAG): $(STAMPS)/data $(CONFIGS) $(SRC_INGEST)
	$(PY) -m gcg.ingest.diagnostics

$(LABELS): $(STAMPS)/data $(CONFIGS) $(SRC_CLASS) | test-classifier
	$(PY) -m gcg.classify.run

$(DEALS): $(LABELS) $(CONFIGS) $(SRC_CLASS) $(SRC_TRANS)
	$(PY) -m gcg.transform.deals

# The classifier must pass its tests before anything downstream runs
# (CLAUDE.md §6).
.PHONY: test-classifier
test-classifier:
	$(PY) -m pytest tests/test_green_classifier.py tests/test_blocs.py tests/test_deflate.py

# ---------------------------------------------------------------------------
analysis: $(FINDINGS)
$(FINDINGS): $(DEALS) $(PREDIAG) $(CONFIGS) $(SRC_ANALYSIS) $(SRC_REPORT)
	$(PY) -m gcg.analysis.descriptives
	$(PY) -m gcg.analysis.run
	$(PY) -m gcg.analysis.robustness
	$(PY) -m gcg.report.findings

# ---------------------------------------------------------------------------
figures: $(STAMPS)/figures
# Builds BOTH variants: screen exhibits to outputs/figures/, print variants to
# outputs/figures/print/. The report embeds only the print variants.
$(STAMPS)/figures: $(FINDINGS) $(SRC_VIZ) $(CONFIGS)
	$(PY) -m gcg.viz.figures
	@mkdir -p $(STAMPS) && touch $@

# ---------------------------------------------------------------------------
# web — the portfolio edition. Reads the same findings.json the report reads, so
# the two cannot disagree about a number. report.pdf does not depend on any of
# this, and `make all` does not build it.
WEB_DATA := web/data/series.json
SRC_WEB  := $(wildcard src/gcg/web/*.py)

.PHONY: web web-data web-test web-deploy web-deploy-check

# The PDF is served from the page's own directory rather than linked as
# ../report/report.pdf. That path works from a local server rooted at web/ and
# breaks on Pages, where the site is rooted at /<repo>/ and ../ escapes it.
# Copying it keeps one relative link that is correct in both places.
web/report.pdf: $(REPORT_PDF)
	cp $< $@

web-data: $(WEB_DATA)
$(WEB_DATA): $(FINDINGS) $(DEALS) $(SRC_WEB) $(CONFIGS) web/index.html
	$(PY) -m gcg.web.export_series
	$(PY) -m gcg.web.inject

web-test: $(WEB_DATA) web/report.pdf
	cd web && node test/checks.mjs && node test/capture.mjs

web: web-data web-test

# ---------------------------------------------------------------------------
# deploy — GitHub Pages, served from docs/ on main.
#
# docs/ rather than a gh-pages branch: Pages serves it with no branch to keep in
# step, the deployed files are reviewable in the same history as the code that
# produced them, and an examiner opening the repo can see exactly what is
# published. The cost is build output in main, which for a deliverable is a
# feature.
#
# Nothing here is copied by hand. A deploy step outside the Makefile drifts from
# the build, and this one is reproduced by `make web-deploy` from a clean tree.
DOCS := docs

web-deploy: web
	rm -rf $(DOCS)
	mkdir -p $(DOCS)
	# Everything the page needs, and nothing it does not: no test harness, no
	# node_modules, no screenshots.
	cd web && tar cf - index.html report.pdf css js data | (cd ../$(DOCS) && tar xf -)
	# Jekyll silently drops any path beginning with an underscore. The page has
	# none today; .nojekyll means it never has to.
	touch $(DOCS)/.nojekyll
	$(PY) -m gcg.web.deploy_check $(DOCS)
	@echo "docs/ built — commit it and set Pages to 'main /docs'"

# Serves docs/ under a sub-path, the way Pages serves /<repo>/, and runs the
# full check suite against it. This is the test that catches the two things
# that break on Pages and never locally: a path that resolves at the server
# root but not under a prefix, and a filename whose case differs from what is
# on disk (Pages is case-sensitive, macOS is not).
web-deploy-check: web-deploy
	cd web && node test/deployed.mjs ../$(DOCS)

# ---------------------------------------------------------------------------
# report — fails loudly on any unresolved {{placeholder}} (CLAUDE.md §2.2).
report: $(REPORT_PDF)
$(REPORT_PDF): $(FINDINGS) $(STAMPS)/figures report/report.md report/template.typ \
                report/metadata.yaml $(SRC_REPORT)
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
