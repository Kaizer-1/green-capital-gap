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
on Kaggle. It is genuine, deal-level, global, and it covers ~90,000 funding rounds with
dates, amounts, round types and country codes.

Its weakness is obvious: it stops in 2013.

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

**RQ1.** How did green venture funding in emerging economies evolve relative to advanced
economies across the Cleantech 1.0 cycle (2000–2012), in deal counts and in real dollars?

**RQ2.** Does the emerging-market green funding regime differ *structurally* from the
advanced-economy one — in deal size, instrument mix and stage graduation — rather than
merely in scale?

**RQ3.** Within emerging economies, does green capital allocate toward climate and energy
*need*, or toward market depth and institutional quality?

**RQ4.** Do the structural signatures identified in 2000–2012 persist in contemporary
evidence on emerging-market green entrepreneurship?

---

## 4. Hypotheses

Each is falsifiable, each maps to one analysis module, each gets an explicit verdict.

### H1 — Deal share rose; dollar share did not
*Emerging markets increased their share of global green deal count over 2000–2012 by
substantially more than their share of global green dollars, implying a persistent and
possibly widening cheque-size gap.*

Tests: EM share of green deals and of green real dollars, annually, plotted together.
Median and IQR deal size by bloc by year, bootstrap CIs. Mann–Whitney U on the
EM-vs-AE green deal size distribution, pooled and by year.
Also compute the **undisclosed-amount rate by bloc and year** — if EM deals are
disproportionately undisclosed, the dollar series is biased and you must say by how much.

Falsified if: EM dollar share tracks EM deal share within the bootstrap CI.

### H2 — The bust was amplified in emerging markets
*The post-2008 contraction in green funding was deeper and longer in emerging markets than
in advanced economies, and deeper than the contraction in non-green funding within
emerging markets.*

Tests: indexed time series (2007 = 100) for four series — EM-green, AE-green, EM-nongreen,
AE-nongreen. Peak-to-trough drawdown and time-to-recovery for each. Difference-in-differences
on log deal volume with a `green × EM × post2008` interaction, year fixed effects, robust
SEs. Plot and formally check pre-trends.

Falsified if: the triple interaction is indistinguishable from zero, or pre-trends diverge.
**If pre-trends fail, downgrade to descriptive and say so in the text.**

### H3 — Emerging-market green capital is less dilutive
*Green ventures in emerging markets draw a higher share of funding from grants, debt and
other non-venture instruments than green ventures in advanced economies, and than
non-green ventures in emerging markets.*

Tests: instrument-mix shares by bloc × green status, by count and by dollars. χ² test of
independence with Cramér's V for effect size. Stacked-area evolution over time.
Watch the trap: `grant` and `debt_financing` rows have systematically different disclosure
rates — report counts and dollars separately.

Falsified if: EM green instrument mix is statistically indistinguishable from AE green.

### H4 — The scale-up step is where emerging markets lose
*Conditional on raising seed capital, green ventures in emerging markets are less likely
to reach Series A, and markedly less likely to reach Series B, than comparable advanced-
economy green ventures — with the largest gap at A→B, the "missing middle".*

Tests: build company-level funding histories from the deal table. Compute cohort
graduation rates seed→A and A→B by bloc × green status, by founding cohort, with
sufficient follow-up time (cohorts must have ≥3 years of observable window before the
2012 truncation — this materially restricts usable cohorts, say so). Logistic regression
on graduation with bloc, green, bloc × green, year fixed effects and sub-domain controls;
report odds ratios with CIs.

This is the hypothesis most likely to be underpowered. **Check cell sizes first. If n is
too small, report it as underpowered rather than stretching the definitions.**

Falsified if: the bloc × green interaction is null, or the gap is no larger at A→B than
at seed→A.

### H5 — Capital tracks market depth, not climate need
*Across emerging economies, country-level green funding intensity correlates with GDP per
capita and financial-market depth, and shows no positive association with indicators of
climate or energy need (CO₂ per capita, electricity access deficit, renewable share).*

Tests: country-level panel. Green funding per capita and green funding per unit GDP as
outcomes. Spearman rank correlations against GDP per capita, electricity access,
renewable share of final energy, CO₂ per capita. Gini coefficient and HHI of green
funding concentration across EM countries, compared with the same for non-green funding.
Top-5 country share over time. OLS with log GDP as a control to show whether need
indicators add anything.

Falsified if: need indicators show a positive, significant association after controlling
for income.

---

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

**Title page** — title, name, USN, course code, date, word count.

**Abstract** (~200 words). Problem, data, method, three headline findings with numbers,
one-sentence implication.

