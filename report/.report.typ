#import "template.typ": conf, exhibit, method-exhibit, CAPTIONS
#CAPTIONS.update((
  "fig_01a_double_gap": [#text(fill: rgb("#141413"), weight: "medium")[In the record, an emerging-market company is half as likely to be green.] Green share of recorded venture deals by bloc, 2000–2012. Crunchbase 2013 Snapshot (CC BY 4.0); authors' calculations. n = 41,105 deals, 2,174 green; bloc rows sum to the total. Intervals are Wilson score. Headline is raw classifier output; bias-corrected risk ratio 0.44, curated 0.40 (Appendix C).],
  "fig_01b_sector_ladder": [#text(fill: rgb("#141413"), weight: "medium")[Capital intensity drives the pattern, and green beats its prediction.] Emerging-market representation relative to advanced economies across 23 sectors, 2000–2012. Capital intensity is median advanced-economy deal size in constant 2015 USD, so the proxy cannot be contaminated by the emerging-market composition it explains. Segments run from predicted to observed; intervals are residual 95% CI.],
  "fig_02_coverage_gdp": [#text(fill: rgb("#141413"), weight: "medium")[Emerging markets hold a fifth of world GDP and a fiftieth of the venture record.] Emerging-market share of world GDP against its share of recorded venture deals, 2000–2012. GDP shares are computed over the same country set the bloc panel covers, so the two series are comparable by construction. This is the denominator check: it establishes that the conditional green-rate gap is not this coverage gap restated.],
  "fig_03_rate_by_year": [#text(fill: rgb("#141413"), weight: "medium")[The two rates met in 2008, at the peak of Cleantech 1.0, then diverged.] Green share of recorded deals by bloc and year, 2000–2012. No emerging-market year-cell reaches the minimum cell size of 30 green deals; the largest is 12, in 2008. No per-year test is reported and this figure is descriptive only. Counts are printed beside each emerging-market point so the reader can see the precision available.],
  "fig_04_subdomain": [#text(fill: rgb("#141413"), weight: "medium")[The taxonomy cannot say what kind of green an emerging-market company is.] Share of green deals resolved to a specific sub-domain, by bloc, 2000–2012. The eleven specific sub-domains are solar, wind/hydro/geothermal, biofuels, storage, efficiency and smart grid, electric mobility, water, waste and circular, sustainable agriculture, green building, and environmental monitoring. This figure replaces the planned sub-domain mix comparison, which the measurement failure shown here makes impossible.],
  "fig_05_cycle": [#text(fill: rgb("#141413"), weight: "medium")[Green deal sizes fell far faster than non-green within the same stages.] Green deals and disclosed green funding, all blocs, 2000–2012. Constant 2015 USD. n = 2,174 green deals, 1,994 with a disclosed amount. Counts and dollars are separate series because undisclosed-amount rates differ by instrument and bloc. The cheque-size claim is the within-stage comparison: green −50.4% against non-green −1.1%, difference −49.3pp [−69.3, −22.4], bootstrapped over 10,000 draws on clean stage codes. The pooled median falls alike in both and is composition-confounded for each. Robust to the start year, sensitive to the end year (§6.1).],
  "fig_06_share_crossover": [#text(fill: rgb("#141413"), weight: "medium")[From 2005, green took a bigger share of venture dollars than of deals.] Green as a share of all recorded deals and of all disclosed dollars, 2000–2012. Constant 2015 USD. A dollar share above the count share means the average green cheque exceeded the average cheque overall, which is consistent with green being capital-intensive; it does not test the cross-sector elasticity. The ordering reverses before 2005 on thin cells: 2001 n=1, 2002 n=4, 2003 n=5, 2004 n=11.],
  "fig_07_crisis": [#text(fill: rgb("#141413"), weight: "medium")[The crisis hit green venture funding and left non-green growing.] Deal volume indexed to 2007, by bloc and green status, 2000–2012. The emerging-market green series is not drawn: its 2007 base year holds a single deal, so the index would reach 1,200 in 2008. No difference-in-differences coefficient is shown: green volume was already growing 0.254 log-points per year faster than non-green before the event window (p = 0.001), so parallel trends fail and the design does not identify a causal effect.],
  "fig_08_instruments": [#text(fill: rgb("#141413"), weight: "medium")[Green ventures lean harder on grants and debt than non-green ones do.] Non-dilutive share of deals by bloc and green status, 2000–2012. Non-dilutive instruments are grants, debt financing and post-IPO debt. Advanced-economy comparison: risk ratio 1.433 [1.256, 1.636], p = 1.2×10⁻⁷. Project finance that is debt or concessional in substance but coded as an equity round understates the non-dilutive share on both sides, and more so for emerging markets; that bias direction was stated before these numbers were computed.],
  "fig_09_power_wall": [#text(fill: rgb("#141413"), weight: "medium")[Every emerging-market test fails on the same wall, for different reasons.] Observations available against the pre-registered minimum cell size, across H2–H5. The minimum cell size of 30 was fixed in config before any hypothesis was tested, and no bar clears it. These are five distinct failures rather than one repeated. The emerging-market green sample of 34 does itself clear the threshold; the non-dilutive cell the instrument test depends on holds 3. Three figures that would have plotted these quantities as estimates were cut rather than drawn.],
  "fig_10_depth_need": [#text(fill: rgb("#141413"), weight: "medium")[Capital tracks market depth; whether it tracks need cannot be measured here.] Green funding intensity across 22 countries with at least three green deals, 2000–2012. Spearman rank correlation with a bootstrap interval over 10,000 draws. The planned small-multiple of need indicators is not drawn; panel (b) shows why. A scatter against a regressor on which 20 of 22 countries record exactly zero would read as a relationship and is not one. Green funding is highly concentrated: Gini 0.917, top five countries hold 89.9% of green dollars.],
  "fig_11_continuity": [#text(fill: rgb("#141413"), weight: "medium")[A later window in one large emerging market reproduces the same scarcity.] Green deals per year. Two different instruments measuring two different populations; the panels share no axis. Left: Crunchbase 2013 Snapshot, emerging markets excluding China and LDCs, 34 green deals. Right: the Indian startup funding scrape, 3,036 dated deals of which 54 are green under the same lexicon. Never pooled: taxonomies and amount conventions are not compatible, and no category_code exists in the Indian data so Tier A cannot fire. 2020 is a partial year and is excluded.],
  "fig_m1_censoring": [#text(fill: rgb("#141413"), weight: "medium")[Only December 2013 is censored, which is why the window closes at 2012.] Monthly deals as a share of their own year, 2011–2013. Expressing each month as a share of its own year removes the level difference between years so the shapes are comparable. The disclosed-amount rate is flat across these years (88.99 / 88.61 / 88.44%), so dollars are not differentially censored either. The window still closes at 2012-12-31, on the coverage-growth argument rather than this one (§4).],
  "fig_m2_elasticity": [#text(fill: rgb("#141413"), weight: "medium")[Emerging-market representation falls roughly in proportion to capital intensity.] 23 sectors, 2000–2012. Ordinary least squares on logs; the line is the model's fitted values. Elasticity −1.19 [−1.64, −0.75], R² = 0.60, p = 1.5×10⁻⁵. The proxy uses advanced-economy deals only. The secondary proxy, median cumulative funding per company, gives an elasticity of −0.96 with R² 0.69.],
))
#show: conf.with(
  title: "The Green Capital Gap",
  subtitle: "A deal-level analysis of cleantech venture funding in emerging economies, 2000–2012",
  shorttitle: "The Green Capital Gap",
  footerright: "RV College of Engineering",
  authors: ((name: "Kaizer Dewaswala", usn: "1RV23IS058"), (name: "Md Asif Ali", usn: "1RV23IS069"), (name: "Shaswat Kumar", usn: "1RV23IS110"), (name: "Vansh Bharadwaj", usn: "1RV23IS134"),),
  guide: "Prof. ChandraKumar R",
  institution: "Department of Information Science & Engineering, RV College of Engineering",
  course: "Final Year Chapter Deliverable",
  date: "October 2026",
  wordcount: "2,237",
)

= The Green Capital Gap
<the-green-capital-gap>
#strong[A deal-level analysis of cleantech venture funding in emerging economies, 2000--2012]

#divider()

== Abstract
<abstract>
Emerging-market green entrepreneurship is almost absent from the open venture record, and
what absence there is turns out not to be about green. Across 41,105
funding rounds from the Crunchbase 2013 Snapshot, classified by a three-tier green
classifier with inter-tier agreement of κ = 0.850, an emerging‑market
company already indexed in the record is #strong[half as likely to be green as an
advanced‑economy one]: 2.60% against 5.43%, a risk ratio of
0.479 \[0.343, 0.669\]. That gap survives every green definition, every bloc scheme, and a
permutation test in which #strong[zero of 1,000] label shuffles reach the
observed value.

The gap is #strong[not green‑specific]. Across 23 sectors, emerging‑market
representation falls roughly in proportion to capital intensity, with an elasticity of
−1.19 \[−1.64, −0.75\] explaining 0.60 of the cross‑sector
variance; biotech sits further below proportionate representation than cleantech does.
Cleantech's residual from that fit is #strong[positive] at 1.92×
\[0.75×, 4.91×\], so a green‑specific penalty is ruled out.

Three of the five hypotheses could not be resolved, each for a different and separately
verifiable reason, and together with three further measurement failures they give #strong[six
independent routes to one conclusion: the capital-regime question is not answerable from
open data.] That is the paper's finding, not its limitation.

#divider()

== 4. Methodology
<methodology>
=== 4.1 The green classifier
<the-green-classifier>
Green status is assigned by a three-tier classifier whose every pattern lives in
`config/green_lexicon.yaml`, not in code. Tier A is the snapshot's own `category_code`
flag. Tier B is a case-insensitive lexicon of 135 regular expressions
over the concatenated taxonomy, tag and description fields, mapped to eleven sub‑domains.
Tier C is an exclusion list that vetoes Tier B hits.

The headline definition is `green = TierA OR (TierB AND NOT TierC)`. Tier C never vetoes
Tier A: a company the snapshot itself flags as cleantech is not removed by a lexicon
exclusion. Agreement between the two independent tiers is κ = 0.850 on
funded companies carrying a taxonomy.

Three design choices in the lexicon are worth stating because each prevents a class of
false positive. The bare token #emph[green] is not a trigger, only green-compounds: "Green" is
a common surname and place name, and admitting it then subtracting the errors in Tier C is
a losing game. The same applies to #emph[carbon], #emph[waste], #emph[organic] and #emph[clean]. A fossil-fuel
veto was added after inspection showed that Crunchbase's `Energy` bucket mixes renewables
with oil, gas and coal, so without it an upstream petroleum company classified as green.
312 companies are vetoed in total, each with a recorded pattern and
reason, reproduced in Appendix A.

=== 4.2 Bloc assignment
<bloc-assignment>
Each deal takes the bloc its country held #strong[in the year the deal closed], derived from
the World Bank's historical income classification. A deal in Poland in 2004 is not a deal
in an advanced economy; a deal in Poland in 2013 is. China is reported separately
throughout, mirroring Climate Policy Initiative's practice, and least developed countries
are separated on the UN list with graduation years applied per year.

Country codes required repair. The snapshot carries withdrawn ISO-3166-3 codes, and
108,563 in-window deals carry no country at all. Recovery used the
flat mirror's own country field first and domain top-level domains second, under an
explicit allow-list. That allow-list is the methodological point: several country-code
domains belong to emerging or least developed countries and are sold worldwide as vanity
domains, so a naive mapping would have manufactured 127 Tuvaluan and 18 São Toméan
ventures out of domain marketing, in a project whose finding is that such ventures are
absent. All 23 refusals are enumerated in Appendix B.

=== 4.3 Window, deflation and censoring
<window-deflation-and-censoring>
Amounts are converted to constant 2015 USD with the US GDP deflator; both the nominal and
the real column are retained. Undisclosed amounts are encoded in the source as a literal
zero rather than as null, which would have dragged every median toward zero while
reporting complete coverage; 6,000 rows are affected and are
nulled, never imputed.

The window closes at 2012-12-31. The usual argument for truncating is
recording lag, and that argument is secondary here. The primary one is differential
coverage growth: Crunchbase's coverage expanded over the period and expanded faster for
emerging markets than for the United States, which was near saturation early, so the final
year is the most coverage-contaminated year for precisely the quantity the headline
measures. #ref(<fig-censoring>) shows the censoring boundary measured rather than assumed.

#method-exhibit("fig_m1_censoring") <fig-censoring>
=== 4.4 Statistical approach
<statistical-approach>
Proportions carry Wilson score intervals rather than normal approximations, which
misbehave on small proportions. Deal-size comparisons use rank-based tests because the
distributions are heavy-tailed. Bootstrap intervals use
10,000 resamples from a seeded generator. A minimum cell size of 30 was
fixed in configuration before any hypothesis was tested, and no significance test is
reported on a cell below it.

Effect sizes are reported alongside every p-value. With tens of thousands of deals almost
any difference reaches significance, so the question a reader needs answered is whether it
matters: the instrument-mix χ² in §6.3 is significant at p = 1.2×10⁻⁷ on a Cramér's V of
0.027, which is why the risk ratio is quoted in the text instead.
28 tests across the family carry Benjamini-Hochberg adjusted p-values
in Appendix D, of which 9 survive correction.

The capital‑intensity model in §5.3 regresses log emerging‑market representation on log
median advanced‑economy deal size across 23 sectors. The proxy is built
from advanced‑economy deals only, so it cannot be contaminated by the emerging‑market
composition it is used to explain. #ref(<fig-elasticity>) shows the fit.

#method-exhibit("fig_m2_elasticity") <fig-elasticity>
=== 4.5 Specifications fixed in advance
<specifications-fixed-in-advance>
Four judgement calls that change a headline number were fixed in configuration, with their
reasoning recorded, before the relevant result was computed: whether a bare `Energy` tag
admits a company as green, whether angel rounds count as funnel entry for the graduation
analysis, that H3's grant arm is descriptive only below the minimum cell size, and that
H4's extended observation window is permitted because it conditions on sample entry. Each
is run both ways in the robustness appendix. Where a pre-commitment's assumption turned
out to be wrong --- H4's assumed a direction when the binding failure was power --- that is
recorded as void rather than quietly satisfied.

=== 4.6 Reproducibility
<reproducibility>
This report was produced by 4 authors --- Kaizer Dewaswala (1RV23IS058); Md Asif Ali (1RV23IS069); Shaswat Kumar (1RV23IS110); Vansh Bharadwaj (1RV23IS134) --- under the
guidance of Prof.~ChandraKumar R at the Department of Information Science & Engineering, RV College of Engineering. That list lives in
`report/metadata.yaml` and is read from there by the title page, this statement and the
README; it is not restated anywhere.

`make all` reproduces every number from a clean checkout. All thirteen source files carry
recorded SHA256 checksums, verified on each run, so a changed upstream file fails the
build rather than silently changing a result. Every statistic in this report is injected
from `outputs/findings.json`\; the renderer fails on an unresolved placeholder, so no
number here was typed by hand. Commit d9d2854, Python 3.11.9, seed
\20251001.

#divider()

== 5. The double gap
<the-double-gap>
=== 5.1 Emerging markets are a fiftieth of the record and a fifth of world GDP
<emerging-markets-are-a-fiftieth-of-the-record-and-a-fifth-of-world-gdp>
Over 2000--2012 emerging markets held 15.3--22.7% of world GDP and
1.7--6.4% of recorded venture deals, an under-representation of
2.8--8.8× (#ref(<fig-coverage>)). This is the coverage gap, and it is
the reason the paper's headline result is measured #emph[within] the dataset rather than
against the world.

#exhibit("fig_02_coverage_gdp") <fig-coverage>
=== 5.2 Conditional on being in the record, an emerging‑market company is half as likely to be green
<conditional-on-being-in-the-record-an-emergingmarket-company-is-half-as-likely-to-be-green>
1,309 emerging‑market deals carry 2.60% green
\[1.86, 3.61\], against 5.43% \[5.20, 5.66\] across 37,896
advanced‑economy deals. The difference is −2.83 percentage points
\[−3.72, −1.94\]; the risk ratio is 0.479 \[0.343, 0.669\], z-test
p = 7.5×10⁻⁶, Fisher's exact p = 1.3×10⁻⁶ (#ref(<fig-double-gap>)).

#exhibit("fig_01a_double_gap") <fig-double-gap>
Both numerator and denominator are drawn from companies Crunchbase chose to index, so the
result does not depend on the coverage gap in §5.1. Counting every deal with no recorded
country as emerging‑market --- the most generous possible treatment --- gives
3.46% and a risk ratio of 0.637, p = 6.3×10⁻⁶.

China, reported separately throughout, sits with the advanced economies rather than with
emerging markets. #ref(<fig-rate-by-year>) shows the two rates by year, with every
emerging‑market cell annotated by its count.

#exhibit("fig_03_rate_by_year") <fig-rate-by-year>
#strong[Verdict: Supported.] Falsified if the emerging‑market green rate were
indistinguishable from the advanced‑economy rate, or if the gap vanished under the upper
bound.

=== 5.3 The gap is a capital‑intensity gap
<the-gap-is-a-capitalintensity-gap>
Emerging-market venture capital in this period concentrated in capital-light consumer
internet and avoided capital-intensive sectors as a class. Regressing log
emerging‑market representation on log median advanced‑economy deal size across
23 sectors gives an elasticity of −1.19
\[−1.64, −0.75\], p = 1.5×10⁻⁵, R² = 0.60 (#ref(<fig-ladder>)). Doubling a sector's capital intensity roughly halves its
emerging‑market representation.

Cleantech sits #strong[above] the position that fit predicts, at
1.92× \[0.75×, 4.91×\] of its predicted
representation. The interval includes 1, so outperformance is not established; what is
established is that there is no green‑specific penalty once capital intensity is
accounted for. Biotech, by contrast, sits below its own prediction.

#exhibit("fig_01b_sector_ladder") <fig-ladder>
Green also took a larger share of venture dollars than of venture deals from 2005 onward
(#ref(<fig-dollar-share>)), which is consistent with green being capital-intensive
without testing the cross‑sector elasticity above.

#exhibit("fig_06_share_crossover") <fig-dollar-share>
=== 5.4 The taxonomy cannot say what kind of green
<the-taxonomy-cannot-say-what-kind-of-green>
88.2% of emerging‑market green deals carry no sub‑domain more
specific than "Clean Technology", against 67.9% in advanced
economies (#ref(<fig-subdomain>)). The mechanism is direct: 26 of the 28 emerging‑market green
companies carry no other taxonomy tag at all. The planned sub‑domain mix comparison was
cut, because the measurement failure shown here makes it impossible.

#exhibit("fig_04_subdomain") <fig-subdomain>

#divider()

== 6. The advanced‑economy benchmark, and what each null says about the record
<the-advancedeconomy-benchmark-and-what-each-null-says-about-the-record>
Advanced economies are the one bloc where the record is dense enough to test the
structural hypotheses. They are the benchmark case for the capital-model mismatch Gaddy
et al.~identify. Each subsection closes by stating what its emerging‑market arm shows
about the record itself.

=== 6.1 Green deal sizes fell far faster than non-green within the same stages
<green-deal-sizes-fell-far-faster-than-non-green-within-the-same-stages>
Between 2007 and 2012, within named funding stages, green deal sizes fell
−50.4% against −1.1% for non-green --- a difference of
−49.3 percentage points \[−69.3, −22.4\], bootstrapped over
10,000 draws (#ref(<fig-cycle>)).

The pooled median falls by about the same amount in both groups and settles nothing: it
is composition-confounded for each, because the platform recorded far more small rounds
as it matured. All 5 start‑end pairs running to the close of the
window are negative, spanning −69.9 to −21.5 percentage points, and the
headline figure is their median, so the direction is robust to the choice of start year.
It is #strong[not] robust to the choice of end year: across all 17 admissible pairs the
difference is negative in 71%, and every positive pair stops in 2006 or 2009--11, before
the decline has run its course. The claim the grid supports is a direction that holds to
the close of the window, with a magnitude that depends on where the comparison starts.

This is a size pattern, not an investor motive. The rotation out of hardware that Gaddy
et al.~document is cited here as external evidence, not as something this dataset shows.

#exhibit("fig_05_cycle") <fig-cycle>
=== 6.2 The crisis hit green and spared non-green, but the test does not identify it
<the-crisis-hit-green-and-spared-non-green-but-the-test-does-not-identify-it>
Across 2008--09, advanced‑economy green deals contracted
−26.5% while non-green #strong[grew]
13.5% (#ref(<fig-crisis>)).

#exhibit("fig_07_crisis") <fig-crisis>
The difference‑in‑differences designed to test this does not identify it. Green deal
volume was already growing 0.254 log-points per year faster than non-green
before the event window, \[0.101, 0.408\], p = 0.001. Parallel trends fail,
so the design never recovered a causal effect and there is no null to report.

#strong[Verdict: Not testable --- identifying assumption failed.] The contraction figures above are descriptive.

#emph[What the emerging‑market arm shows about the record:] it does not exist. The largest
emerging‑market green year‑cell holds 12 deals.

=== 6.3 Green capital is less dilutive than non-green
<green-capital-is-less-dilutive-than-non-green>
Within advanced economies, 10.41% of green deals use
non‑dilutive instruments --- grants, debt, post‑IPO debt --- against
7.26% of non-green deals. The risk ratio is 1.433
\[1.256, 1.636\], p = 1.2×10⁻⁷ (#ref(<fig-instrument>)).

#exhibit("fig_08_instruments") <fig-instrument>
The χ² on the full instrument mix is also significant, but its Cramér's V of
0.027 falls below the conventional threshold for a small effect: with tens of
thousands of deals the test detects a negligible association, and the risk ratio on the
quantity the hypothesis is about is the interpretable figure.

#strong[Verdict: Supported for the advanced‑economy benchmark case.]

#emph[What the emerging‑market arm shows about the record:] it is null by construction. The
record codes infrastructure project equity as ordinary venture rounds, which understates
non‑dilutive share on both sides and more so for emerging markets, where independent power
producers are seven of 28 green companies. The direction of that bias was stated before the
numbers were computed. On 34 deals the arm could not have settled the
question either way.

=== 6.4 The scale-up step is unobservable
<the-scale-up-step-is-unobservable>
Conditional on raising seed capital, advanced‑economy green companies reached Series A
with an odds ratio of 1.30 \[0.65, 2.60\] against non-green, p = 0.458. The
interval spans 1 and identifies no direction.

It cannot. The advanced‑economy green seed cohort holds 40
companies and the Series A to Series B pool --- the specific missing‑middle transition ---
holds 13. No model of that transition is reported, under any specification.

#strong[Verdict: Underpowered --- cannot determine.]

#emph[What the emerging‑market arm shows about the record:] there are
0 emerging‑market green seed entrants across thirteen years. The
scale-up step the missing‑middle literature identifies as decisive cannot be observed at
all.

=== 6.5 Capital tracks market depth; whether it tracks need cannot be determined
<capital-tracks-market-depth-whether-it-tracks-need-cannot-be-determined>
Across 22 countries with enough green activity to measure, green
funding per capita correlates with GDP per capita at ρ = 0.674
\[0.298, 0.866\] (#ref(<fig-depth>)).

#exhibit("fig_10_depth_need") <fig-depth>
Green funding is extraordinarily concentrated: a Gini of
0.917, with the top five countries holding 89.9% of all green dollars
across 42 countries.

The need limb cannot be tested. Twenty of the 22 panel countries
record an electricity-access deficit of exactly zero; the regressor is in substance a
dummy for one country. An income‑controlled coefficient on it appeared positive and
significant, met the pre‑registered falsification condition, and survived both
leave‑one‑out and collinearity checks before a degenerate-variance check rejected it.

#strong[Verdict: Partially supported.]

#emph[What this shows about the record:] countries with real energy-access deficits have too
few green deals to enter the panel. The need indicators were not tested and found null;
they could not be tested.

=== 6.6 Six routes, one conclusion
<six-routes-one-conclusion>
Three hypotheses were unresolved, each for a different stated reason: H2's identifying
assumption failed, H4 had 13 companies at the transition it exists to
measure, H5's need regressor had no variance. Three further failures are properties of
the record rather than of any hypothesis: 88.2% of
emerging‑market green deals carry no specific sub‑domain; a pre-declared venture‑stage
criterion failed because project finance is coded as venture rounds; and H3's
emerging‑market arm is biased by that same coding in a direction stated in advance.

#ref(<fig-cells>) puts the first four on one scale, against the minimum cell size fixed
in config before any hypothesis was tested. No cell clears it.

#exhibit("fig_09_power_wall") <fig-cells>
These are six independent routes to one conclusion. The open venture record cannot
support the capital-regime analysis the field needs.
