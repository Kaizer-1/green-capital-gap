# CLAUDE.md — Green Capital Gap

> Build spec. Read this fully before writing any code. Read `docs/RESEARCH_BRIEF.md`
> before writing any prose for the report. Both are authoritative; where this file and
> your instincts disagree, this file wins.

---

## 0. What this is

An academic research project for a final-year Information Science chapter deliverable,
worth 40% of the module mark. It is graded by a human who will read the report and may
open the code.

**Theme:** Green Entrepreneurship, Emerging Economies
**Topic:** Open dataset analysis — green startup funding trends in emerging markets
**Stack:** Python (pandas) + open startup-funding datasets
**Deliverable:** a data-driven trend report with visualisations

**Working title:** *The Green Capital Gap: a deal-level analysis of cleantech venture
funding in emerging economies*

---

## 1. The single most important thing

A chart deck is not a finding. This project must produce **a falsifiable argument,
tested against data, with the tests reported honestly — including the ones that fail.**

### The thesis, revised at build step 3

The original thesis held that emerging-market green entrepreneurship operates under a
structurally different capital regime — later, thinner per deal, more non-dilutive, worse
at graduating, more cycle-exposed. **The data cannot carry that claim.** The in-window
emerging-market green sample is 35 deals across thirteen years, and widening the green
definition to its broadest admissible form does not change that: Tier A strict gives 29,
the headline 34, and Tier B with every veto removed also 34. Country recovery on the
blank-country bucket added one. The constraint is the record, not the classifier.

Per §15, the thesis therefore serves the data. The revised argument, reframed again at
build step 5 once the capital-intensity regression was run:

> Green entrepreneurship in emerging economies is subject to a **double gap** in the open
> venture record. First, emerging markets are under-represented in the record relative to
> their economic weight. Second, and separately, **conditional on a company already being
> in the record, an emerging-market company is markedly less likely to be green than an
> advanced-economy one** — 2.60% against 5.43%, a risk ratio of 0.48 [0.34, 0.67].
>
> **But the second gap is not green-specific. It is a capital-intensity gap.** Across 23
> sectors, a sector's emerging-market representation falls roughly in proportion to its
> capital intensity: the elasticity of the EM/AE representation ratio with respect to
> median advanced-economy deal size is **−1.19 [−1.64, −0.75]**, explaining 60% of the
> cross-sector variance. Biotech sits at 0.11 of proportionate representation, hardware at
> 0.31, enterprise at 0.34 — all below cleantech's 0.51. Emerging-market venture capital
> in 2000–2012 avoided capital-intensive, long-horizon, R&D-heavy sectors **as a class**,
> and concentrated in capital-light consumer internet: e-commerce at 3.4× proportionate,
> travel at 3.6×.
>
> Cleantech's residual from that fit is **positive** — 1.92× its predicted representation
> [0.75×, 4.91×] — though the interval includes 1. The data therefore cannot separate
> "green is exactly as under-represented as its capital intensity predicts" from "green is
> substantially better represented than its capital intensity predicts". What it **does**
> rule out is a green-specific *deficit*: after controlling for capital intensity there is
> no evidence that green was penalised beyond its capital needs, and the point estimate
> runs the other way, consistent with policy and development-finance pull creating demand
> that pure market logic would not.
>
> Together these mean the deal-level evidence required to study emerging-market green
> entrepreneurship does not exist in open data, and that absence is itself the finding —
> but the mechanism is the capital intensity of green technology meeting thin capital
> markets, not a green-specific aversion.

The first gap is the denominator check. **The second gap is the headline, and the
capital-intensity result is its qualifier.** Both belong on page one: putting the gap at
the front and its qualifier in an appendix is the same error as suppressing the gap.

The structural claims from the original thesis are not abandoned. They are tested where
the data has power — **green against non-green within advanced economies**, which is the
benchmark case for the capital-model mismatch that Gaddy et al. identify. Each then
carries an emerging-market arm reported as an explicitly bounded, underpowered probe with
every cell size printed and no significance test below n = 30.

Five hypotheses operationalise the revised claim (H1–H5 in `docs/RESEARCH_BRIEF.md` §4).
Every figure, table and paragraph must serve one of them, the methodology, or the
limitations. If something doesn't, delete it. A tight report beats a sprawling one.

