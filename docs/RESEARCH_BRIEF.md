# RESEARCH_BRIEF.md

> The intellectual content of the project. `CLAUDE.md` says how to build; this says what
> to argue and why. Read before writing any analysis module or any report prose.

---

## 1. Why this topic is harder than it looks

The brief says "open dataset analysis of green startup funding trends in emerging markets".
The obvious reading is: download a funding CSV, filter to green, groupby country, plot.
That produces a report with no claim in it, and it will be marked as such.

The real difficulty is that **there is no open, current, deal-level dataset of green
startup funding in emerging markets.** Everything current is proprietary:

| Source | Status | What it would give you |
|---|---|---|
| Dealroom | paywalled | deal-level, global, current |
| Tracxn | paywalled | deal-level, strong India coverage |
| Net Zero Insights | paywalled | climate-tech-specific taxonomy |
| Sightline Climate | paywalled | VC/growth equity focus |
| PitchBook, CB Insights | paywalled | general |
| Crunchbase (live) | API paywalled | deal-level, global |

What *is* open: the **Crunchbase 2013 Snapshot**, released under CC BY 4.0 and mirrored
on Kaggle. It is genuine, deal-level, global, and it covers **52,928 funding rounds** with
dates, amounts, round types and country codes, of which **41,455 fall in the 2000-2012
analysis window**. (Corrected at build step 2; an earlier draft of this brief said
~90,000, which was wrong.)

Its weakness is obvious: it stops in 2013. Measured precisely, the deal-level relational
dump ends at 2013-12-12.

**Turn that into the design.** The 2005–2012 window is not a stale window. It is the
window of **Cleantech 1.0** — the first global green venture boom and its collapse. It is
the only period for which deal-level green funding data is publicly available at all, and
it is the period that structurally determined everything that followed. Analysing it
properly, and then testing whether its structural signatures persist in contemporary
secondary evidence, is a far stronger piece of work than a shallow pass over a 1,000-row
synthetic CSV of 2024 deals.

**Frame the report this way explicitly, in the introduction.** The data constraint is a
finding about the field, not an embarrassment: the measurement of green entrepreneurship
in emerging economies is itself gated behind proprietary data, which is part of why the
capital gap persists.

---

## 2. Context the report needs (all externally cited, none computed)

### 2.1 Cleantech 1.0: the boom and the bust

The canonical reference is Gaddy, Sivaram, Jones and Wayman, *Venture Capital and
Cleantech: The Wrong Model for Energy Innovation*, MIT Energy Initiative working paper
2016, published in *Energy Policy* 102 (2017).

Findings to cite:
- VC firms committed over **US$25 billion** to cleantech startups between **2006 and 2011**
  and recovered less than half of it.
- More than **90% of cleantech A-round investments made after 2007** failed to return the
  capital invested.
- The underperformance was concentrated in **materials, chemistries and hardware** firms
  that never reached manufacturing scale, not in software.
- Investors responded by cutting sector allocation and **rotating from hardware into
  cleantech software**.
- Their conclusion: the venture model is structurally mismatched to clean energy, which
  needs more capital over longer horizons than a 3–5 year fund life permits.

Use this as the external benchmark against which your emerging-market results are read.
If the VC model was already a poor fit for cleantech in deep, liquid, dollar-denominated
US capital markets, the prior expectation for emerging markets — thinner capital pools,
currency risk, weaker exit markets — is that the mismatch is worse. H2 and H4 test that.

### 2.2 The present-day structure (triangulation targets)

These are for §7 of the report, where you ask whether the 2005–2012 structure persisted.
All are secondary citations, clearly labelled as such — **do not present them as your
results.**

**Climate Policy Initiative, Global Landscape of Climate Finance (2025, 2026 editions)**
- Global tracked climate finance reached roughly **US$1.9 trillion in 2023** and crossed
  **US$2 trillion in 2024**, with growth decelerating to ~6% in 2024 from ~16% in 2023.
