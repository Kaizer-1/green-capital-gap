# The Green Capital Gap

**A deal-level analysis of cleantech venture funding in emerging economies, 2000–2012**

---

## Abstract

Emerging-market green entrepreneurship is almost absent from the open venture record, and
what absence there is turns out not to be about green. Across {{data.deals_in_window}}
funding rounds from the Crunchbase 2013 Snapshot, classified by a three-tier green
classifier with inter-tier agreement of κ = {{classifier.kappa}}, an emerging-market
company already indexed in the record is **half as likely to be green as an
advanced-economy one**: {{h1.em_rate_pct}}% against {{h1.ae_rate_pct}}%, a risk ratio of
{{h1.rr}} {{h1.rr_ci}}. That gap survives every green definition, every bloc scheme, and a
permutation test in which **zero of {{robust.perm_draws}}** label shuffles reach the
observed value.

The gap is **not green-specific**. Across {{h1b.n_sectors}} sectors, emerging-market
representation falls roughly in proportion to capital intensity, with an elasticity of
{{h1b.elasticity}} {{h1b.elasticity_ci}} explaining {{h1b.r2}} of the cross-sector
variance; biotech sits further below proportionate representation than cleantech does.
Cleantech's residual from that fit is **positive** at {{h1b.cleantech_residual}}
{{h1b.cleantech_residual_ci}}, so a green-specific penalty is ruled out.

Three of the five hypotheses could not be resolved, each for a different and separately
verifiable reason, and together with three further measurement failures they give **six
independent routes to one conclusion: the capital-regime question is not answerable from
open data.** That is the paper's finding, not its limitation.

---

## 5. The double gap

### 5.1 Emerging markets are a fiftieth of the record and a fifth of world GDP

Over 2000–2012 emerging markets held {{measure.em_gdp_share_range}} of world GDP and
{{measure.em_deal_share_range}} of recorded venture deals, an under-representation of
{{measure.under_rep_range}} (Figure 2). This is the coverage gap, and it is the reason the
paper's headline result is measured *within* the dataset rather than against the world.

### 5.2 Conditional on being in the record, an emerging-market company is half as likely to be green

{{pop.em_deals}} emerging-market deals carry {{h1.em_rate_pct}}% green
{{h1.em_ci}}, against {{h1.ae_rate_pct}}% {{h1.ae_ci}} across {{pop.ae_deals}}
advanced-economy deals. The difference is {{h1.difference_pp}} percentage points
{{h1.difference_ci}}; the risk ratio is {{h1.rr}} {{h1.rr_ci}}, z-test
p = {{h1.p}}, Fisher's exact p = {{h1.fisher_p}} (Figure 1a, Table 1).

Both numerator and denominator are drawn from companies Crunchbase chose to index, so the
result does not depend on the coverage gap in §5.1. Counting every deal with no recorded
country as emerging-market — the most generous possible treatment — gives
{{h1.ub_em_rate_pct}}% and a risk ratio of {{h1.ub_rr}}, p = {{h1.ub_p}}.

China, reported separately throughout, sits with the advanced economies rather than with
emerging markets.

**Verdict: {{h1.verdict}}.** Falsified if the emerging-market green rate were
indistinguishable from the advanced-economy rate, or if the gap vanished under the upper
bound.

### 5.3 The gap is a capital-intensity gap

Emerging-market venture capital in this period concentrated in capital-light consumer
internet and avoided capital-intensive sectors as a class. Regressing log
emerging-market representation on log median advanced-economy deal size across
{{h1b.n_sectors}} sectors gives an elasticity of {{h1b.elasticity}}
{{h1b.elasticity_ci}}, p = {{h1b.p}}, R² = {{h1b.r2}} (Figure 1b, Figure M2).
Doubling a sector's capital intensity roughly halves its emerging-market representation.

Cleantech sits **above** the position that fit predicts, at
{{h1b.cleantech_residual}} {{h1b.cleantech_residual_ci}} of its predicted
representation. The interval includes 1, so outperformance is not established; what is
established is that there is no green-specific penalty once capital intensity is
accounted for. Biotech, by contrast, sits below its own prediction.

### 5.4 The taxonomy cannot say what kind of green

{{measure.em_unspecified_pct}}% of emerging-market green deals carry no sub-domain more
specific than "Clean Technology", against {{measure.ae_unspecified_pct}}% in advanced
economies (Figure 4). The mechanism is direct: 26 of the 28 emerging-market green
companies carry no other taxonomy tag at all. The planned sub-domain mix comparison was
cut, because the measurement failure shown here makes it impossible.

---

## 6. The advanced-economy benchmark, and what each null says about the record

Advanced economies are the one bloc where the record is dense enough to test the
structural hypotheses. They are the benchmark case for the capital-model mismatch Gaddy
et al. identify. Each subsection closes by stating what its emerging-market arm shows
about the record itself.

### 6.1 Green deal sizes fell far faster than non-green within the same stages