**If a hypothesis fails to hold in the data, say so in the report and keep the test in.**
A null result that is honestly reported scores higher than a laundered one, and the
examiner will be checking for exactly this. H3's emerging-market arm is expected to come
back null; it stays in.

### The claim the absence does NOT license

A venture database indexes equity rounds. If emerging-market green capital ran
predominantly through grants, concessional debt and development-finance instruments —
and CPI puts roughly 29% of flows into its Emerging Markets grouping through concessional
loans and grants — then those ventures are **structurally unindexable here**, and their
absence is a property of the instrument, not of the entrepreneurship.

That mechanism is argued from external evidence. **It is not identified by this data and
must never be presented as though it were.** The competing explanation — that emerging
market ecosystems in 2000–2012 were genuinely less green — cannot be excluded with this
dataset. Both readings must appear in the discussion, and neither may be asserted as
established.

## 2. Non-negotiables

1. **No synthetic, simulated, fabricated or LLM-generated data. Ever.** If a dataset
   fails to download, stop and tell the user. Do not "generate a representative sample
   to demonstrate the pipeline". A single fabricated row destroys the project.
2. **No number is ever typed by hand into the report.** Every statistic in `report.md`
   is injected from `outputs/findings.json`, which is written by code. Enforce this
   with a placeholder syntax (`{{h1.em_dollar_share_2013}}`) and a renderer that fails
   loudly on an unresolved placeholder.
3. **Every figure is reproducible from `make all` on a clean checkout.** No manual steps,
   no notebook-only results, no hand-edited CSVs.
4. **Determinism.** Seed everything (`numpy`, `random`, any bootstrap). Same input →
   byte-identical output.
5. **Cite or delete.** Every factual claim in the report is either (a) computed by this
   pipeline and tagged with a figure/table ID, or (b) cited to a named source in
   `report/references.bib`. No orphan assertions.
6. **Document the data's weaknesses before the examiner finds them.** See §9.

---

## 3. Repository layout

```
green-capital-gap/
├── CLAUDE.md                  # this file
├── README.md                  # what it is, how to run it, what it found (write LAST)
├── Makefile                   # make data | features | analysis | figures | report | all
├── pyproject.toml             # deps + ruff + pytest config
├── .gitignore                 # data/raw/ and data/interim/ are ignored
├── config/
│   ├── pipeline.yaml          # paths, year windows, thresholds, seeds
│   ├── green_lexicon.yaml     # the green classifier — see §6
│   └── blocs.yaml             # country → bloc overrides and exceptions
├── data/
│   ├── raw/                   # untouched downloads (gitignored)
│   ├── interim/               # cleaned, not yet joined (gitignored)
│   ├── processed/             # analysis-ready parquet (committed if <50MB)
│   └── MANIFEST.md            # every source: URL, licence, SHA256, date, row count
├── src/gcg/
│   ├── config.py              # load pipeline.yaml, resolve paths, expose SEED
│   ├── io.py                  # read/write parquet, checksum, download-with-cache
│   ├── ingest/
│   │   ├── crunchbase.py      # the 2013 snapshot — relational + flat, joined
│   │   ├── india.py           # Indian startup funding 2015–2020
│   │   └── worldbank.py       # income groups, indicators, GDP deflator
│   ├── classify/
│   │   ├── green.py           # 3-tier green classifier + sub-domain tagging
│   │   └── blocs.py           # time-varying EM/AE/China/LDC assignment
│   ├── transform/
│   │   ├── deals.py           # the canonical deal-level fact table
│   │   └── deflate.py         # nominal → constant 2015 USD
│   ├── analysis/
│   │   ├── descriptives.py
│   │   ├── h1_share_and_size.py
│   │   ├── h2_cycle_amplification.py
│   │   ├── h3_instrument_mix.py
│   │   ├── h4_graduation.py
│   │   ├── h5_concentration.py
│   │   └── robustness.py      # re-runs H1–H5 under alternative definitions
│   ├── viz/
│   │   ├── theme.py           # the house style — see §8
│   │   └── figures.py         # one function per figure, named fig_01_* … fig_12_*
│   └── report/
│       ├── findings.py        # assembles outputs/findings.json
│       └── render.py          # placeholder substitution + md → pdf
├── tests/
│   ├── test_green_classifier.py
│   ├── test_blocs.py
│   ├── test_deflate.py
│   ├── test_deal_table.py
│   └── fixtures/              # tiny hand-built CSVs with KNOWN answers
├── outputs/
│   ├── figures/               # .png (300dpi) + .pdf for each figure
│   ├── tables/                # .csv + .tex for each table
│   └── findings.json
├── report/
│   ├── report.md              # the deliverable, with {{placeholders}}
│   ├── report.pdf             # rendered
│   └── references.bib
└── docs/
    ├── RESEARCH_BRIEF.md      # hypotheses, literature, report outline
    ├── DATA_SOURCES.md        # provenance and licensing
    ├── METHODOLOGY.md         # classifier + bloc assignment, written up properly
    └── LIMITATIONS.md         # threats to validity, written honestly
```

