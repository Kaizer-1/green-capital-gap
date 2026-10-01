# METHODOLOGY

> Status: under construction. Sections 1–4 are **pre-commitments**, written before the
> relevant results were computed, so that the analytical choices they describe cannot be
> read as post-hoc. Each states the date and build step at which it was fixed. The full
> methodology write-up is assembled at build step 12; nothing in sections 1–4 may be
> weakened after the fact, only reported against.

---

## 1. Pre-commitments fixed before the green classifier was built (build step 2→3)

### 1.1 H3 grant arm: descriptive only, no significance test below n = 30

**Fixed before the bloc × green split was computed.**

The 2000–2012 window contains **535 grant rounds in total, across all countries and all
sectors**. Debt financing contributes 2,405 and convertible notes 114. Non-dilutive
instruments are 7.1% of in-window deals.

Split by bloc × green status, the grant cell will very likely fall below the minimum cell
size of 30 set in `config/pipeline.yaml`. The decision, taken now:

- **Grants are reported descriptively**, with exact cell sizes printed on the figure and in
  the table, and **no significance test is run on any grant cell with n < 30.**
- **Debt financing carries the inferential test for H3.** The χ² test of independence and
  Cramér's V are computed on the instrument-family contingency table, where the
  non-dilutive column is debt-dominated.
- If the grant cell turns out to be adequately powered, the test is run and reported. The
  commitment is not to *suppress* a test that is available; it is to refuse to treat a
  thin cell as informative because the result happens to be convenient.
- The green definition is **not** widened to recover power in any cell. If H3's grant arm
  is underpowered it is reported as underpowered.

### 1.2 H4 observation window asymmetry

**Fixed before any graduation rate was computed.**

H1 and H2 measure *levels* — deal counts and dollar volumes by bloc and year. Those
quantities are directly contaminated by Crunchbase's coverage growth over the period
(§2 below). H4 measures a *conditional transition*: given that a company raised seed
capital and therefore entered the sample, did it go on to raise Series A, and then
Series B?

Because H4's numerator and denominator are both drawn from the same entry cohort, growth
in coverage partly differences out: a cohort that is better covered contributes more
companies to both the denominator and the numerator. This is a weaker form of
contamination than the level-based hypotheses face, not an absence of it — coverage growth
could still be correlated with the *kind* of company recorded, and that residual threat is
carried into the limitations.

On that basis, and only on that basis, H4 is permitted a **reported secondary
specification** with an observation window extended to **2013-11-30**. The gain is an
extra year of follow-up, which admits one further founding cohort under the three-year
minimum; it is **not** about the larger raw deal count. The headline H4 specification
remains the project window ending 2012-12-31, and both are reported.

Permitted only because the two censoring checks in §3 below both cleared.

### 1.3 H4 funnel entry gate

Folding angel rounds into the seed entry gate inflates the funnel denominator and
depresses measured graduation rates. That effect is expected to be larger in emerging
markets, where angel-only financing is more common, which biases H4 **toward** the
project's thesis.

The headline specification therefore uses **strict seed** (`funding_round_code == 'seed'`,
n = 8,163 in window), the specification that does not flatter the hypothesis. The
angel-inclusive specification (n = 10,848 in window) is run and reported alongside. If the
two diverge materially, that divergence is itself reported as the H4 finding. The
direction of the bias is verified empirically before the headline is fixed; if the data
reverses it, the headline switches and the text says so.

### 1.4 Instrument field selection

`funding_round_code` is used as the instrument field, with `funding_round_type` as a
fallback where the code is absent. This was established empirically at step 2 and is not a
stylistic preference: `funding_round_type` is a nine-value rollup that collapses `seed`
into `angel` for 10,189 rows and buries `grant` (776), `debt_round` (3,409),
`convertible` (187) and `secondary_market` (16) inside a single `other` bucket.
Normalising from it would have left H3 untestable and H4 unmeasurable, and the failure
would have been silent.

The two fields disagree for 16,419 of 52,928 rows (31.0%). The code field wins. The full
contingency table is `outputs/tables/appendix_instrument_type_x_code.csv` and the
canonical-label conflicts are `outputs/tables/appendix_instrument_conflicts.csv`.

---