Between 2007 and 2012, within named funding stages, green deal sizes fell
{{cheque.green_pct}}% against {{cheque.nongreen_pct}}% for non-green — a difference of
{{cheque.difference_pp}} percentage points {{cheque.ci}}, bootstrapped over
{{repro.bootstrap_draws}} draws (Figure 5).

The pooled median falls by about the same amount in both groups and settles nothing: it
is composition-confounded for each, because the platform recorded far more small rounds
as it matured. All {{cheque.pairs_to_close}} start-end pairs running to the close of the
window are negative, spanning {{cheque.range_to_close}} percentage points, so the
direction is robust to the choice of start year.

This is a size pattern, not an investor motive. The rotation out of hardware that Gaddy
et al. document is cited here as external evidence, not as something this dataset shows.

### 6.2 The crisis hit green and spared non-green, but the test does not identify it

Across 2008–09, advanced-economy green deals contracted
{{h2.crisis_ae_green_pct}}% while non-green **grew** {{h2.crisis_ae_non_green_pct}}%
(Figure 7).

The difference-in-differences designed to test this does not identify it. Green deal
volume was already growing {{h2.pretrend_coef}} log-points per year faster than non-green
before the event window, {{h2.pretrend_ci}}, p = {{h2.pretrend_p}}. Parallel trends fail,
so the design never recovered a causal effect and there is no null to report.

**Verdict: {{h2.verdict}}.** The contraction figures above are descriptive.

*What the emerging-market arm shows about the record:* it does not exist. The largest
emerging-market green year-cell holds {{h2.em_largest_cell}} deals.

### 6.3 Green capital is less dilutive than non-green

Within advanced economies, {{h3.ae_green_nondilutive_pct}}% of green deals use
non-dilutive instruments — grants, debt, post-IPO debt — against
{{h3.ae_nongreen_nondilutive_pct}}% of non-green deals. The risk ratio is {{h3.rr}}
{{h3.rr_ci}}, p = {{h3.p}} (Figure 8, Table 3).

The χ² on the full instrument mix is also significant, but its Cramér's V of
{{h3.cramers_v}} falls below the conventional threshold for a small effect: with tens of
thousands of deals the test detects a negligible association, and the risk ratio on the
quantity the hypothesis is about is the interpretable figure.

**Verdict: {{h3.verdict}}.**

*What the emerging-market arm shows about the record:* it is null by construction. The
record codes infrastructure project equity as ordinary venture rounds, which understates
non-dilutive share on both sides and more so for emerging markets, where independent power
producers are seven of 28 green companies. The direction of that bias was stated before the
numbers were computed. On {{h3.em_green_deals}} deals the arm could not have settled the
question either way.

### 6.4 The scale-up step is unobservable

Conditional on raising seed capital, advanced-economy green companies reached Series A
with an odds ratio of {{h4.or}} {{h4.or_ci}} against non-green, p = {{h4.p}}. The
interval spans 1 and identifies no direction.

It cannot. The advanced-economy green seed cohort holds {{h4.ae_green_entrants}}
companies and the Series A to Series B pool — the specific missing-middle transition —
holds {{h4.ae_ab_pool}}. No model of that transition is reported, under any specification.

**Verdict: {{h4.verdict}}.**

*What the emerging-market arm shows about the record:* there are
{{h4.em_green_entrants}} emerging-market green seed entrants across thirteen years. The
scale-up step the missing-middle literature identifies as decisive cannot be observed at
all.

### 6.5 Capital tracks market depth; whether it tracks need cannot be determined

Across {{h5.countries_panel}} countries with enough green activity to measure, green
funding per capita correlates with GDP per capita at ρ = {{h5.depth_rho}}
{{h5.depth_ci}} (Figure 11). Green funding is extraordinarily concentrated: a Gini of
{{h5.gini}}, with the top five countries holding {{h5.top5_pct}}% of all green dollars
across {{h5.countries_any}} countries.

The need limb cannot be tested. Twenty of the {{h5.countries_panel}} panel countries
record an electricity-access deficit of exactly zero; the regressor is in substance a
dummy for one country. An income-controlled coefficient on it appeared positive and
significant, met the pre-registered falsification condition, and survived both
leave-one-out and collinearity checks before a degenerate-variance check rejected it.

**Verdict: {{h5.verdict}}.**

*What this shows about the record:* countries with real energy-access deficits have too
few green deals to enter the panel. The need indicators were not tested and found null;
they could not be tested.

### 6.6 Six routes, one conclusion

Three hypotheses were unresolved, each for a different stated reason: H2's identifying
assumption failed, H4 had {{h4.ae_ab_pool}} companies at the transition it exists to
measure, H5's need regressor had no variance. Three further failures are properties of
the record rather than of any hypothesis: {{measure.em_unspecified_pct}}% of
emerging-market green deals carry no specific sub-domain; a pre-declared venture-stage
criterion failed because project finance is coded as venture rounds; and H3's
emerging-market arm is biased by that same coding in a direction stated in advance.

Figure 9 puts the first four on one scale, against the minimum cell size fixed in config
before any hypothesis was tested. No cell clears it.

These are six independent routes to one conclusion. The open venture record cannot
support the capital-regime analysis the field needs.