---

## 4. Data sources

Full detail in `docs/DATA_SOURCES.md` (you write that file). Summary of what to fetch:

### Primary — Crunchbase 2013 Snapshot (CC BY 4.0)
Two Kaggle datasets. **Use both and join them.**

**Corrected at build step 2:** these are NOT mirrors of the same snapshot. The relational
dump ends at `funded_at` 2013-12-12; the flat file extends to `last_funding_at` 2015-01-01
and is an early-2015 export. `funding_rounds.csv` holds 52,928 rounds (41,455 in the
2000-2012 window), not ~90,000. The flat file is used for its taxonomy only, never as a
funding source. See `outputs/tables/appendix_mirror_vintage.csv`.

| Handle | What it gives you |
|---|---|
| `justinas/startup-investments` | Relational: 11 CSVs. `funding_rounds.csv` is **deal-level** — `funded_at`, `raised_amount_usd`, `funding_round_type`, `funding_round_code`. `objects.csv` has `permalink`, `category_code`, `tag_list`, `country_code`, `founded_at`, `status`. |
| `arindam235/startup-investments-crunchbase` | Flat `investments_VC.csv`, 54k companies, with the **rich `category_list`** field (pipe-delimited, e.g. `Clean Energy\|Solar\|Renewables`) which the relational dump's coarse `category_code` lacks. |

**The join is the methodological trick that makes this project work.** `category_code`
alone gives you one blunt `cleantech` bucket. `category_list` gives you a usable green
taxonomy but has no deal dates. Join on `permalink` (normalise: lowercase, strip, drop
the `/organization/` or `/company/` prefix before comparing) to get **deal-level rows
carrying rich green labels**. Report the join rate in the methodology — expect high
80s–low 90s percent; investigate and document the non-matches rather than silently
dropping them.

```bash
pip install kaggle
kaggle datasets download -d justinas/startup-investments -p data/raw --unzip
kaggle datasets download -d arindam235/startup-investments-crunchbase -p data/raw --unzip
```

Fallback if the user has no Kaggle credentials — a public mirror of the flat file exists
in the `matthewquerdasi/Startups-Analysis` GitHub repo as `investments_VC.csv` (try both
`main` and `master` on `raw.githubusercontent.com`). **Ask the user before relying on a
mirror** and record which source you used in `data/MANIFEST.md`.

### Secondary — Indian startup funding, 2015–2020
`sudalairajkumar/indian-startup-funding`. Real, scraped deal records. Used for one thing
only: a **continuity probe** in §7 of the report, testing whether the structural pattern
found in 2005–2013 still shows up in a later window in one large emerging market. Do not
pool it with the Crunchbase data — the taxonomies and amount conventions are not
compatible. Keep it strictly as a separate, caveated section.

### Enrichment — all open, no auth required
- **World Bank income groups, time-varying:**
  `https://ourworldindata.org/grapher/world-bank-income-groups.csv?csvType=full`
- **World Bank country metadata** (region + current income level, ISO-3):
  `https://api.worldbank.org/v2/country?format=json&per_page=400`
- **World Bank indicators** (`https://api.worldbank.org/v2/country/all/indicator/{CODE}?format=json&per_page=20000&date=1995:2024`):
  - `NY.GDP.MKTP.CD` GDP, current USD
  - `NY.GDP.PCAP.CD` GDP per capita
  - `SP.POP.TOTL` population
  - `EG.ELC.ACCS.ZS` access to electricity, % of population
  - `EG.FEC.RNEW.ZS` renewable share of final energy consumption
  - `NY.GDP.DEFL.ZS` GDP deflator (use the USA series for the constant-USD conversion)
