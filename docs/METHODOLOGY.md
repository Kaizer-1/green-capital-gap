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

---

## 6. The differential-audit asymmetry, and why the headline is raw classifier output

**Named before the results are reported, with its direction stated.**

The 28 emerging-market green companies were audited exhaustively, company by
company. The 1,114 advanced-economy green companies were audited only at the top of
the funding distribution. Removing false positives more thoroughly from one bloc than
from the other biases the double gap, and the direction is knowable in advance: if the
emerging-market false-positive rate is higher, curation lowers the emerging-market green
rate further and **widens** the gap.

The headline specification is therefore the **raw classifier output, with no manual
exclusions applied**. The classifier is symmetric by construction — the same lexicon,
the same vetoes, the same thresholds, applied to every company regardless of bloc.
Manual curation is not symmetric, because the attention paid to each bloc was not equal.
The curated specification is reported alongside as a robustness run, and both appear in
the text. Raw leads.

### 6.1 Measuring the asymmetry

60 advanced-economy green companies were drawn **at random** — not funding-ranked, so
the estimate is unbiased with respect to deal size — using the project seed, and audited
against the same standard as the emerging-market set. Every call is recorded in
`config/audit_calls.yaml` with a one-line reason.

| | Audited | False positives | Rate | 95% CI |
|---|---:|---:|---:|---|
| Emerging markets | 28 (census) | 6 | **21.4%** | 10.2–39.5 |
| Advanced economies | 60 (random of 1,114) | 9 | **15.0%** | 8.1–26.1 |

Two-proportion test: p = 0.455. Risk ratio 1.43 [0.56, 3.62]. **The two rates are not
distinguishable at this sample size.** The differential-audit concern is real in
principle and is not detectably biasing the result.

The point estimate nonetheless runs in the predicted direction, and the specification
grid confirms the consequence: the risk ratio moves from 0.479 raw to 0.399 curated, so
**curation widens the gap and the raw headline is the conservative choice.**

The same standard was applied in both directions. The rule that excluded SEDEMAC
Mechatronics from the emerging-market set — improving the efficiency of internal
combustion is not a green product — also excluded Transonic Combustion from the
advanced-economy sample. The tag-soup rule that excluded GATe Technology also excluded
IndustryTrader.com. Five advanced-economy companies were kept as **unverified**, exactly
as Villgro Innovation Marketing and Scion Global were kept, because excluding on
unverifiability preferentially deletes thinly-documented rows, which is the bias this
project is measuring.

---

## 7. The fossil rule

Stated once, applied symmetrically:

> A company is excluded as fossil when its **primary generation asset mix, or its primary
> product, was predominantly fossil in the observation window.**

Two properties of this rule need stating plainly.

First, it is applied on **external knowledge of the named companies, not on tag
patterns.** The Tier-C fossil regex in `config/green_lexicon.yaml` catches companies that
describe themselves in fossil terms; it cannot catch a coal-fired independent power
producer that Crunchbase tagged only "Clean Technology". That gap is why a manual rule
exists, and because the rule rests on outside knowledge it belongs in the curated
specification rather than the headline.

Second, **"mixed fuel" fails the rule and the company is kept.** Akenerji Elektrik Uretim
operates hydro and wind alongside substantial natural-gas capacity. It is not
predominantly fossil, so it stays, even though excluding it would have strengthened the
reported gap. The rule is followed rather than the thesis.

The same scrutiny was applied to advanced-economy independent power producers and fuel
businesses: it removed Luca Technologies (biogenic coalbed methane) and Prometheus Energy
(liquefied natural gas) from the advanced-economy sample, and KSK Power Venture
(predominantly coal-fired thermal) from the emerging-market set.

---

## 8. The ccTLD near-miss

Country codes were missing for 1,650 in-window companies — a bucket larger than the
entire emerging-market bloc. `city`, `state_code` and `region` are blank for every one of
them (`region` is the literal string `"unknown"`), so recovery had to come from the flat
mirror's own `country_code` (207 companies) and from domain top-level domains (101).

The domain route required an explicit allow-list, and this is worth recording by name
because the alternative was a fabricated result.

Several country-code top-level domains belong to emerging or least-developed countries
and are sold worldwide as vanity domains. Had they been mapped naively to their nominal
country, the following attributions would have entered the sample:

| TLD | Nominal country | Companies | Status |
|---|---|---:|---|
| `.me` | Montenegro | 315 | vanity, refused |
| `.tv` | **Tuvalu — an LDC** | 127 | vanity, refused |
| `.ly` | Libya | 65 | vanity, refused |
| `.fm` | Micronesia | 39 | vanity, refused |
| `.cc` | Cocos (Keeling) Islands | 34 | vanity, refused |
| `.st` | **Sao Tome and Principe — an LDC** | 18 | vanity, refused |
| `.to` | Tonga | 12 | vanity, refused |
| `.ws` | Samoa | 10 | vanity, refused |
| `.nr` | Nauru | 7 | vanity, refused |

A naive mapping would have **fabricated 127 Tuvaluan and 18 São Toméan ventures out of
domain-name marketing, in a project whose finding is that LDC green ventures are absent
from the record.** The LDC bloc contains 13 deals and zero green deals; `.tv` alone would
have multiplied it tenfold with companies that have no connection to Tuvalu.

All 23 refusals are enumerated with reasons in `config/blocs.yaml`, and the 29 accepted
ccTLDs are listed there too. Every recovered row carries the route that recovered it, so
any result can be re-run without the inferred ones.

---

## 9. The venture-stage criterion, declared in advance, did not work

Several of the largest emerging-market green deals are utility-scale generation assets
rather than startups. To separate them from venture-stage companies, an instrument-based
criterion was declared in `config/pipeline.yaml` **before being applied to any data**,
using only fields already present, and deliberately ignoring deal size, company name,
country and green status so that it could not be tuned toward a preferred answer:

> A company is venture-stage if at least one of its in-window rounds carries a venture
> instrument (angel, seed, Series A/B/C+, unspecified venture, convertible note).

**It did not separate the populations.** 96–98% of deals are venture-stage in every bloc,
and emerging-market green deals are 97.1% venture-stage against 96.5% for
advanced-economy green. The double gap is unchanged: the risk ratio is 0.479 under both
the full sample and the venture-stage-only sample.

The reason is visible in the data and is itself informative. Crunchbase codes
infrastructure project equity as ordinary venture rounds: Greenko Group and Akenerji as
`venture_unspecified`, KSK Power Venture as `series_a`, Auro Mira Energy as `series_b`,
Azure Power as `series_a` then `series_b`. Only Isagen appears as `debt_financing`. The
instrument field does not distinguish a Series B into a solar independent power producer
from a Series B into a software company.

The criterion is reported as declared, with its failure stated, rather than replaced by
one tuned until it produced a separation. Isolating infrastructure finance would require
company-by-company external knowledge, which would reintroduce precisely the audit
asymmetry that §6 exists to avoid.

The size cross-check does show the criterion picked up *something*: non-venture deals
have a higher mean ($22.3m against $9.1m) but a lower median ($1.0m against $2.9m), which
is the signature of a bimodal group mixing small grants with large infrastructure rounds.
It is not a clean venture/infrastructure split.

---

## 10. Sector composition: the green deficit is not green-specific

Reported because the alternative is to let the double gap imply something it does not.

Emerging-market venture capital in this snapshot is not simply a smaller version of
advanced-economy venture capital. Its sector composition is different, and the difference
explains a large part of the green deficit. Representation ratio is the emerging-market
share of a sector divided by the advanced-economy share, so 1.0 means proportionate:

| Sector | EM share | AE share | Ratio |
|---|---:|---:|---:|
| Biotech | 1.49% | 13.70% | **0.11** |
| Hardware | 1.24% | 3.97% | 0.31 |
| Enterprise | 2.57% | 7.59% | 0.34 |
| **Cleantech** | **2.41%** | **4.77%** | **0.51** |
| Software | 12.95% | 17.46% | 0.74 |
| Mobile | 9.88% | 7.89% | 1.25 |
| Web | 12.53% | 9.61% | 1.30 |
| Social | 5.06% | 1.93% | 2.62 |
| E-commerce | 15.44% | 4.50% | **3.43** |
| Travel | 2.66% | 0.74% | 3.60 |

The pattern is capital intensity, not greenness. Emerging-market venture capital in
2000–2012 concentrated in capital-light consumer internet — e-commerce at 3.4× its
advanced-economy weight, travel at 3.6×, social at 2.6× — and avoided capital-intensive,
long-horizon, R&D-heavy sectors. **Biotech is 4.6 times more under-represented than
cleantech.** Three sectors are more under-represented in emerging markets than cleantech
is: biotech, hardware and enterprise.

This is a substantive explanation rather than a confound to be purged. It says the
emerging-market green deficit is one instance of a general preference for capital-light
bets in thin markets, and it extends Gaddy et al. directly: if the venture model was
already mismatched to capital-intensive energy innovation in deep, liquid US capital
markets, the mismatch is worse where capital pools are thinner and exits are harder — and
what the data shows is emerging-market venture avoiding the whole class of
capital-intensive sectors, with cleantech among them rather than singled out.

