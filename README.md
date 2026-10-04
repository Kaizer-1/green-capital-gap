# The Green Capital Gap

A deal-level analysis of cleantech venture funding in emerging economies, 2000–2012.

Final-year chapter deliverable, Department of Information Science & Engineering,
RV College of Engineering. Authors and guide are listed in
[`report/metadata.yaml`](report/metadata.yaml), which is the single source of truth for
them: the title page, the report's reproducibility statement and this README all read from
that file rather than restating it.

The deliverable is **[`report/report.pdf`](report/report.pdf)**, built by `make all`.

There is also a web edition of the argument, with the figures drawn in the browser and
every statistic injected from the same `findings.json` the report reads:
**<https://kaizer-1.github.io/green-capital-gap/>**. It is built by `make web` and
published by `make web-publish`; if it ever disagrees with the PDF on a number, the build
is broken. Its source is in [`web/`](web/).

---

## What it found

**1. Emerging markets are a fiftieth of the open venture record and a fifth of world GDP.**
Over the window they hold 15.3–22.7% of world GDP against 1.7–6.4% of recorded venture
deals. This is the denominator check, and it is the reason the headline is measured inside
the dataset rather than against the world.

**2. Conditional on a company already being in the record, an emerging-market company is
half as likely to be green.** 2.60% against 5.43%, a risk ratio of 0.479 [0.343, 0.669]
across 41,105 funding rounds. The gap survives every green definition, every bloc scheme,
and a permutation test in which no label shuffle reaches the observed value.

**3. That gap is not green-specific — it is a capital-intensity gap.** Across 23 sectors,
emerging-market representation falls roughly in proportion to capital intensity, with an
elasticity of −1.19 [−1.64, −0.75] explaining 60% of cross-sector variance. Biotech sits
further below proportionate representation than cleantech does. Cleantech's residual from
that fit is *positive* at 1.92× [0.75×, 4.91×], so a green-specific penalty is ruled out
while outperformance is not confirmed.

**And the finding the project is actually entitled to make:** the structural questions the
field asks about emerging-market green capital **cannot be answered from open data**. Five
pre-registered hypotheses were specified before the data was examined. Two returned usable
answers within advanced economies; three could not be resolved, each for a different and
independently verifiable reason. Three further measurement failures arise from the
record's own structure. Six independent routes, one conclusion.

| Hypothesis | Verdict |
|---|---|
| H1 — the double gap | Supported |
| H2 — cycle amplification | Not testable — identifying assumption failed |
| H3 — instrument mix | Supported for the advanced-economy benchmark case |
| H4 — graduation | Underpowered — cannot determine |
| H5 — allocation | Partially supported |

The emerging-market green sample is **34 deals across thirteen years**. That is the
constraint, and it is the result.

---

## Running it