- **Our World in Data CO₂:**
  `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv`

Cache every download to `data/raw/` with its SHA256 recorded. Never re-download on a
re-run. Fail loudly on a checksum mismatch.

---

## 5. Country blocs

Defensible classification is worth marks. Do it properly.

- **Advanced Economies (AE)** — World Bank high-income
- **Emerging Markets (EM)** — upper-middle + lower-middle + low income, **excluding China
  and excluding LDCs**
- **China** — always reported separately. It dominates EM aggregates and hides everything
  else. This mirrors Climate Policy Initiative's own practice.
- **LDC** — reported separately where sample size allows, folded into a footnote where
  it doesn't.

**Time-varying assignment.** A deal in Poland in 2004 is not a deal in an advanced
economy; a deal in Poland in 2013 is. Use the historical OWID/World Bank income-group
series and assign each deal the bloc its country held **in the year the deal closed**.
Almost nobody does this; doing it is a genuine methodological contribution and must be
stated explicitly in the methodology section.

**Robustness:** re-run every headline result with (a) a static present-day classification
and (b) the MSCI Emerging Markets constituent list, and report whether conclusions change.
Put the comparison in an appendix table.

Country codes in Crunchbase are ISO-3 but with legacy quirks (`ROM` for Romania, `TMP`
for Timor-Leste, and blanks). Write an explicit override map in `config/blocs.yaml`,
test it, and log every code that fails to map rather than silently dropping it.

---

## 6. The green classifier

This is the methodological core. Build it as three tiers, keep them separable, and report
agreement between them.

**Tier A — strict.** `objects.category_code == 'cleantech'`.

**Tier B — lexicon.** Case-insensitive regex over the concatenation of `category_list`,
`tag_list` and `short_description`, driven entirely by `config/green_lexicon.yaml`. No
patterns hard-coded in Python. Map each hit to one of eleven sub-domains:

`solar` · `wind_hydro_geo` · `biofuels_biomass` · `energy_storage_battery` ·
`energy_efficiency_smart_grid` · `electric_mobility` · `water_sanitation` ·
`waste_recycling_circular` · `sustainable_agriculture` · `green_building_materials` ·
`environmental_monitoring_carbon`

**Tier C — exclusions.** Kill the false positives before they poison the sample. At
minimum: "cleaning" / "dry cleaning" / "cleaner" (services), "Green" as a surname or
place name, "Greenhouse" (the HR software), "greeting", "solaris"/"solarium", "wind" in
"window"/"windows", "waste" in "wasteland", "organic" in "organic search"/"organic
growth", "carbon" in "carbon copy"/"Carbonite", media and conference companies ("Greentech
Media", "Cleantech Group"). Use word boundaries. Manually eyeball the 150 highest-funded
Tier-B-only hits and record the exclusion decisions in `config/green_lexicon.yaml`
with a one-line reason each — this is defensible hand-curation, not slop, and the audit
trail is the point.

**Headline definition:** `green = TierA OR (TierB AND NOT TierC)`.

Report Cohen's κ between Tier A and Tier B. **Every headline result must be re-run under
Tier A alone (strict) as a robustness check** and the table placed in the appendix. If a
conclusion only survives under the broad definition, say so in the text.

Write `tests/test_green_classifier.py` with a hand-built fixture of ~40 companies with
known labels, including every nasty edge case above. The classifier must pass before
anything downstream runs.

---

## 7. Known data traps

These will cost you hours if you discover them late. They are real; handle each one and
write a line in `METHODOLOGY.md` about what you did.

**File-level**
- `investments_VC.csv` is **latin-1 / ISO-8859-1**, not UTF-8. `pd.read_csv(..., encoding='latin-1')`.
- Its **column names carry leading and trailing whitespace** (` market`, ` funding_total_usd `).
  Strip all column names on load, as a first step, always.
- `funding_total_usd` is a **string** with thousands separators and `-` for null.
  Clean with a dedicated coercion function, and log how many rows were coerced.