- **Advanced economies plus China have accounted for around 80% of global flows since
  2019.** EMDEs excluding China captured roughly 14–17%; LDCs roughly 2–3%.
- CPI's "Emerging Markets" grouping (111 EMDEs excluding China and excluding 45 LDCs) is
  **over half the world's population and 23% of global GDP** — and is now the
  fastest-growing grouping, at a **25% CAGR since 2022**.
- Domestic sources supply roughly **63% of flows into Emerging Markets**, versus a much
  higher domestic share in China and only ~27% in LDCs.
- LDCs saw international public climate flows **fall 24% year-on-year in 2024**.
- Needs: mitigation finance must reach roughly **US$7.8 trillion a year over 2025–2030**,
  rising toward **US$9 trillion a year through 2035**.

**Regional shares** — sub-Saharan Africa and South Asia received approximately **2.8% and
3.4%** of tracked global climate finance flows in 2021–22 despite carrying far higher
climate vulnerability. This needs-versus-flows mismatch is exactly what H5 tests at
deal level.

**Venture-side, current**
- Dealroom puts climate tech VC at roughly **US$39 billion in 2025**, around 3% of total
  VC, with energy (~$24bn, −30% YoY) and mobility (~$13bn, −27% YoY) dominant in 2024;
  **Europe overtook the US** for climate tech VC in 2023.
- Net Zero Insights records only **US$23.5 billion of climate tech equity in H1 2025**, one
  of the weakest half-years since 2020, with **non-dilutive capital rising** as equity
  shrinks, and **falling graduation rates from seed to Series A and Series A to Series B**.
- Sightline Climate puts H1 2025 total climate tech funding **down ~19% year-on-year**,
  after a ~41% drop in 2023, with **Series B down 29%** — the stage most exposed to the
  scale-up gap.

**Note the divergence between those three estimates and use it.** $39bn, $23.5bn and
"down 19%" are not reconcilable without knowing each provider's taxonomy and instrument
coverage. That is a legitimate, citable point about the measurement of green
entrepreneurship, and it justifies the care you take over your own classifier in §6 of
`CLAUDE.md`.

**India, as the emerging-market case**
- Tracxn's *India Climate Tech 2026* report: cumulative funding of roughly **US$12.8
  billion across 1,583 funded companies** since 2008, with annual funding rising from
  about **US$315 million in 2020 to US$2.6 billion in 2025**.
- Renewable energy tech leads cumulatively at ~**US$1.5 billion**; solid waste
  (~$477m), energy efficiency (~$352m), air pollution (~$237m) and water/wastewater
  (~$208m) together exceed $1.2 billion.
- India's share of global PE/VC climate tech investment **fell to ~4.2% in CY2024 from
  ~6.6% in CY2023**, as global climate tech funding fell ~40% to ~$30.9bn from ~$51.5bn.
- India's climate investment need is estimated at **US$253–263 billion a year** against
  current flows of roughly **US$44 billion a year**.

### 2.3 The structural mechanisms the literature names

Cite these as the explanatory frame for whatever you find.

**The missing middle / pioneer gap.** The financing chasm between proof-of-concept capital
and growth capital. Too large for grants and angels, too unproven for banks and
infrastructure investors, too capital-hungry and slow for venture. In climate specifically
it bites hardest at first-of-a-kind commercial deployment. Africa's SME financing gap
alone is estimated around **US$331 billion**.

**Currency and country risk.** Emerging-market green ventures earn revenue in local
currency but raise in hard currency. Hedging is expensive or unavailable, so investors
demand a risk premium that compounds the capital-intensity problem. This is a first-order
explanation for a non-dilutive, debt-and-grant-heavy instrument mix (H3).