It does **not** dissolve the double gap. Cleantech is still under-represented at 0.51, and
the conditional green rate gap is significant under every specification. The claim the
sector composition licenses is narrower and more defensible: the gap is a capital-intensity
gap that green entrepreneurship sits inside, not evidence of something specific to green.

---

## 11. H3 is caveated before its numbers, not after

**Stated here before any H3 result is computed.**

§9 established that the record cannot distinguish infrastructure project equity from
venture rounds: KSK Power Venture's coal-and-hydro project financing is coded `series_a`,
Greenko Group's and Akenerji's as `venture_unspecified`, Azure Power's as `series_a` then
`series_b`. Only Isagen appears as `debt_financing`.

This has a direct and knowable consequence for H3, which measures the share of funding
arriving through non-dilutive instruments. **Project finance that is genuinely debt or
concessional in nature, but coded as an equity round, understates the non-dilutive share
on both sides of the comparison.**

The bias is very unlikely to be symmetric. Infrastructure-scale independent power
producers are a far larger fraction of the emerging-market green set — on inspection,
seven of the 28 emerging-market green companies are IPPs or utility-scale generation
developers — than of the advanced-economy green set, where venture-stage hardware and
software firms dominate. So the understatement of non-dilutive share should be **larger
for emerging markets than for advanced economies.**

The direction matters because H3's emerging-market arm asks whether emerging-market green
capital is *more* non-dilutive than advanced-economy green capital. If the measured
answer is "no difference" or "less non-dilutive", that result is **biased toward the
answer it gives**, and cannot be read as evidence against the underlying hypothesis. It
can only be read as: the open record does not show the difference, and the record's own
instrument coding is a reason it would not show it even if the difference were real.

H3's emerging-market arm is reported with this caveat attached, in the text, before the
numbers.

---

## 12. Two measurement findings about the record itself

These are findings, not caveats, and they belong in the results. They are two faces of one
claim: **the open venture record lacks the resolution to study emerging-market green
entrepreneurship, in both the sector dimension and the instrument dimension.**

### 12.1 The taxonomy cannot resolve green sub-domains in emerging markets

91.2% of emerging-market green deals carry no green sub-domain more specific than
"general". The mechanism is direct: **26 of the 28 emerging-market green companies carry
no taxonomy tag more specific than "Clean Technology"**, with match text reading
`|Clean Technology| | cleantech | | | Clean Technology` and nothing else. Only four carry
specific evidence — Vital Renewable Energy (sugarcane ethanol), farmhopping, Keclon and
Stima Systems.

The advanced-economy rate is 67.5%, itself high, so this is a general weakness of the
taxonomy that becomes disabling in emerging markets. The consequence is that the planned
sub-domain mix comparison (originally Figure 5) is dead in every form, including
conditional on having a specific sub-domain, and it was cut.

### 12.2 The record cannot distinguish project finance from venture finance

A pre-declared, instrument-based, symmetrically-applied venture-stage criterion failed to
separate utility-scale generation assets from venture-stage startups: 96–98% of deals
classify as venture-stage in every bloc. The worked examples are in §9 — KSK, Greenko,
Azure, Auro Mira, Akenerji, all coded as ordinary venture rounds.

Taken together: a researcher using this record cannot tell *what kind of green* an
emerging-market company is, nor *what kind of capital* it raised. Those are the two
variables an analysis of the emerging-market green capital regime would need most. Their
absence is why this paper reports a measurement result rather than the regime result it
set out to produce, and it is a concrete, citable statement about the data infrastructure
of the field.

---

## 13. The audit comparison is underdetermined, not reassuring

§6 reports emerging-market and advanced-economy false-positive rates of 21.4%
[10.2–39.5] and 15.0% [8.1–26.1], with p = 0.455.

**That is an absence of power, not a demonstration of equality.** With 28 and 60 companies
audited, the study cannot detect a 6-percentage-point difference in false-positive rates;
the two intervals overlap across most of their range and the risk-ratio interval
[0.56, 3.62] admits anything from the advanced-economy rate being nearly twice the
emerging-market rate to the reverse being more than threefold. The correct statement is
that the differential-audit asymmetry **has not been ruled out**, and that the point
estimate runs in the direction that would make the raw headline conservative.

Because the comparison is underdetermined, a third specification is reported rather than
resting on either raw or partially-curated numbers alone.

### 13.1 The three specifications

