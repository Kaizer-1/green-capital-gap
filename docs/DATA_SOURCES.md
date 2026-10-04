# Data sources

Provenance, licensing, and what each source can and cannot support.

`data/MANIFEST.md` is the machine-generated companion to this file: it records the exact
file, row count, size and SHA256 of every download, and is rewritten by `make data`. This
file is the human one. Where they disagree, the manifest is right about *what was
fetched* and this file is right about *why*.

Nothing here is downloaded more than once. Every file is cached in `data/raw/` with its
checksum in `data/raw/_checksums.json`, verified on each run; a mismatch fails the build
rather than silently changing a result. No source is substituted, mirrored from an
unrecorded location, or simulated.

---

## 1. Crunchbase 2013 Snapshot — primary

**Licence:** CC BY 4.0. **Obtained via:** two Kaggle mirrors.

| Mirror | Kaggle handle | What it supplies |
|---|---|---|
| Relational | `justinas/startup-investments` | `funding_rounds.csv` (deal-level: `funded_at`, `raised_amount_usd`, `funding_round_type`, `funding_round_code`) and `objects.csv` (`permalink`, `category_code`, `tag_list`, `country_code`, `founded_at`, `status`, `short_description`) |
| Flat | `arindam235/startup-investments-crunchbase` | `investments_VC.csv`, whose pipe-delimited `category_list` field carries the green taxonomy the relational dump's single-value `category_code` cannot |

### The join

The relational dump has dates but a blunt taxonomy; the flat file has a usable taxonomy
but no dates. Joining them on a normalised permalink (lowercased, trimmed, with any
`/organization/` or `/company/` prefix removed) produces deal-level rows carrying rich
green labels. That join is what makes the three-tier classifier possible, and the join
rates are reported in the report's §3 and in `outputs/tables/`.

### They are not the same vintage

This is the single most important caveat about the primary source, and the project
documentation originally assumed the opposite. The relational dump's last `funded_at` is
**2013-12-12**; the flat file's last `last_funding_at` is **2015-01-01**, making it an
early-2015 export. Thousands of companies appear in the flat file with funding the
relational dump does not record.

Consequences, all of which are implemented rather than merely noted:

- The flat file is used for its **taxonomy only**, never as a funding source.
- The gap is quantified rather than waved at:
  `outputs/tables/appendix_mirror_vintage.csv` reports the implied under-recording, which
  the report quotes in §3 and Appendix H.
- Because the deal-level data stops in 2013 and the analysis window closes at 2012-12-31,
  the vintage difference does not reach the headline result.

### What it under-covers

Crunchbase 2013 systematically under-covers non-US, non-English-language ecosystems. This
is the largest threat to validity in the project and is treated at length in
`docs/LIMITATIONS.md`. It is the reason the headline result is a comparison *within* the
dataset, conditional on a company already being indexed, rather than a comparison of
blocs against the world.

### File-level traps, all handled in `src/gcg/ingest/crunchbase.py`

- `investments_VC.csv` is **latin-1**, not UTF-8.
- Its column names carry leading and trailing whitespace (`" market"`,
  `" funding_total_usd "`). All column names are stripped on load, as the first step.
- `funding_total_usd` is a string with thousands separators and `-` for null.
- `raised_amount_usd` encodes undisclosed amounts as a literal `0.0` in several thousand
  rows. These are nulled, never imputed, after a sweep confirmed no other sentinel was in
  use. Deal counts and deal dollars are reported as separate series throughout as a
  result.
- `funded_at` contains impossible dates; the analysis window clips them and the count is
  recorded in the attrition ledger.
- `funding_round_type` and `funding_round_code` disagree on roughly a third of rows. The
  project normalises from **`funding_round_code`**. See §5 below.

---

## 2. Indian startup funding, 2015–2020 — secondary

**Kaggle handle:** `sudalairajkumar/indian-startup-funding`. **Licence:** see the Kaggle
page (CC0 as listed).