**Institutional voids and the Porter hypothesis.** The green entrepreneurship literature
on emerging economies converges on institutional quality, regulatory enforcement and
policy credibility as the moderators that determine whether green entrepreneurial
intention converts into funded, scalable ventures. Where enforcement is weak, the
regulatory "pull" that creates green markets is absent, and green ventures compete on
price alone against incumbents with unpriced externalities.

**Capital follows institutions, not need.** The recurring empirical finding is that green
capital allocates toward depth of financial markets and ease of exit, not toward
emissions, vulnerability or energy poverty. H5 tests this at deal level.

**Blended and concessional finance.** Concessional public capital is positioned as the
instrument that de-risks the missing middle. Roughly 29% of flows into CPI's Emerging
Markets grouping in 2023 moved through concessional loans and grants.

---

## 3. Research questions

Revised at build step 3, after the emerging-market green sample was measured at 35 deals.
The original RQ1/RQ2 presumed a comparable emerging-market series exists. It does not, and
the revised questions ask what the data can actually answer.

**RQ1.** How visible is green entrepreneurship in emerging economies in the open venture
record, relative to advanced economies — both in absolute coverage and, conditional on
dataset membership, in the probability that a recorded company is green?

**RQ2.** Within the one bloc where the record is dense enough to test them, do green
ventures face a structurally different capital regime from non-green ventures — in cycle
exposure, instrument mix and stage graduation? This is the benchmark case against which
any future emerging-market evidence can be read.

**RQ3.** Across countries, does green capital allocate toward climate and energy *need*,
or toward market depth and institutional quality?

**RQ4.** What do the structural signatures identified in 2000–2012 imply for
contemporary emerging-market green entrepreneurship, and which of them appear in current
secondary evidence?

---

## 4. Hypotheses

Each is falsifiable, each maps to one analysis module, each gets an explicit verdict.
H1 was replaced at build step 3; H2–H4 were re-specified onto the advanced-economy
benchmark with a bounded emerging-market arm; H5 is unchanged.

**Standing rule for every emerging-market arm below.** It is reported as an explicitly
bounded, underpowered probe. Every cell size is printed. **No significance test is run on
any cell with n < 30.** Nulls are retained. Leave-one-out sensitivity is published for
every emerging-market headline number, because with 35 deals one curation decision moves
a figure by up to 20%.

### H1-revised — Selection and visibility: the double gap
*Emerging markets are under-represented in the venture record relative to their economic
weight; and, conditional on a company already being in the record, an emerging-market
company is markedly less likely to be green than an advanced-economy one.*

The second clause is the headline. It is immune to the coverage objection because
numerator and denominator are both drawn from indexed companies.

Tests: green rate by bloc, conditional on dataset membership, with Wilson score intervals.
Two-proportion z-test plus Fisher's exact as a small-sample check. Effect size as a risk
ratio with CI, an odds ratio with CI, and Cohen's h. The same by year, with the cell-size
rule applied — in practice no emerging-market year-cell reaches n = 30, so no per-year
test is reported and the table says so. An **upper bound** in which every still
unattributable deal is counted as emerging-market, which is maximally generous to the
null. The GDP-share comparison is the denominator check establishing that the second gap
is not the first restated.

Falsified if: the emerging-market green rate is indistinguishable from the
advanced-economy rate, or the gap vanishes under the upper bound.

### H2 — The green bust was amplified relative to non-green
*Within advanced economies, the post-2008 contraction in green funding was deeper and
longer than the contraction in non-green funding.*

Tests: indexed series (2007 = 100) for AE-green and AE-non-green, with the emerging-market
series plotted but not tested. Peak-to-trough drawdown and time-to-recovery. Difference-in
differences on log deal volume with a `green × post2008` interaction, year fixed effects,
robust SEs. Plot and formally check pre-trends.

Falsified if: the interaction is indistinguishable from zero, or pre-trends diverge.
**If pre-trends fail, downgrade to descriptive and say so.**