| Specification | EM rate | AE rate | Risk ratio | 95% CI |
|---|---:|---:|---:|---|
| **Raw — headline** | 2.597% | 5.425% | **0.479** | 0.343–0.669 |
| Bias-corrected | 2.016% | 4.579% | 0.437 | 0.261–0.652 |
| Partially curated | 2.139% | 5.357% | 0.399 | 0.276–0.577 |

The bias-corrected specification applies each bloc's measured false-positive rate to its
**whole** green population, rather than only to the companies that happened to be audited,
so both blocs are corrected on the same basis. Audit uncertainty is propagated by drawing
the false-positive rates from Jeffreys Beta posteriors, with binomial sampling of the green
counts layered on top, across 20,000 seeded draws.

It **sits between the other two**, which is the confirmation that matters: partial curation
inflates the gap, because it removes false positives from the bloc that was audited
exhaustively while leaving them in the bloc that was only sampled. The raw specification
leads because it is symmetric and conservative; the bias-corrected one is the honest
midpoint; the partially-curated one is the upper bound on the gap and is reported as such
rather than as a result.

Under bias correction the risk ratio is below 1 in **20,000 of 20,000 draws**. The gap
itself is not in question under any specification. Only its magnitude is.

---

## 14. Three corrections made after the first pass

Recorded because each reverses something this document previously asserted.

### 14.1 The cheque-size finding was retracted too early

§5 of the figure set first reported that the median green cheque fell 72% in real terms
over 2007–2012, and read it as the Gaddy et al. rotation out of hardware. A control
against non-green deals showed a 73% fall over the same window, and the finding was
retracted.

**That retraction was wrong, and on the same grounds the original claim was wrong.** The
pooled median is composition-confounded for *both* groups: holding the 2007 stage mix
fixed leaves non-green at −11%. A pooled comparison cannot settle the question in either
direction. The real control is the within-stage comparison, and it was available all
along.

Tested properly — bootstrap over 10,000 draws, resampling within each group × stage ×
year cell, on clean stage codes only:

| | within-stage change, 2007→2012 |
|---|---:|
| Green | −50.4% |
| Non-green | −1.1% |
| **Difference** | **−49.3pp [−69.3, −22.4]** |

The interval excludes zero, so the finding **stands in narrowed form**: within named
funding stages, green deal sizes fell substantially faster than non-green. The
`venture_unspecified` catch-all is excluded, because its median collapses in both groups
as its volume explodes, which is coverage expansion rather than repricing.

What still cannot be claimed is the *mechanism*. A size pattern is not an investor motive;
the rotation out of hardware remains external evidence.

### 14.2 H4 is undetermined, not refuted

An earlier draft recorded H4 as "Not supported" and noted that the signal ran opposite to
the hypothesis. Both were wrong.

The seed-to-A odds ratio is 1.30 with an interval of [0.65, 2.60]. That interval spans 1
and identifies no direction, so reading one off the point estimate reads noise. The A→B
transition — the specific missing-middle prediction — is not testable at all: the
advanced-economy green pool is 13 companies. The spread across specifications (1.30, 1.66,
1.00) is one wide interval sampled three ways, not three results.

**H4 is recorded as "Underpowered — cannot determine."** The §1.3 pre-commitment, which
chose strict seed as the specification that would not flatter the hypothesis, reasoned
about the *direction* of an expected negative effect. It is void here because the binding
failure is power, not direction. That is recorded rather than quietly satisfied.

What the exercise does establish is sharper than a verdict: there are **zero**
emerging-market green seed entrants across thirteen years, and even in the best-covered
bloc the A→B pool is 13 companies. The scale-up step is unobservable in the open record.

### 14.3 The H5 falsifier did not fire

The income-controlled coefficient on the electricity-access deficit was positive and
significant (+0.223, p = 0.010), which met the pre-registered falsification condition, and
it survived both a leave-one-out check (no sign flips, no loss of significance) and a
collinearity check (VIF 2.79).

Both checks missed the actual problem. **Twenty of the 22 panel countries have an
electricity deficit of exactly 0.0%**; China is 0.1% and India is 20.1%. The regressor is
in substance a dummy for one country, the largest single value carries 99.5% of the total,
and dropping India sends the coefficient to 32.8 because no variance remains. A
coefficient identified off one observation is not interpretable however well it behaves on
VIF and sign stability.

A degenerate-variance check is now part of the stress test, and the falsification condition
is recorded as **not having fired**. H5 stands as Supported.

The degeneracy is itself the more important result, and it belongs in the text rather than
the appendix: **countries with real energy-access deficits have too few green deals to
enter the panel at all.** H5's need indicators were not tested and found null. They could
not be tested. That is the sixth independent route to the measurement thesis.
