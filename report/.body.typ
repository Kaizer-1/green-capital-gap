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

== 5. The double gap
<the-double-gap>
=== 5.1 Emerging markets are a fiftieth of the record and a fifth of world GDP
<emerging-markets-are-a-fiftieth-of-the-record-and-a-fifth-of-world-gdp>
Over 2000--2012 emerging markets held 15.3--22.7% of world GDP and
1.7--6.4% of recorded venture deals, an under-representation of
2.8--8.8× (#ref(<fig-coverage>)). This is the coverage gap, and it is
the reason the paper's headline result is measured #emph[within] the dataset rather than
against the world.

#exhibit("fig_02_coverage_vs_gdp", [Emerging-market share of world GDP against its share of recorded venture deals.]) <fig-coverage>
=== 5.2 Conditional on being in the record, an emerging‑market company is half as likely to be green
<conditional-on-being-in-the-record-an-emergingmarket-company-is-half-as-likely-to-be-green>
1,309 emerging‑market deals carry 2.60% green
\[1.86, 3.61\], against 5.43% \[5.20, 5.66\] across 37,896
advanced‑economy deals. The difference is −2.83 percentage points
\[−3.72, −1.94\]; the risk ratio is 0.479 \[0.343, 0.669\], z-test
p = 7.5×10⁻⁶, Fisher's exact p = 1.3×10⁻⁶ (panel (a) of #ref(<fig-double-gap>)).

#exhibit("fig_01_double_gap_capital_intensity", [The double gap by bloc, and the sector representation ladder that qualifies it.]) <fig-double-gap>
Both numerator and denominator are drawn from companies Crunchbase chose to index, so the
result does not depend on the coverage gap in §5.1. Counting every deal with no recorded
country as emerging‑market --- the most generous possible treatment --- gives
3.46% and a risk ratio of 0.637, p = 6.3×10⁻⁶.

China, reported separately throughout, sits with the advanced economies rather than with
emerging markets. #ref(<fig-rate-by-year>) shows the two rates by year, with every
emerging‑market cell annotated by its count.

#exhibit("fig_03_green_rate_by_year", [Green share of recorded deals by bloc and year, emerging‑market counts annotated.]) <fig-rate-by-year>
#strong[Verdict: Supported.] Falsified if the emerging‑market green rate were
indistinguishable from the advanced‑economy rate, or if the gap vanished under the upper
bound.

=== 5.3 The gap is a capital‑intensity gap
<the-gap-is-a-capitalintensity-gap>
Emerging-market venture capital in this period concentrated in capital-light consumer
internet and avoided capital-intensive sectors as a class. Regressing log
emerging‑market representation on log median advanced‑economy deal size across
23 sectors gives an elasticity of −1.19
\[−1.64, −0.75\], p = 1.5×10⁻⁵, R² = 0.60 (panel (b) of
#ref(<fig-double-gap>)). Doubling a sector's capital intensity roughly halves
its emerging‑market representation.

Cleantech sits #strong[above] the position that fit predicts, at
1.92× \[0.75×, 4.91×\] of its predicted
representation. The interval includes 1, so outperformance is not established; what is
established is that there is no green‑specific penalty once capital intensity is
accounted for. Biotech, by contrast, sits below its own prediction.

Green also took a larger share of venture dollars than of venture deals from 2005 onward
(#ref(<fig-dollar-share>)), which is consistent with green being capital-intensive
without testing the cross‑sector elasticity above.

#exhibit("fig_06_green_share_of_all", [Green as a share of all recorded deals and of all disclosed dollars.]) <fig-dollar-share>
=== 5.4 The taxonomy cannot say what kind of green
<the-taxonomy-cannot-say-what-kind-of-green>
88.2% of emerging‑market green deals carry no sub‑domain more
specific than "Clean Technology", against 67.9% in advanced
economies (#ref(<fig-subdomain>)). The mechanism is direct: 26 of the 28 emerging‑market green
companies carry no other taxonomy tag at all. The planned sub‑domain mix comparison was
cut, because the measurement failure shown here makes it impossible.

#exhibit("fig_04_subdomain_resolution", [Share of green deals resolved to a specific sub‑domain, by bloc.]) <fig-subdomain>

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

#exhibit("fig_05_cycle", [Green deals and disclosed green funding, in counts and constant 2015 USD.]) <fig-cycle>
=== 6.2 The crisis hit green and spared non-green, but the test does not identify it
<the-crisis-hit-green-and-spared-non-green-but-the-test-does-not-identify-it>
Across 2008--09, advanced‑economy green deals contracted
−26.5% while non-green #strong[grew]
13.5% (#ref(<fig-crisis>)).

#exhibit("fig_07_crisis_contraction", [Deal volume indexed to 2007, by bloc and green status.]) <fig-crisis>
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

#exhibit("fig_08_instrument_mix", [Non-dilutive share of deals by bloc and green status.]) <fig-instrument>
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

#exhibit("fig_11_depth_vs_need", [Green funding intensity against market depth, beside the need regressor’s distribution.]) <fig-depth>
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

#exhibit("fig_09_cell_sizes", [Observations available in each emerging‑market test cell, against the minimum.]) <fig-cells>
These are six independent routes to one conclusion. The open venture record cannot
support the capital-regime analysis the field needs.