## 2. Coverage growth as the primary censoring argument

**Fixed before the EM/AE split was computed.**

The conventional argument for truncating the window is right-censoring: deals are recorded
with a lag, so the final months are incomplete. That argument is correct but secondary.

The primary argument is **differential coverage growth**. Crunchbase's coverage expanded
substantially over 2000–2013, and it almost certainly expanded *faster* for
emerging-market ecosystems than for the United States, which was close to saturation
early. Coverage of a non-US, non-English-language ecosystem in 2004 is far worse than
coverage of the same ecosystem in 2013.

This means the final year of the window is the **most coverage-contaminated year for
precisely the quantity H1 measures** — the emerging-market share of global green deals and
dollars. An apparent rise in EM share toward the end of the period is exactly what growing
EM coverage would produce in the absence of any real change in the underlying capital
flows. The two are not separable with this data alone.

Three consequences, all binding:

1. The headline window ends **2012-12-31**, and the argument given in the report is
   coverage growth first, recording lag second.
2. H1's trend claim is stated as **conditional on coverage**, and the report says plainly
   that a rising EM share is consistent with both a real shift and a measurement artefact.
3. The contamination is **quantified, not disclaimed**: EM share of green deals by year is
   benchmarked against EM share of world GDP by year, and the gap and its trend are
   reported. A measurable bias beats a disclaimed one. This test is built at step 4, once
   time-varying bloc assignment exists, and its result is reported whichever way it falls.

---

## 3. Censoring checks performed before the deal table was built (build step 2)

Both were run before the 2013-inclusive secondary specification was permitted. Both
cleared. Had either failed, the secondary specification would have been dropped.

### 3.1 Seasonality cannot explain the December 2013 dip

December 2013 holds 424 deals against a 2013 monthly mean near 950. Attributing that to
the snapshot cut requires ruling out an ordinary December seasonal effect.

December as a share of its own year's deals:

| Year | December share |
|---|---|
| 2011 | 8.04% |
| 2012 | 6.99% |
| 2013 | **3.83%** |

December is not normally a weak month. The 2013 share is 0.51× the 2011–2012 baseline of
7.52%. November 2013, by contrast, holds 944 deals (8.53% of its year), *above* the
November shares for 2011 (7.92%) and 2012 (7.14%). The discontinuity is confined to
December, consistent with a snapshot taken mid-December 2013.

Table: `outputs/tables/diag_censoring_monthly_counts.csv`.

### 3.2 Dollar amounts are not differentially censored in 2013

Deal counts can look complete while dollars are still censored, because amounts backfill
after a round is first entered. Disclosed-amount rate by year:

| Year | Disclosed |
|---|---|
| 2011 | 88.99% |
| 2012 | 88.61% |
| 2013 | 88.44% |

Flat. Within 2013, November (92.27%) and December (92.22%) are among the **highest**
monthly disclosure rates anywhere in 2011–2013. The deals that had been entered by
snapshot time were disproportionately the well-documented ones; the count is censored, the
surviving rows are not amount-censored.

Table: `outputs/tables/diag_censoring_disclosure_by_month.csv`.

---

## 4. Amount null encoding, established by evidence rather than assumption

**Fixed before any amount was nulled.**

In `funding_rounds.csv` an undisclosed amount is encoded as a literal `0.0`, not as NaN:
6,000 of 52,928 rows. Treating those as disclosed zero-dollar rounds would drag every
median, IQR and dollar total toward zero while reporting 100% data coverage.

Before nulling, the column was swept for other sentinel patterns:

| Check | Result |
|---|---|
| Negative amounts | 0 |
| Exactly `1.0` | 0 |
| Positive but under $1,000 | 1 (minimum $291) |
| Above $5bn for a single round | 0 (maximum $3.835bn) |
| Zeros with a positive local-currency amount | 362 |
| Zeros with a currency code but no amount | 2,934 |
| Zeros with no other evidence of a round | 3,066 |

The most frequently repeated positive values are ordinary round numbers ($1m × 1,549,
$5m × 1,215, $2m × 1,173), which is human round-number reporting rather than a placeholder
signature. No single implausible value repeats.