**Row-level**
- `raised_amount_usd` in `funding_rounds.csv` is **missing for a large minority of rows**
  (undisclosed deals). **Do not impute.** Report deal *counts* and deal *dollars* as two
  separate, independently-reported series throughout. Where you must use dollars, state
  the covered subsample size on the figure. This disclosure-bias split is itself one of
  the report's findings — undisclosed-amount rates differ systematically by bloc, so
  compute and report that rate by bloc and year.
- `funded_at` contains impossible dates (pre-1990, post-snapshot). Clip to the analysis
  window and log the count dropped.
- Round-type strings are inconsistent (`series-a`, `Series A`, `angel`, `seed`,
  `private-equity`, `post-ipo-equity`, `debt-financing`, `grant`, `venture`,
  `crowdfunding`, `other`). Normalise through an explicit mapping in
  `config/pipeline.yaml`, never a `.str.lower().str.replace()` chain scattered in code.
- Deduplicate on `(object_id, funded_at, funding_round_type, raised_amount_usd)`.
  Report the duplicate count.

**Window-level**
- **Right-censoring.** The snapshot's final months are incomplete — deals get recorded
  with a lag, so 2013 and any 2014 rows look like a crash that is actually a reporting
  artefact. **Truncate the analysis window at 2012-12-31** and state why. Then, separately,
  plot the raw uncensored tail in one small figure labelled as an artefact, to prove you
  understood it. Examiners love this.
- Start the window at **2000-01-01**; pre-2000 coverage is too thin and the dot-com
  distortion is irrelevant to the argument.

**Comparability**
- **Deflate.** Comparing $2004 with $2012 unadjusted is a basic error. Convert all
  amounts to **constant 2015 USD** using the US GDP deflator. Keep the nominal column
  alongside and name both unambiguously (`amount_usd_nominal`, `amount_usd_real2015`).
- Deal sizes are **heavy-tailed and log-normal-ish**. Report medians and IQRs, not bare
  means. Where a mean is reported, report the median next to it. Use log scales on
  distribution plots and say so in the axis label.

**Coverage bias — the big one**
- Crunchbase 2013 systematically under-covers non-US, non-English-language ecosystems.
  This **inflates the AE share** and is the single biggest threat to validity. It must be
  (a) stated prominently in `LIMITATIONS.md` and in the report's methodology section,
  (b) partially mitigated by leaning on *within-bloc* comparisons (green vs non-green
  inside EM) and *ratios* rather than absolute EM-vs-AE levels, and (c) probed
  empirically: compute EM coverage as a share of deals vs. EM share of world GDP in the
  same year and show the gap. A measurable bias you quantified beats a bias you
  disclaimed.

---

## 8. Visualisation standards

Default matplotlib output reads as unfinished work. Build a house style in
`src/gcg/viz/theme.py` and apply it via a single `apply_theme()` called once.

**Palette** — considered, not rainbow:
```
ink          #141413     text, axis labels
ink_muted    #6E6E68     secondary text, source lines
rule         #E3E1DA     gridlines
canvas       #FFFFFF     figure background (print-safe)
em           #0E7C7B     Emerging Markets        (deep teal)
ae           #B5651D     Advanced Economies      (burnt ochre)
china        #4A4A52     China                   (graphite)
ldc          #9C7B9B     LDCs                    (muted plum)
accent_green #3F7D3F     green/cleantech series
accent_grey  #A8A69E     non-green comparison series
alert        #B03A2E     annotations, callouts
```
Sub-domain charts use a single-hue sequential ramp off `em`, never a categorical rainbow.

**Typography** — serif titles, sans labels, with graceful degradation. Try in order:
titles `["Source Serif 4", "Charter", "Georgia", "DejaVu Serif"]`, body
`["Inter", "Source Sans 3", "Helvetica Neue", "DejaVu Sans"]`. Write a
`_resolve_font()` helper that checks `matplotlib.font_manager` and falls back silently.
Never let a missing font crash the build or emit tofu boxes.

**Every figure, without exception:**
- Title is a **sentence that states the finding**, not a label.
  Yes: *"Emerging markets gained deal share but not dollar share."*
  No: *"Figure 4: Funding by region over time."*