EM arm: the emerging-market green series runs 2, 12, 4, 4, 7, 6 across 2007–2012.
Descriptive only. Note in the text that the EM green *rate* tracked the AE rate almost
exactly in 2008 (10.08% against 10.24%) and then diverged, without claiming a test.

### H3 — Green capital is less dilutive than non-green
*Green ventures draw a higher share of funding from grants, debt and other non-venture
instruments than non-green ventures do.*

Tests: instrument-mix shares by green status, by count and by dollars. χ² test of
independence with Cramér's V. Stacked-area evolution over time. Debt carries the
inferential test; grants are descriptive only where n < 30, a decision recorded in
`docs/METHODOLOGY.md` §1.1 before the split was computed.

Falsified if: green and non-green instrument mixes are statistically indistinguishable.

EM arm, pre-registered expectation: **this arm is expected to return a null.** The
green/non-green gap looks larger than the EM/AE gap, so the original H3 claim that
emerging-market green is *more* non-dilutive than advanced-economy green is unlikely to
survive. It stays in and is reported either way.

### H4 — The scale-up step is where green ventures lose
*Conditional on raising seed capital, green ventures are less likely to reach Series A,
and markedly less likely to reach Series B, than comparable non-green ventures — with the
largest gap at A→B, the "missing middle".*

Tests: company-level funding histories from the deal table. Cohort graduation rates
seed→A and A→B by green status, by founding cohort, cohorts needing ≥3 years of
observable window. Logistic regression with green, year fixed effects and sub-domain
controls; odds ratios with CIs. Headline uses strict seed; the angel-inclusive
specification is run alongside (`docs/METHODOLOGY.md` §1.3).

H4 is permitted the extended 2013-11-30 observation window as a reported secondary
specification, justified in `docs/METHODOLOGY.md` §1.2.

Falsified if: the green coefficient is null, or the gap is no larger at A→B than seed→A.

EM arm: not testable. Report the cell sizes and say so.

### H5 — Capital tracks market depth, not climate need
*Country-level green funding intensity correlates with GDP per capita and financial-market
depth, and shows no positive association with indicators of climate or energy need.*

Tests: country-level panel. Green funding per capita and per unit GDP as outcomes.
Spearman rank correlations against GDP per capita, electricity access, renewable share of
final energy, CO₂ per capita — **with bootstrap CIs on ρ, not bare ρ**. Gini and HHI of
green funding concentration. Top-5 country share over time. OLS with log GDP as a control.

**Power, stated up front:** 42 countries have at least one green deal, 23 have at least
three, 20 have at least five. The outcome is built on small per-country counts. The
correlations are reported with CIs and the small-n caveat in the text, not as precise
estimates.

Falsified if: need indicators show a positive, significant association after controlling
for income.

## 5. Analytical choices that earn marks

Make these explicit in the methodology section. Each is a point an examiner can tick.

1. **Time-varying bloc assignment.** Deals get the income classification their country
   held in the deal year, not today's.
2. **Constant-dollar conversion.** All amounts in 2015 USD via the US GDP deflator.
3. **Right-censoring handled.** Window truncated at 2012-12-31, with the uncensored tail
   shown separately and labelled as an artefact.
4. **Counts and dollars reported as separate series throughout**, because
   undisclosed-amount rates differ systematically by bloc.
5. **Three-tier green classifier with a published lexicon and a published exclusion list**,
   inter-tier κ reported, every headline result re-run under the strict definition.
6. **Coverage bias quantified, not just disclaimed** — EM share of deals benchmarked
   against EM share of world GDP in the same year.
7. **Within-bloc comparisons privileged over cross-bloc levels**, because the former are
   far more robust to the coverage bias.
8. **Attrition ledger** showing every row dropped and why.
9. **Multiple-comparison correction** across the test family.
10. **Null results retained and reported.**

---

## 6. What would make this project fail

Write these on a sticky note:

- Charts with no argument attached.
- Hand-typed numbers in the prose that don't match the code.
- Pooling the Crunchbase and India datasets as if they were one series.
- Treating 2013's apparent crash as real.
- Comparing nominal dollars across a decade.
- Hiding the 2013 cutoff instead of framing it.
- Claiming causality from a correlation in H5.
- Quietly widening the green definition until a result goes significant.
- A limitations section that says "future work could use more data".

---

## 7. Report outline

Target 3,500–4,500 words excluding figures, tables, references and appendices.
Restructured at build step 3 around the double gap.

**Title page** — title, name, USN, course code, date, word count.

**Abstract** (~200 words). The measurement problem, the data, the method, the double gap
with numbers, the advanced-economy benchmark result, one-sentence implication.

**1. Introduction** (~500 words)
Green entrepreneurship as the private-sector channel of the climate transition. The
needs-versus-flows mismatch, with the CPI figures. The research gap: deal-level evidence
on emerging-market green finance is rare because it is paywalled. State the four RQs.
State the contribution: not a measurement of the emerging-market green capital regime,
but a measurement of **why that regime cannot be measured in open data**, plus a
benchmark case for the capital-model mismatch.

**2. Background and related work** (~600 words)
Green entrepreneurship in emerging economies, institutional voids, the Porter hypothesis.
Cleantech 1.0 and the MIT post-mortem. The missing middle and currency risk. Current
climate finance geography. Close by stating the gap this paper fills.

**3. Data** (~650 words)
Sources, licences, coverage. Why the open-data frontier stops in 2013 and why that window
is the right one. The join between the relational and flat Crunchbase datasets, **including
that they are different vintages** and what that bounds. Enrichment layers. Attrition
ledger. Country recovery and the vanity-TLD refusals. The negative result on taxonomy
richness: emerging-market companies carry *more* tags, not fewer, so the bias is in which
companies exist rather than how well they are described.

**4. Methodology** (~700 words)
Green classifier: three tiers, lexicon, exclusions, κ = 0.85, sub-domains. Bloc
assignment: time-varying, China and LDCs separated, robustness alternatives. Deflation.
Truncation, with coverage growth as the primary argument. Statistical approach and the
multiple-comparison correction. The pre-commitments. One paragraph on reproducibility.

**5. The double gap** (~700 words, Figures 1–4, Table 1) — **the headline section**
Gap one: coverage against economic weight, as the denominator check. Gap two: green rate
conditional on dataset membership, by bloc, with intervals, the upper bound and the
leave-one-out range. The `general_unspecified` rate as a measurement finding in its own
right — the taxonomy cannot resolve green sub-domains in emerging markets, because 26 of
28 emerging-market green companies carry no tag more specific than "Clean Technology".
Then the careful part: what the absence does and does not license, with the instrument
argument given as external evidence and the competing explanation left open.

**5a. The gap is a capital-intensity gap** (~550 words, Figure 1b, Table 2) — **primary finding**
Sector composition as a result in its own right, not a control. Emerging-market venture
capital concentrated in capital-light consumer internet and avoided capital-intensive,
long-horizon, R&D-heavy sectors as a class. The representation ladder: biotech 0.11,
hardware 0.31, enterprise 0.34, cleantech 0.51, against e-commerce 3.43 and travel 3.60.
The regression: log representation ratio on log median advanced-economy deal size,
elasticity −1.19 [−1.64, −0.75], R² = 0.60, 23 sectors, proxy built from advanced-economy
data only. Cleantech's residual is +1.92× [0.75×, 4.91×], so a green-specific deficit is
ruled out while outperformance is not confirmed. State what this licenses and what it
does not: the gap is real, and it is a capital-intensity gap that green sits inside.

**6. The advanced-economy benchmark, and what each null says about the record**
(~1,200 words, Figures 5–10, Tables 2–4)

H2, H3 and H4 on green against non-green within advanced economies, as the benchmark case
for the Gaddy et al. capital-model mismatch. Finding first, then evidence, then the
verdict line and the falsification condition.