**1. Introduction** (~500 words)
Green entrepreneurship as the private-sector channel of the climate transition. The
needs-versus-flows mismatch in emerging economies, with the CPI figures. The research gap:
most evidence on emerging-market green finance is macro and aggregated; deal-level
evidence is rare because it is paywalled. State the four RQs. State what the paper
contributes.

**2. Background and related work** (~600 words)
Green entrepreneurship in emerging economies, institutional voids, the Porter hypothesis.
Cleantech 1.0 and the MIT post-mortem. The missing middle and currency risk. Current
climate finance geography. Close by stating the gap this paper fills.

**3. Data** (~600 words)
Sources, licences, coverage. Honest statement of why the open-data frontier stops in 2013
and why that window is the right one to study. The join between the relational and flat
Crunchbase mirrors. Enrichment layers. Attrition ledger table. Coverage-bias quantification.

**4. Methodology** (~700 words)
Green classifier: three tiers, lexicon, exclusions, κ, sub-domains. Bloc assignment:
time-varying, China and LDCs separated, robustness alternatives. Deflation. Truncation.
Statistical approach and the multiple-comparison correction. One paragraph on
reproducibility.

**5. Descriptive landscape** (~500 words, Figures 1–5)
Global green funding over the cycle. Bloc composition. Sub-domain mix and how it differs
between EM and AE — expect energy access, agriculture and water to be relatively larger
in EM, and advanced materials and storage relatively larger in AE. Country ranking within
EM.

**6. Hypothesis tests** (~1,200 words, Figures 6–11, Tables 1–4)
One subsection per hypothesis. Finding first, then evidence, then the verdict line and the
falsification condition. Do not narrate the analysis; report it.

**7. Does the pattern persist?** (~400 words, Figure 12)
The continuity probe. Indian startup funding 2015–2020 as an independent later window,
clearly caveated as non-comparable in taxonomy. Then triangulation against the current
secondary evidence in §2.2 above — CPI's 14–17% EMDE share, the falling graduation rates
Net Zero Insights reports, Tracxn's India trajectory, India's shrinking share of a
shrinking global pool. State plainly which structural signatures appear to have persisted
and which have not, and that this section is suggestive, not a test.

**8. Discussion** (~400 words)
What follows for policy: where concessional and blended capital would bind if the
missing-middle result holds. What follows for founders in emerging markets: instrument
mix, stage planning, the A→B wall. What follows for researchers and for the data
infrastructure of the field.

**9. Limitations and threats to validity** (~350 words)
Coverage bias first and in full. Selection into Crunchbase. Right-censoring. Undisclosed
amounts. The 2013 frontier and what it does and does not permit you to claim. No causal
identification in H5. Underpowered cells in H4 if applicable. Taxonomy sensitivity.

**10. Conclusion** (~200 words)
Three findings, one implication, one concrete next step that is actually actionable.

**Reproducibility statement.** Commit hash, Python version, dataset SHA256s, runtime,
one-line reproduce instruction.

**References.** Numbered, consistent style, every in-text citation resolving.

**Appendix A** — full green lexicon and exclusion list with reasons.
**Appendix B** — country-to-bloc mapping and overrides.
**Appendix C** — robustness tables: strict vs broad green, static vs time-varying blocs.
**Appendix D** — full test family with raw and BH-adjusted p-values and effect sizes.
**Appendix E** — attrition ledger.

---

## 8. Figure plan

Twelve figures. Each has a job. If a figure has no job, cut it.

| # | Figure | Job |
|---|---|---|
| 1 | Global green venture funding, 2000–2012, deals and real dollars on stacked panels, with the 2008 and 2011 events annotated | Establish the cycle |
| 2 | Green as a share of all venture funding, by bloc, over time | Show green is a cycle within a cycle |
| 3 | EM share of green deals vs EM share of green dollars (H1) | The headline divergence |
| 4 | Deal-size distributions by bloc, green vs non-green, log scale, violin or ridgeline (H1) | The cheque-size gap |
| 5 | Green sub-domain mix, EM vs AE, diverging bar | Different green, not just less green |
| 6 | Indexed drawdown, four series, 2007 = 100 (H2) | Amplification |
| 7 | DiD coefficient plot with pre-trend panel (H2) | The formal test |
| 8 | Instrument mix, stacked area by bloc × green (H3) | Non-dilutive dependence |
| 9 | Stage graduation funnel, EM vs AE green (H4) | The missing middle |
| 10 | Graduation odds ratios with CIs (H4) | The formal test |
| 11 | Green funding intensity vs GDP per capita and vs climate-need indicators, small-multiple scatter with Spearman ρ (H5) | Capital follows markets |
| 12 | Continuity probe: India 2015–2020 alongside the 2000–2012 EM series, visually separated and labelled as non-comparable | Persistence |

Plus one small, clearly-labelled censoring artefact figure in the methodology section.

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