- A one-line subtitle giving the unit and window.
- A footer line, 7pt, `ink_muted`: `Source: Crunchbase 2013 Snapshot (CC BY 4.0); author's
  calculations. n = X deals, 2000–2012, constant 2015 USD.`
- No top or right spine. Horizontal gridlines only, `rule`, behind the data, linewidth 0.6.
- **Direct labelling at the series terminus instead of a legend** wherever ≤5 series.
- Saved at 300 dpi as both `.png` and `.pdf`, figsize `(7.2, 4.4)` for single-column and
  `(7.2, 8.0)` for a stacked pair.
- Deterministic filename: `fig_03_em_share_divergence.png`.

**Banned outright:** pie charts, donut charts, 3-D anything, dual y-axes, rainbow/jet
colormaps, gradient fills, drop shadows, emoji, truncated y-axes without an explicit
break marker, more than seven categorical colours in one chart, chartjunk backgrounds.

**Required annotation layer.** At least three figures must carry an inline text callout
with a thin leader line marking a real event — the 2008 crisis, the 2011–12 cleantech
bust, the right-censoring boundary. A chart that makes the reader find the story is a
chart that failed.

---

## 9. Statistical standards

- **Bootstrap** (10,000 resamples, seeded) for CIs on medians and shares. Report CIs,
  not just point estimates.
- **Mann–Whitney U** for deal-size distribution comparisons across blocs — the data is
  not normal, do not reach for a t-test.
- **Difference-in-differences** for H2: outcome = log deal volume; treatment = green ×
  EM; event = post-2008. Report the interaction coefficient with robust SEs. State the
  parallel-trends assumption and show the pre-trend plot. If parallel trends fails,
  **say so** and downgrade the claim to descriptive.
- **Logistic regression** for H4 graduation, with year fixed effects and sub-domain
  controls. Report odds ratios with CIs, and the n in each cell.
- **Spearman rank correlation** for H5 — relationships here are monotone, not linear.
- **Benjamini–Hochberg** correction across the full family of tests. Report both raw and
  adjusted p-values in the appendix table.
- Report **effect sizes alongside p-values**, always. With ~41k in-window deals almost
  everything is "significant"; the question is whether it matters.
- Any cell with n < 30 gets suppressed or explicitly flagged on the figure.

---

## 10. Writing standards for the report

Target 3,500–4,500 words plus figures, tables, references and appendices.

**Voice:** plain academic English. Short declarative sentences. Active voice. The reader
is a competent examiner who is bored of padding.

**Banned phrases and constructions** — a non-exhaustive blacklist. Grep for these before
submitting and rewrite every hit:

> delve · landscape (figurative) · underscore(s) · it is worth noting · it's important
> to note · in today's rapidly evolving · navigate the complexities · a testament to ·
> tapestry · realm · pivotal · crucial (as filler) · leverage (as a verb) · robust (as
> filler) · holistic · paradigm shift · game-changer · unlock the potential · at the
> intersection of · shed light on · paving the way · the findings suggest that it may be
> possible that · Moreover, · Furthermore, · Additionally, (as paragraph openers) ·
> "Not only X, but Y" · "It's not just X — it's Y" · rhetorical-question openers

Also: no em-dash-heavy prose (cap at roughly one per 300 words), no three-item lists
where two items would do, no sentence that could be deleted without losing information,
no paragraph that opens by restating the section heading.

**Structure discipline:**
- Open the Results section with the finding, then the evidence. Never build suspense.
- Every figure is referenced in the text by number before it appears, and the text says
  what the figure shows rather than inviting the reader to interpret it.
- Each hypothesis section ends with an explicit one-line verdict:
  **Supported / Partially supported / Not supported**, and a sentence on what would
  falsify it.
- The Limitations section is written to be read by a hostile examiner looking for the
  weakness you missed. Find it first.

**The report must include** a Reproducibility Statement: commit hash, Python version,
dataset SHA256s, `make all` runtime, and a one-line statement of what a reader needs to
reproduce every number.

---

## 11. Build pipeline

```make
make install    # uv/pip install, pre-commit
make data       # download + checksum + cache to data/raw
make features   # clean, classify, join, deflate → data/processed/deals.parquet
make analysis   # run H1–H5 + robustness → outputs/tables/*.csv, outputs/findings.json
make figures    # render all figures → outputs/figures/
make report     # substitute placeholders, render report.md → report.pdf
make test       # pytest
make all        # data features analysis figures report
make clean      # wipe interim/processed/outputs, keep raw
```