Requires Python 3.11+, [`uv`](https://docs.astral.sh/uv/), `pandoc` and `typst`
(`brew install pandoc typst`), and Kaggle API credentials for the two primary datasets.

```bash
make install     # uv venv + editable install
make all         # data → features → analysis → figures → report
```

`make all` on a warm cache takes about 95 seconds and rebuilds every number, every figure
and the PDF from scratch. Individual stages:

```bash
make data        # download, checksum, cache to data/raw, write data/MANIFEST.md
make features    # clean, classify, assign blocs, deflate → data/processed/deals.parquet
make analysis    # H1–H5 + robustness → outputs/tables, outputs/findings.json
make figures     # 14 figures, screen and print variants → outputs/figures
make report      # resolve placeholders, run the gates, render → report/report.pdf
make test        # pytest
make lint        # ruff
make clean       # wipe interim/processed/outputs/stamps, KEEP data/raw
```

Downloads are cached by SHA256 and never re-fetched; a checksum mismatch fails the build.
If a dataset will not download the build stops and says so. Nothing is ever substituted or
simulated.

---

## How the no-typed-numbers rule is enforced

Every statistic in the report is a `{{placeholder}}` resolved from
`outputs/findings.json`, which is written by code. `make report` runs eight gates and each
one fails the build rather than warning:

1. **Unresolved placeholders** — a report that renders with a literal `{{h1.rr}}` is worse
   than one that does not render, because the first can be submitted.
2. **Banned phrases** — the writing blacklist in `CLAUDE.md` §10.
3. **Typography** — primes used as apostrophes, ASCII `x` as a multiplication sign,
   hyphen-minus as a minus sign.
4. **Stale numbers** — any bare number in the prose that is not a value in
   `findings.json`, not a year, a section reference or a small cardinal, and not inside a
   sentence carrying a citation. This exists because the placeholder gate cannot see a
   number that was never a placeholder, which is how a stale "26 of the 28" survived
   beside a figure caption that said 23 of 27.
5. **Figure numbers** — the same membership check applied to every string drawn into a
   figure. Figure text is composed in Python and rasterised into a PDF before the renderer
   runs, so no other gate can see it; that is how a hand-typed `2` reached a published
   figure, and how one figure came to print a bootstrap interval that disagreed with the
   sentence beside it.
6. **Print chrome** — a print-variant figure that still carries its own caption's finding
   sentence would show the reader that sentence twice.
7. **Figure alignment** — every print variant's ink must reach its canvas edges, and the
   canvas must match the template's text column, so figures are never silently rescaled
   and all share one left edge with the captions.
8. **PDF smoke test** on the rendered document's extracted text.

Figure captions go through the same placeholder resolution as the prose, and the text
inside the figures goes through the same number check, so neither can quote a stale number.

---

## Layout

```
config/         pipeline.yaml, green_lexicon.yaml, blocs.yaml, audit_calls.yaml
data/           raw (gitignored), interim, processed, MANIFEST.md
src/gcg/
  ingest/       download, checksum, cache, pre-analysis diagnostics
  classify/     three-tier green classifier, time-varying bloc assignment
  transform/    canonical deal table, deflation, attrition ledger
  analysis/     H1–H5, capital intensity, cheque size, audit symmetry, robustness
  viz/          house style, flush-fit layout, print variants, 14 figures
  report/       findings assembly, placeholder resolution, gates, Typst render
tests/          classifier, blocs, deflate, deal table, rounding
outputs/        figures, tables, findings.json
report/         report.md, metadata.yaml, template.typ, references.bib, report.pdf
docs/           RESEARCH_BRIEF.md, METHODOLOGY.md, DATA_SOURCES.md, LIMITATIONS.md
```

Three methodological choices are worth naming:

- **Blocs are time-varying.** A deal takes the income group its country held in the year
  the deal closed, so a 2004 Polish deal is emerging-market and a 2013 Polish deal is not.
- **Instruments are normalised from `funding_round_code`, not `funding_round_type`.** The
  latter files seed under `angel` and both grant and debt under `other`, which would have
  made the graduation funnel unmeasurable and the non-dilutive share invisible, without
  raising an error.
- **Country recovery refuses vanity domains by name.** `.tv`, `.io`, `.me`, `.ly` and `.st`
  are sold worldwide; accepting them would have manufactured hundreds of companies in
  exactly the countries this project reports as absent.

---

## Reading further

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — classifier, blocs, pre-commitments, the
  corrections made during the build and what each one cost
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — provenance, licensing, and the traps in
  each source
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — threats to validity, worst first
- [`docs/RESEARCH_BRIEF.md`](docs/RESEARCH_BRIEF.md) — hypotheses, literature, report
  outline

---

## Reproducibility

Python 3.11.9, seed 20251001, bootstraps at 10,000 draws. All 12 source files carry
recorded SHA256 checksums, verified on every run. `make clean && make all` rebuilds
everything from `data/raw` with no manual steps.

Primary data is the Crunchbase 2013 Snapshot (CC BY 4.0); enrichment is World Bank and Our
World in Data (CC BY 4.0); the continuity probe uses a Kaggle scrape of Indian startup
funding. Full detail in `data/MANIFEST.md` and `docs/DATA_SOURCES.md`.