**Structural requirement: every subsection closes with one line tying its emerging-market
arm back to the measurement thesis.** The nulls are not separate disappointments; they are
the same finding arriving six times, and the section is written so a reader cannot miss
that. The six routes:

1. **H2** — the emerging-market arm does not exist. Six year-cells of 1–12 green deals;
   no difference-in-differences is possible.
2. **H3** — the emerging-market arm is null *by construction*, with the bias direction
   stated before the numbers: equity-coded project finance understates non-dilutive share
   on both sides and more so for emerging markets.
3. **H4** — **zero** emerging-market green seed entrants across thirteen years, and the
   advanced-economy A→B pool is 13 companies. The scale-up step the missing-middle
   literature points to is unobservable in the open record.
4. **H5** — the country panel runs on 22 countries, 20 of which have an electricity
   deficit of exactly zero. The need indicators cannot be tested because need-afflicted
   countries have too few green deals to enter the panel.
5. **The taxonomy** — 88.2% of emerging-market green deals carry no sub-domain more
   specific than "Clean Technology". The record cannot say what *kind* of green.
6. **The instrument coding** — a pre-declared venture-stage criterion fails because
   Crunchbase codes infrastructure project equity as ordinary venture rounds. The record
   cannot say what *kind* of capital.

Close the section by stating that these are six independent routes to one conclusion.

**7. Where the capital goes** (~450 words, Figure 11, Table 5)
H5 at country level, with the power situation stated up front and CIs on every ρ.

**8. What the open record cannot answer** (~450 words, Figure 12)

Open with the claim the paper is actually entitled to make: **the capital-regime question
is not answerable from open data, and that is the finding.** Not "more data would help" —
the specific, demonstrated statement that the five structural questions this project set
out to ask each fail for a different, independently verifiable reason, and that the
failure is a property of the data infrastructure rather than of the analysis.

Then the continuity probe.
The continuity probe. Indian startup funding 2015–2020, caveated as non-comparable in
taxonomy, and itself yielding only 54 green deals — which is a continuation of the
measurement finding, not an escape from it. Then triangulation against current secondary
evidence: CPI's 14–17% EMDE share, Net Zero Insights on falling graduation rates,
Tracxn's India trajectory. **Bank the structural-change observation:** non-dilutive
instruments were 7.1% of in-window deals in 2000–2012, and Net Zero Insights reports
non-dilutive capital *rising* as equity shrinks in 2025. State plainly which signatures
appear to have persisted, and that this section is suggestive, not a test.

**9. Discussion** (~400 words)
What follows for the data infrastructure of the field, first — that is where this paper
bites. Then policy: where concessional and blended capital would bind. Then founders.

**10. Limitations and threats to validity** (~400 words)
Coverage bias first and in full. The 35-deal emerging-market sample and everything it
forbids. Selection into Crunchbase. The two-vintage join and the 6.5% under-recording.
Right-censoring. Undisclosed amounts. Taxonomy anachronism. No causal identification in
H5. Taxonomy sensitivity.

**11. Conclusion** (~200 words)
Three findings, one implication, one concrete next step that is actually actionable.

**Reproducibility statement.** Commit hash, Python version, dataset SHA256s, runtime,
one-line reproduce instruction.

**References.** Numbered, consistent style, every in-text citation resolving.

**Appendix A** — full green lexicon and exclusion list with reasons, plus the ratified
manual-exclusion decisions.
**Appendix B** — country-to-bloc mapping, overrides, and the country-recovery rules
including the refused vanity TLDs.
**Appendix C** — robustness: strict vs broad green, static vs time-varying blocs,
bare-energy flag on and off, strict vs angel-inclusive seed.
**Appendix D** — full test family with raw and BH-adjusted p-values and effect sizes.
**Appendix E** — attrition ledger.
**Appendix F** — leave-one-out sensitivity on every emerging-market headline number.
**Appendix G** — instrument `funding_round_type` × `funding_round_code` contingency table.
**Appendix H** — mirror vintage comparison.