Each stage is idempotent and skips work whose inputs are unchanged (compare input
checksums against a `.stamp` file). `make all` on a warm cache should finish in under
three minutes.

Logging: `structlog` or stdlib `logging` to both console and `logs/build.log`. Every
stage logs rows in, rows out, rows dropped and why. The drop ledger goes into the
methodology appendix as a table — a transparent attrition table is one of the clearest
quality signals a marker can see.

---

## 12. Code standards

- Python 3.11+. `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `pyyaml`,
  `requests`, `pyarrow`, `pytest`, `ruff`. Nothing exotic. **Not** seaborn — the house
  theme is explicit and seaborn's defaults fight it.
- Type hints on every public function. Docstrings in NumPy style on anything non-obvious.
- No magic numbers in code. Thresholds, windows, seeds all live in `config/pipeline.yaml`.
- No chained-indexing assignment. No `inplace=True`. No `SettingWithCopyWarning` left
  unresolved — treat warnings as errors in CI.
- Functions do one thing. If an analysis function exceeds ~50 lines, split it.
- Every `analysis/h*_*.py` module exposes `run(deals: pd.DataFrame, cfg: Config) -> dict`
  returning a JSON-serialisable findings dict. `findings.py` merges them. This is what
  makes rule §2.2 enforceable.

---

## 13. Build order

Do not jump ahead. Each step is verifiable.

1. Scaffold repo, `pyproject.toml`, `Makefile`, config files, `.gitignore`.
2. `io.py` + `ingest/` — download, checksum, cache, write `data/MANIFEST.md`.
   **Print row counts and the head of each table. Stop and show the user.**
3. `classify/green.py` + its tests. **Show the user the classification counts, the κ
   between tiers, and the top 30 Tier-B-only companies by funding so they can sanity-check
   the lexicon.** Do not proceed until this looks right.
4. `classify/blocs.py` + tests. Show the unmapped-country log.
5. `transform/deals.py` — build and persist the canonical deal table. Show the attrition
   ledger.
6. `viz/theme.py` + **one** figure. Show it. Get the look agreed before building eleven more.
7. `analysis/` H1–H5, one module at a time, each printing its findings dict.
8. `robustness.py`.
9. Remaining figures.
10. `report/findings.py` + `render.py`.
11. `report/report.md` — written against `docs/RESEARCH_BRIEF.md` §7 outline, with
    placeholders only.
12. `docs/METHODOLOGY.md`, `docs/LIMITATIONS.md`, `docs/DATA_SOURCES.md`.
13. `README.md` last, written once you know what the project actually found.
14. Full `make clean && make all` from scratch. Verify zero unresolved placeholders,
    zero missing figures, zero test failures.

At steps 2, 3, 5 and 6 **stop and report to the user** rather than barrelling on. Those
are the four points where a silent wrong turn is expensive to undo.

---

## 14. Done means

- [ ] `make clean && make all` succeeds from scratch, no manual steps
- [ ] `pytest` green, classifier and bloc tests included
- [ ] Zero unresolved `{{placeholders}}` in `report.pdf`
- [ ] Every figure has a finding-sentence title, a source footer and an n
- [ ] Every one of H1–H5 has an explicit verdict, including any that failed
- [ ] Robustness appendix present: strict vs broad green, static vs time-varying blocs
- [ ] Attrition ledger present, drop reasons itemised
- [ ] `LIMITATIONS.md` names the Crunchbase coverage bias and the 2012 truncation first,
      not buried at the end
- [ ] Blacklist grep (§10) returns zero hits in `report.md`
- [ ] `references.bib` complete, every in-text citation resolves
- [ ] README states the three headline findings in plain sentences

---

## 15. If something blocks you

Stop and ask. Specifically:
- A dataset won't download → ask. Never substitute or simulate.
- A hypothesis has insufficient n → report it as underpowered. Never widen the definition
  until it becomes significant.
- A result contradicts the thesis in §1 → **report the contradiction and revise the
  thesis.** The thesis serves the data, not the other way round. This is the single most
  important line in this file.