Real scraped deal records, used for exactly one thing: the continuity probe in the
report's §7, testing whether the pattern found in 2000–2012 still appears in a later
window in one large emerging market.

**It is never pooled with the Crunchbase data.** The taxonomies are not compatible, the
amount conventions differ, and the file has no `category_code`, so Tier A of the green
classifier cannot fire on it at all — only the lexicon tier applies. The scrape's own
coverage rules are unknown. The report treats it as a separate, caveated section and
draws no quantitative comparison across the two instruments.

---

## 3. Enrichment — all open, no authentication

| Source | URL | Used for |
|---|---|---|
| World Bank historical income groups | `ourworldindata.org/grapher/world-bank-income-groups.csv?csvType=full` | The time-varying bloc assignment |
| World Bank country metadata | `api.worldbank.org/v2/country?format=json&per_page=400` | ISO-3 validation, region |
| `NY.GDP.MKTP.CD` | World Bank indicator API | GDP, for the coverage-vs-economic-weight check |
| `NY.GDP.PCAP.CD` | World Bank indicator API | GDP per capita, the H5 market-depth regressor |
| `SP.POP.TOTL` | World Bank indicator API | Population, for per-capita normalisation |
| `EG.ELC.ACCS.ZS` | World Bank indicator API | Electricity access, an H5 need indicator |
| `EG.FEC.RNEW.ZS` | World Bank indicator API | Renewable share of final energy consumption |
| `NY.GDP.DEFL.ZS` | World Bank indicator API | **US series only**, for the constant-2015-USD conversion |
| OWID CO₂ dataset | `raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv` | CO₂ per capita, an H5 need indicator |

World Bank and OWID material is CC BY 4.0.

Two notes on use. The deflator uses the **USA** series because the amounts are already
denominated in USD; deflating a USD amount by a local deflator would be an error. And the
income classification is applied **by deal year**, not by present-day status, so a 2004
Polish deal is an emerging-market deal and a 2013 Polish deal is not.

---

## 4. Country blocs

Blocs are not a data source but are built from one, and the rules live in
`config/blocs.yaml` rather than in code:

- **AE** — World Bank high-income in the deal's year
- **EM** — upper-middle, lower-middle and low income, excluding China and excluding LDCs
- **China** — always separate; it dominates emerging-market aggregates and hides everything else
- **LDC** — the UN list, with graduation years applied per year
- **UNASSIGNED** — deals whose country cannot be established, reported as their own row rather than dropped or imputed

Crunchbase country codes carry legacy quirks (`ROM` for Romania, `TMP` for Timor-Leste,
regional aggregates like `FST` and `CSS` that are not countries, and blanks). Every
override is explicit in config and tested.

**Country recovery and the vanity-domain refusals.** Where a country is missing, it is
recovered first from the flat mirror's own country field and second from the company
homepage's country-code top-level domain, under an explicit allow-list. The allow-list
matters: several ccTLDs belong to emerging or least-developed countries and are sold
worldwide as vanity domains. `.tv` (Tuvalu), `.io`, `.me`, `.ly`, `.st` (São Tomé) and
others are **refused by name with a reason each**, because accepting them would have
manufactured hundreds of ventures in precisely the countries this project reports as
absent. The accepted and refused lists are in `config/blocs.yaml` and reproduced in the
report's Appendix B, with counts stated separately at company scale and deal scale.

---

## 5. A source field that is wrong in a way that does not announce itself

`funding_round_type` looks like the natural instrument field and is the wrong one. It
files seed rounds under `angel`, and both grant and debt rounds under `other`. Reading
instruments from it would have collapsed the seed stage into angel — making the graduation
funnel unmeasurable — and buried the non-dilutive instruments the instrument-mix
hypothesis depends on. Neither collapse raises an error.

The project therefore normalises from **`funding_round_code`**, with
`funding_round_type` as a fallback only where the code is absent. The full disagreement
table is `outputs/tables/appendix_instrument_conflicts.csv` and the report's Appendix G.

This is recorded here because it is the clearest example of the general risk in this
dataset: a plausible field that silently answers a different question.