---

## 8. Figure plan

Twelve figures. Each has a job. If a figure has no job, cut it. Revised at build step 3:
the old Figure 5 (green sub-domain mix, EM vs AE) is **cut** — at 91.2%
`general_unspecified` on a 35-deal base the comparison is dead in every form, including
conditional on having a specific sub-domain. The double-gap exhibit replaces it.

| # | Figure | Job |
|---|---|---|
| 1 | Green rate conditional on dataset membership, by bloc, with Wilson intervals, upper bound overlaid | **The headline.** Gap two |
| 2 | Bloc share of recorded deals against bloc share of world GDP, by year | Gap one, as the denominator check |
| 3 | Green rate by bloc and year, cell sizes annotated, EM cells flagged as untestable | Gap two over time, honestly |
| 4 | `general_unspecified` share by bloc, with the specific sub-domains stacked | The taxonomy cannot resolve EM green |
| 5 | Global green venture funding 2000–2012, deals and real dollars, 2008 and 2011 annotated | Establish the cycle |
| 6 | Green as a share of all venture funding over time, AE, with EM plotted untested | Green is a cycle within a cycle |
| 7 | Indexed drawdown, AE-green vs AE-non-green, 2007 = 100 (H2) | Amplification |
| 8 | DiD coefficient plot with pre-trend panel (H2) | The formal test |
| 9 | Instrument mix, stacked area by green status (H3) | Non-dilutive dependence |
| 10 | Stage graduation funnel and odds ratios with CIs, green vs non-green (H4) | The missing middle |
| 11 | Green funding intensity vs GDP per capita and vs climate-need indicators, small-multiple scatter with Spearman ρ and CIs (H5) | Capital follows markets |
| 12 | Continuity probe: India 2015–2020 alongside the 2000–2012 series, visually separated and labelled non-comparable | Persistence |

Plus one small, clearly-labelled censoring-artefact figure in the methodology section:
monthly deal counts for 2011, 2012 and 2013 overlaid, showing December 2013 at 3.83% of
its year against a 7.52% baseline.

---

## 9. Reference list to build from

Populate `report/references.bib` with at least these, verifying each before citing:

1. Gaddy, B., Sivaram, V., Jones, T., Wayman, L. (2017). Venture capital and cleantech:
   The wrong model for energy innovation. *Energy Policy*, 102, 385–395. (MIT Energy
   Initiative working paper, 2016.)
2. Climate Policy Initiative. *Global Landscape of Climate Finance 2025* and *2026*,
   including the EMDE Spotlight.
3. Climate Policy Initiative. *Accelerating Sustainable Finance for Emerging Markets and
   Developing Economies*.
4. Tracxn. *India Climate Tech 2026 Report*.
5. Net Zero Insights. *State of Climate Tech 2025* and the H1/Q3 2025 updates.
6. Dealroom. *Climate Tech* deep dive.
7. Sightline Climate. H1 2025 climate tech funding review.
8. World Bank. *World Bank Country and Lending Groups*, FY2026 income classification.
9. Our World in Data. World Bank income groups dataset; CO₂ and energy datasets.
10. Crunchbase. *Crunchbase 2013 Snapshot*, CC BY 4.0 (via Kaggle).
11. A recent systematic review of green entrepreneurship in emerging economies — pick one
    from *Business Strategy and the Environment* or *International Entrepreneurship and
    Management Journal* and read the abstract before citing it.
12. Porter, M. E., van der Linde, C. (1995). Toward a new conception of the
    environment–competitiveness relationship. *Journal of Economic Perspectives*, 9(4).

**Verify every citation before it goes in the bib file.** A fabricated reference is worse
than a missing one, and it is the single easiest thing for a marker to catch.