The decisive evidence that `0.0` means "undisclosed" and not "a zero-dollar round" is the
362 rows that carry a **positive** amount in local currency alongside a USD value of
exactly zero. A round cannot simultaneously be worth £4m and $0. The zero marks an absent
USD conversion, not an absent round.

Accordingly: zeros become NaN, counted on the attrition ledger, and **never imputed**.

### 4.1 The 362 currency-conversion failures bias against the thesis

These rows have a positive local-currency amount and no USD conversion. They are a
distinct failure mode from a genuinely undisclosed deal and are counted separately. They
are **not** back-converted; doing so would require an unvetted historical FX source.

Their country distribution was checked for emerging-market skew, which would have added a
line to the bias ledger. The skew runs the other way:

| Country | Share of FX failures | Share of all deals | Skew |
|---|---|---|---|
| United Kingdom | 20.0% | 5.59% | 3.6× |
| Canada | 15.1% | 2.85% | 5.3× |
| Spain | 11.4% | 1.01% | 11.3× |
| Germany | 10.2% | 1.97% | 5.2× |
| France | 7.1% | 1.81% | 3.9× |
| United States | 1.9% | 68.4% | 0.03× |

Currencies affected: EUR (216), GBP (68), CAD (54), JPY (12), SEK (6), ILS (3), AUD (3).
**Every affected currency belongs to an advanced economy.** No emerging-market currency
appears. The effect therefore understates **advanced-economy** dollar totals by a small
amount, which is conservative with respect to H1's claim that emerging-market dollar share
lags its deal share. At 362 rows, 0.7% of deals, the magnitude is small either way.

Tables: `outputs/tables/diag_fx_failures_by_country.csv`,
`outputs/tables/diag_fx_failures_by_currency.csv`.

---

## 5. The two Crunchbase datasets are different vintages

**Established at build step 2. This corrects a premise in the build specification.**

`CLAUDE.md` §4 described the two Kaggle datasets as "two Kaggle mirrors of the same
underlying snapshot". They are not.

| | Relational (`justinas/startup-investments`) | Flat (`arindam235/startup-investments-crunchbase`) |
|---|---|---|
| Latest funding date | `funded_at` 2013-12-12 | `last_funding_at` 2015-01-01 |
| Vintage | December 2013 snapshot | early-2015 export |

Of 18,593 companies present in the flat file but carrying no deal rows in the relational
dump, 14,511 are absent from `objects.csv` entirely and 9,463 last raised in 2014, after
the relational snapshot closed. The flat file is a later export.

### 5.1 What this does and does not compromise

The relational dump is **not** incomplete for post-snapshot activity — that activity simply
postdates it. But a genuine census gap exists within its own period:

- **2,186 companies** that the flat file reports as funded before 2013-12-12 carry **zero
  deal rows** in `funding_rounds.csv`, with $14.31bn of claimed funding.
- On the 30,845 matched companies, the flat file reports **9,765 more rounds** than the
  relational dump. 6,353 of those are explained by post-snapshot activity. **3,412 are
  not**, which is **6.5% of all deal rows**.

So `funding_rounds.csv` under-records by roughly 6.5% relative to a later re-export of the
same database, within its own period. Three consequences:

1. The flat file is used **for its taxonomy only** — `category_list` feeds the green
   classifier. Its funding columns are **never** summed, and no dollar figure in this
   report derives from them.
2. The deal table is described in the report as the December 2013 relational census, with
   its measured under-recording stated, rather than as a complete record of the period.
3. Whether the under-recording is **differential by bloc** is tested at step 4 and added to
   the bias ledger. If emerging-market deals are disproportionately missing, the gap
   compounds the coverage bias in §2 and the report says so.

This strengthens the case for the strategy the brief already mandates: privilege
**within-bloc comparisons and ratios** over absolute cross-bloc levels.

### 5.2 Taxonomy anachronism

The green labels come from a 2015-vintage `category_list` applied to companies whose deals
occurred in 2000–2012. A company that pivoted into or out of a green line of business
between 2012 and 2015 is labelled by its later self. The direction of the resulting bias is
unknown and is carried into the limitations rather than assumed away. The 2015 taxonomy is
also richer and more complete than a 2013 one would have been, which is why the join is
worth making despite the anachronism.

Table: `outputs/tables/appendix_mirror_vintage.csv`.
