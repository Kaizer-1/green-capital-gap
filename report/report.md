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

## 1. Introduction

Green entrepreneurship is the private-sector channel of the climate transition. Public
money sets prices and de-risks; firms build the plant. Where those firms raise capital, on
what terms, and whether they survive the step from prototype to deployment determines how
fast the transition moves where it matters most.

The money is not where the need is. Climate Policy Initiative puts tracked global climate
finance at roughly US$1.9 trillion in 2023, with advanced economies and China accounting
for around 80% of flows since 2019; emerging markets excluding China captured roughly
14–17%, and least-developed countries 2–3% [@cpi2025]. The same source puts the emerging
markets grouping at over half the world's population and 23% of global GDP. Mitigation
finance needs to reach roughly US$7.8 trillion a year over 2025–2030. The mismatch between
need and flow is the motivating fact of this paper.

Evidence is missing at the level the mismatch is created: individual deals, with dates,
amounts and instruments. Aggregate flow accounting cannot say whether an emerging-market
green venture raises later, smaller, or on different instruments than its advanced-economy
counterpart, because it does not observe ventures, and deal-level data that could say so
is almost entirely paywalled. This paper asks what the open record can support, using the
Crunchbase 2013 Snapshot [@crunchbase2013] joined to World Bank and Our World in Data
enrichment layers.

It does not succeed in measuring that regime, and the central claim is that doing so with
open data is not possible — a result rather than a shortfall. Five pre-registered
hypotheses were specified before the data was examined. Two returned usable answers within
advanced economies; three could not be resolved, each for a different and independently
verifiable reason. Three further measurement failures arise from the record's own
structure. Six routes, one conclusion.

Two findings survive. Conditional on a company already being indexed, an emerging-market
company is half as likely to be classified green as an advanced-economy one. That gap is
real and robust, and it is **not** green-specific: it is a capital-intensity gap that
green sits inside, and sectors with no environmental character at all sit further below
proportionate representation than cleantech does.

## 2. Background and related work

The benchmark for what venture capital does to clean technology is the post-mortem on
Cleantech 1.0. Gaddy et al. find that venture firms committed over US$25 billion to
cleantech startups between 2006 and 2011 and recovered less than half of it, and that more
than 90% of cleantech A-rounds made after 2007 failed to return the capital invested
[@gaddy2017]. The losses concentrated in materials, chemistries and hardware firms that
never reached manufacturing scale; software was spared. Their conclusion is structural
rather than cyclical: clean energy needs more capital over longer horizons than a three-to
five-year fund life permits, so the venture model is mismatched to the asset.

That sets the prior here. If the venture model fitted cleantech badly in deep, liquid, 
dollar-denominated US markets, it should fit worse in thinner ones. Emerging-market green
ventures earn in local currency and raise in hard currency, and hedging is expensive or
unavailable, so investors demand a premium that compounds the capital-intensity problem.
The missing middle — too large for grants, too unproven for banks, too slow for venture —
bites hardest at first-of-a-kind commercial deployment, which is where these ventures
sit.

The emerging-economy literature adds institutional quality as the moderator. Where
regulatory enforcement is weak, the policy pull that creates green markets is absent and
green ventures compete on price against incumbents with unpriced externalities. Porter and
van der Linde's argument that well-designed regulation can make environmental performance
and competitiveness complementary [@porter1995] is conditional on enforcement; Khanna and
Palepu's institutional voids describe what happens when the intermediating institutions
that argument assumes are missing [@khanna1997]. The recurring empirical finding is that
green capital allocates toward depth of financial markets and ease of exit rather than
toward emissions, vulnerability or energy poverty.

Current trackers disagree about the present-day level. Net Zero Insights records US$23.5
billion of climate tech equity in H1 2025, one of the weakest half-years since 2020, with
non-dilutive capital rising as equity shrinks and graduation rates from seed to Series A
falling [@nzi2025]. Sightline Climate puts H1 2025 funding down roughly 19%
year-on-year, with Series B down 29% [@sightline2025]. Those estimates are not reconcilable
without knowing each provider's taxonomy and instrument coverage. The disagreement is
itself evidence for this paper's argument: the measurement of green entrepreneurship is
not settled, and a classifier's construction determines what it counts. That is why the
classifier in §4.1 is built in separable tiers and reported with its agreement statistic.

The gap this paper fills is not another estimate of the level, but a direct test of
whether the open record can answer the structural questions the literature poses, and a
demonstration of the specific points at which it cannot.

## 3. Data

The primary source is the Crunchbase 2013 Snapshot, distributed under CC BY 4.0
[@crunchbase2013]. Two Kaggle mirrors are used and joined. The relational dump carries
deal-level rows — date, amount, round type and round code — but only a coarse
single-value `category_code`. The flat export carries a pipe-delimited `category_list`
rich enough to support a green taxonomy, but no deal dates. Joining them on a normalised
permalink yields deal-level rows carrying rich green labels, which is what makes the
classifier in §4.1 possible. The join succeeds for {{data.join_rate_pct}}% of companies
and {{data.join_rate_deals_pct}}% of deals.

The two mirrors are **different vintages**, which the project documentation originally
assumed they were not. The relational dump's last funding date is
{{data.relational_vintage}}; the flat file extends to {{data.flat_vintage}} and is an
early-2015 export. {{data.census_gap_companies}} companies appear in the flat file with
funding the relational dump does not record, implying under-recording of about
{{data.under_recording_pct}}% of deals. The flat file is therefore used for its taxonomy
only and never as a funding source. The comparison is in Appendix H.

`funding_rounds.csv` holds {{data.rounds_total}} rounds in total. Applying the
2000-01-01 to 2012-12-31 window and the cleaning rules leaves {{data.deals_in_window}}
deals, a retention of {{data.retention_pct}}%; {{data.rows_dropped}} rows are dropped and
every drop reason is itemised in the attrition ledger (Appendix E), which is complete by
construction because each filter is applied through a ledger object that records its own
before and after counts. Two cleaning decisions are worth naming here.
{{data.undisclosed_zero_rows}} rows encode an undisclosed amount as a literal `0.0`; these
are nulled rather than treated as zero-dollar rounds, after a sweep confirmed no other
sentinel value was in use. {{data.fx_failures}} rows carry a currency that cannot be
converted and are excluded from dollar series but retained in deal counts.

Country attribution is the other substantial cleaning step, and it is measured at two
scales that should not be confused. At company scale, {{data.blank_country_companies}} of
the {{data.companies_total}} companies in the snapshot carry no country code; recovery from
the flat mirror's country field and from country-code top-level domains fixes
{{data.country_recovered_companies}} of them, a recovery rate of
{{data.country_recovery_rate_pct}}%. Most of those companies never raised a recorded round,
so the effect on the analysis is far smaller: at deal scale, {{data.country_recovered_deals}}
of the {{data.deals_in_window}} in-window deals gain a country this way, and
{{pop.unassigned_deals}} remain unattributable — {{data.unassigned_no_country}} with no code
at all and {{data.unassigned_unmappable}} carrying a code that maps to no country.
{{data.tld_refused}} vanity top-level domains — `.io`, `.co`, `.me`, `.tv` and similar — are
refused by name with a reason each, because they signal branding rather than domicile
(Appendix B). Unattributable deals are reported as their own bloc rather than dropped or
assigned, and §5.2 reports an upper bound in which all of them are counted as
emerging-market.

Enrichment comes from the World Bank and Our World in Data [@worldbank; @owid]:
historical income classifications for the time-varying bloc assignment, GDP, population,
electricity access, renewable share, and the US GDP deflator. The Indian startup funding
scrape [@indiafunding] supports the continuity probe in §7 and is never pooled.

One expected bias does not appear. If emerging-market companies were more thinly
described, the classifier would under-detect them for a clerical reason. They are not:
across {{tax.em_companies}} emerging-market companies the mean tag count is
{{tax.em_mean_tags}} against {{tax.ae_mean_tags}} for advanced economies (Mann–Whitney
p = {{tax.p}}) — the opposite direction to the one that would explain the result away. The
record's bias is in which companies it indexes, not in how well it describes them.

## 4. Methodology

### 4.1 The green classifier

Green status is assigned by a three-tier classifier whose every pattern lives in
`config/green_lexicon.yaml`, not in code. Tier A is the snapshot's own `category_code`
flag. Tier B is a case-insensitive lexicon of {{classifier.patterns}} regular expressions
over the concatenated taxonomy, tag and description fields, mapped to
{{classifier.subdomains}} sub-domains.
Tier C is an exclusion list that vetoes Tier B hits.

The headline definition is `green = TierA OR (TierB AND NOT TierC)`. Tier C never vetoes
Tier A: a company the snapshot itself flags as cleantech is not removed by a lexicon
exclusion. Agreement between the two independent tiers is κ = {{classifier.kappa}} on
funded companies carrying a taxonomy.

Two design choices prevent whole classes of false positive. Bare tokens are not
triggers — only compounds — because *green*, *carbon*, *waste*, *organic* and *clean* are
all common in unrelated senses, and admitting them to subtract the errors later is a
losing game. A fossil-fuel veto was added after inspection showed Crunchbase's `Energy`
bucket mixes renewables with oil, gas and coal; without it an upstream petroleum company
classified as green. {{classifier.vetoed}} companies are vetoed in total, each with a
recorded pattern and reason, in Appendix A.

### 4.2 Bloc assignment

Each deal takes the bloc its country held **in the year the deal closed**, derived from
the World Bank's historical income classification. A deal in Poland in 2004 is not a deal
in an advanced economy; a deal in Poland in 2013 is. China is reported separately
throughout, mirroring Climate Policy Initiative's practice, and least developed countries
are separated on the UN list with graduation years applied per year.

Country attribution required repair, and the allow-list governing it is the methodological
point. Several country-code domains belong to emerging or least developed countries and
are sold worldwide as vanity domains, so a naive mapping would have manufactured
{{data.tld_tv}} Tuvaluan and {{data.tld_st}} São Toméan *companies* out of domain
marketing — {{data.fabrication_avoided}} fabricated company attributions in all — in a
project whose finding is that such ventures are absent. {{data.tld_accepted}} domains are
accepted and {{data.tld_refused}} refused by name, each with a reason, in Appendix B.

### 4.3 Window, deflation and censoring

Amounts are converted to constant 2015 USD with the US GDP deflator, with the nominal
column retained alongside. Undisclosed amounts are encoded in the source as a literal zero
rather than null, which would have dragged every median toward zero while reporting
complete coverage; {{data.undisclosed_zero_rows}} rows are nulled, never imputed.

The window closes at {{data.window_end}}-12-31. The usual argument for truncating is
recording lag; here that is secondary. The primary argument is differential coverage
growth. Crunchbase's coverage expanded over the period and expanded faster for emerging
markets than for the United States, which saturated early, so the final year is the most
coverage-contaminated year for precisely the quantity the headline measures.
`#ref(<fig-censoring>)`{=typst} shows the boundary measured rather than assumed.

```{=typst}
#method-exhibit("fig_m1_censoring") <fig-censoring>
```

### 4.4 Statistical approach

Proportions carry Wilson score intervals rather than normal approximations, which
misbehave on small proportions. Deal-size comparisons use rank-based tests because the
distributions are heavy-tailed. Bootstrap intervals use
{{repro.bootstrap_draws}} resamples from a seeded generator. A minimum cell size of
{{power.min_cell}} was fixed in configuration before any hypothesis was tested, and no
significance test is reported on a cell below it.

Effect sizes accompany every p-value, because with tens of thousands of deals almost any
difference reaches significance: the instrument-mix χ² in §6.3 is significant at
p = {{h3.p}} on a Cramér's V of {{h3.cramers_v}}, which is why the risk ratio is quoted
instead. {{robust.tests_total}} tests carry Benjamini-Hochberg adjusted p-values in
Appendix D, of which {{robust.tests_significant}} survive correction.

The capital-intensity model in §5.3 regresses log emerging-market representation on log
median advanced-economy deal size across {{h1b.n_sectors}} sectors. The proxy is built
from advanced-economy deals only, so it cannot be contaminated by the emerging-market
composition it is used to explain. `#ref(<fig-elasticity>)`{=typst} shows the fit.

```{=typst}
#method-exhibit("fig_m2_elasticity") <fig-elasticity>
```

### 4.5 Specifications fixed in advance

Four judgement calls that move a headline number were fixed in configuration, with
reasoning recorded, before the relevant result was computed: whether a bare `Energy` tag
admits a company as green, whether angel rounds count as funnel entry, that H3's grant arm
is descriptive only below the minimum cell size, and that H4's extended window is
permitted because it conditions on sample entry. Each is run both ways in Appendix C.
Where a pre-commitment's assumption proved wrong — H4 assumed a direction when the binding
failure was power — it is recorded as void rather than quietly satisfied.

### 4.6 Reproducibility

This report was produced by {{meta.author_count}} authors — {{meta.authors}} — under the
guidance of {{meta.guide}} at the {{meta.institution}}. That list lives in
`report/metadata.yaml`, read from there by the title page, this statement and the README.

`make all` reproduces every number from a clean checkout. All {{repro.source_files}} source
files carry recorded SHA256 checksums, verified each run, so a changed upstream file fails
the build rather than silently changing a result. Every statistic here is injected from
`outputs/findings.json` and the renderer fails on an unresolved placeholder, so no number
in this report was typed by hand — including the numbers in the figure captions. Commit
{{repro.commit}}, Python {{repro.python}}, seed {{repro.seed}}.

---

## 5. The double gap

### 5.1 Emerging markets are a fiftieth of the record and a fifth of world GDP

Over 2000–2012 emerging markets held {{measure.em_gdp_share_range}} of world GDP and
{{measure.em_deal_share_range}} of recorded venture deals, an under-representation of
{{measure.under_rep_range}} (`#ref(<fig-coverage>)`{=typst}). This is the coverage gap, and it is
the reason the paper's headline result is measured *within* the dataset rather than
against the world.

```{=typst}
#exhibit("fig_02_coverage_gdp") <fig-coverage>
```


### 5.2 Conditional on being in the record, an emerging-market company is half as likely to be green

{{pop.em_deals}} emerging-market deals carry {{h1.em_rate_pct}}% green
{{h1.em_ci}}, against {{h1.ae_rate_pct}}% {{h1.ae_ci}} across {{pop.ae_deals}}
advanced-economy deals. The difference is {{h1.difference_pp}} percentage points
{{h1.difference_ci}}; the risk ratio is {{h1.rr}} {{h1.rr_ci}}, z-test
p = {{h1.p}}, Fisher's exact p = {{h1.fisher_p}} (`#ref(<fig-double-gap>)`{=typst}).

```{=typst}
#exhibit("fig_01a_double_gap") <fig-double-gap>
```


Both numerator and denominator are drawn from companies Crunchbase chose to index, so the
result does not depend on the coverage gap in §5.1. Counting every deal with no recorded
country as emerging-market — the most generous possible treatment — gives
{{h1.ub_em_rate_pct}}% and a risk ratio of {{h1.ub_rr}}, p = {{h1.ub_p}}.

China, reported separately throughout, sits with the advanced economies rather than with
emerging markets. `#ref(<fig-rate-by-year>)`{=typst} shows the two rates by year, with every
emerging-market cell annotated by its count.

```{=typst}
#exhibit("fig_03_rate_by_year") <fig-rate-by-year>
```


**Verdict: {{h1.verdict}}.** Falsified if the emerging-market green rate were
indistinguishable from the advanced-economy rate, or if the gap vanished under the upper
bound.

### 5.3 The gap is a capital-intensity gap

Emerging-market venture capital in this period concentrated in capital-light consumer
internet and avoided capital-intensive sectors as a class. Regressing log
emerging-market representation on log median advanced-economy deal size across
{{h1b.n_sectors}} sectors gives an elasticity of {{h1b.elasticity}}
{{h1b.elasticity_ci}}, p = {{h1b.p}}, R² = {{h1b.r2}} (`#ref(<fig-ladder>)`{=typst}). Doubling a sector's capital intensity roughly halves its
emerging-market representation.

Cleantech sits **above** the position that fit predicts, at
{{h1b.cleantech_residual}} {{h1b.cleantech_residual_ci}} of its predicted
representation. The interval includes 1, so outperformance is not established; what is
established is that there is no green-specific penalty once capital intensity is
accounted for. Biotech, by contrast, sits below its own prediction.

```{=typst}
#exhibit("fig_01b_sector_ladder") <fig-ladder>
```


Green also took a larger share of venture dollars than of venture deals from 2005 onward
(`#ref(<fig-dollar-share>)`{=typst}), which is consistent with green being capital-intensive
without testing the cross-sector elasticity above.

```{=typst}
#exhibit("fig_06_share_crossover") <fig-dollar-share>
```


### 5.4 The taxonomy cannot say what kind of green

{{measure.em_unspecified_pct}}% of emerging-market green deals carry no sub-domain more
specific than "Clean Technology", against {{measure.ae_unspecified_pct}}% in advanced
economies (`#ref(<fig-subdomain>)`{=typst}). The mechanism is direct:
{{measure.em_unspecified_companies}} of the {{measure.em_green_companies}} emerging-market
green companies carry no other taxonomy tag at all. The planned sub-domain mix comparison was
cut, because the measurement failure shown here makes it impossible.

```{=typst}
#exhibit("fig_04_subdomain") <fig-subdomain>
```


---

## 6. The advanced-economy benchmark, and what each null says about the record

Advanced economies are the one bloc dense enough to test the structural hypotheses, and
the benchmark case for the capital-model mismatch Gaddy et al. identify. Each subsection
closes by stating what its emerging-market arm shows about the record itself.

### 6.1 Green deal sizes fell far faster than non-green within the same stages

Between 2007 and 2012, within named funding stages, green deal sizes fell
{{cheque.green_pct}}% against {{cheque.nongreen_pct}}% for non-green — a difference of
{{cheque.difference_pp}} percentage points {{cheque.ci}}, bootstrapped over
{{repro.bootstrap_draws}} draws (`#ref(<fig-cycle>)`{=typst}).

The pooled median falls by about the same amount in both groups and settles nothing: it is
composition-confounded for each, because the platform recorded far more small rounds as it
matured. All {{cheque.pairs_to_close}} start-end pairs running to the close of the window
are negative, spanning {{cheque.range_to_close}} percentage points, and the headline is
their median, so the direction is robust to the start year. It is **not** robust to the
end year: across {{cheque.pairs_evaluated}} admissible pairs the difference is negative in
{{cheque.pairs_negative_pct}}%, and every positive pair stops in 2006 or 2009–11, before
the decline has run its course. The claim the grid supports is a direction holding to the
window close, with a magnitude depending on where the comparison starts.

This is a size pattern, not an investor motive. The rotation out of hardware Gaddy et al.
document is cited as external evidence, not as something this dataset shows.

```{=typst}
#exhibit("fig_05_cycle") <fig-cycle>
```


### 6.2 The crisis hit green and spared non-green, but the test does not identify it

Across 2008–09, advanced-economy green deals contracted
{{h2.crisis_ae_green_pct}}% while non-green **grew**
{{h2.crisis_ae_non_green_pct}}% (`#ref(<fig-crisis>)`{=typst}).

```{=typst}
#exhibit("fig_07_crisis") <fig-crisis>
```


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
{{h3.rr_ci}}, p = {{h3.p}} (`#ref(<fig-instrument>)`{=typst}).

```{=typst}
#exhibit("fig_08_instruments") <fig-instrument>
```


The χ² on the full instrument mix is also significant, but its Cramér's V of
{{h3.cramers_v}} falls below the conventional threshold for a small effect: with tens of
thousands of deals the test detects a negligible association, and the risk ratio on the
quantity the hypothesis is about is the interpretable figure.

**Verdict: {{h3.verdict}}.**

*What the emerging-market arm shows about the record:* it is null by construction. The
record codes infrastructure project equity as ordinary venture rounds, which understates
non-dilutive share on both sides and more so for emerging markets, where independent power
producers are {{audit.utility_scale}} of {{audit.em_census_n}} green companies. The direction of that bias was stated before the
numbers were computed. On {{h3.em_green_deals}} deals the arm could not have settled the
question either way.

### 6.4 The scale-up step is unobservable

Conditional on raising seed capital, advanced-economy green companies reached Series A
with an odds ratio of {{h4.or}} {{h4.or_ci}} against non-green, p = {{h4.p}}. The
interval spans 1 and identifies no direction.

The question is whether a wider window or a looser seed definition would resolve it. It
would not. The advanced-economy green seed cohort holds {{h4.ae_green_entrants}} companies
and the Series A to Series B pool — the specific missing-middle transition — holds
{{h4.ae_ab_pool}}. No model of that transition is reported, under any specification.

**Verdict: {{h4.verdict}}.**

*What the emerging-market arm shows about the record:* there are
{{h4.em_green_entrants}} emerging-market green seed entrants across thirteen years. The
scale-up step the missing-middle literature identifies as decisive cannot be observed at
all.

### 6.5 Capital tracks market depth; whether it tracks need cannot be determined

Across {{h5.countries_panel}} countries with enough green activity to measure, green
funding per capita correlates with GDP per capita at a Spearman ρ of {{h5.depth_rho}}
{{h5.depth_ci}} (`#ref(<fig-depth>)`{=typst}). Green funding is extraordinarily
concentrated: a Gini of {{h5.gini}}, with the top five countries holding
{{h5.top5_pct}}% of all green dollars across {{h5.countries_any}} countries.

```{=typst}
#exhibit("fig_10_depth_need") <fig-depth>
```

The need limb cannot be tested. {{h5.depth_zero_countries}} of the
{{h5.countries_panel}} panel countries record an electricity-access deficit of exactly
zero; the regressor is in substance a dummy for one country. A need regressor with no
variance cannot identify anything, and a scatter against it would present a relationship
that does not exist. An income-controlled coefficient on it appeared positive and
significant, met the pre-registered falsification condition, and survived both
leave-one-out and collinearity checks before a degenerate-variance check rejected it.

**Verdict: {{h5.verdict}}.** The depth limb holds; the need limb is untestable here. The
depth result would be falsified if the correlation reversed or its interval crossed zero;
the need limb would become testable only on a panel with real variation in the need
indicators.

*What this shows about the record:* {{h5.countries_any}} countries record any green deal
at all and only {{h5.countries_panel}} carry enough to enter the panel — and those are the
countries that already have capital markets. The countries where need is highest are
precisely the countries with too few green deals to enter the panel, which is not a
missing variable but the same selection this paper has been describing throughout.

### 6.6 Six routes, one conclusion

Three hypotheses were unresolved, each for a different stated reason: H2's identifying
assumption failed, H4 had {{h4.ae_ab_pool}} companies at the transition it exists to
measure, H5's need regressor had no variance. Three further failures are properties of
the record rather than of any hypothesis: {{measure.em_unspecified_pct}}% of
emerging-market green deals carry no specific sub-domain; a pre-declared venture-stage
criterion failed because project finance is coded as venture rounds; and H3's
emerging-market arm is biased by that same coding in a direction stated in advance.

`#ref(<fig-cells>)`{=typst} puts the first four on one scale, against the minimum cell size fixed
in config before any hypothesis was tested. No cell clears it.

```{=typst}
#exhibit("fig_09_power_wall") <fig-cells>
```


These are six independent routes to one conclusion. The open venture record cannot
support the capital-regime analysis the field needs.

## 7. What the open record cannot answer

The capital-regime question is not answerable from open data. That is this paper's
finding, and it is a specific claim rather than a call for more research. Five
pre-registered hypotheses about how emerging-market green ventures raise capital were
specified before the data was examined. Each failure has a named, separately verifiable
cause, and no two causes are the same: an identifying assumption that the data falsifies,
a transition cell holding {{h4.ae_ab_pool}} companies, a regressor with no variance, a
taxonomy that resolves {{measure.em_unspecified_pct}}% of emerging-market green deals no
further than "Clean Technology", and an instrument field that codes infrastructure project
equity as an ordinary venture round. None of these would be fixed by a longer window or a
looser classifier. They are properties of the data infrastructure.

The continuity probe asks whether the scarcity is an artefact of the window. It is not.
The Indian startup funding scrape covers 2015–2020 with {{india.deals}} dated deals, of
which {{india.green}} are green under the same lexicon — {{india.rate_pct}}%, against
{{h1.em_rate_pct}}% for emerging markets in the Crunchbase window
(`#ref(<fig-continuity>)`{=typst}). The two are never pooled: the taxonomies are not
compatible, the amount conventions differ, and no `category_code` exists in the Indian data
so Tier A cannot fire. A later window in one large emerging market reproduces the same
scarcity rather than escaping it.

```{=typst}
#exhibit("fig_11_continuity") <fig-continuity>
```

Secondary evidence suggests two signatures persisted. Non-dilutive instruments were
{{h3.all_nondilutive_pct}}% of in-window deals here; Net Zero Insights reports
non-dilutive capital rising as equity shrinks in 2025, and graduation rates from seed to
Series A falling [@nzi2025] — the same transition this paper could not observe at all.
Climate Policy Initiative's 14–17% share for emerging markets excluding China [@cpi2025]
is far above the {{measure.em_deal_share_range}} deal share seen here, which is consistent
with a large share of that capital moving through instruments a venture database does not
index. Tracxn puts Indian climate tech at roughly US$12.8 billion cumulative across 1,583
funded companies since 2008 [@tracxn2026], against the {{india.green}} green deals the open
scrape records for 2015–2020. This section is suggestive and is not a test.

## 8. Discussion

The first implication is for the data infrastructure of the field, because that is where
this paper bites. Green entrepreneurship in emerging economies is studied through
aggregate flow accounting because deal-level evidence is paywalled, and the open
alternative cannot carry the weight. A public deal-level register with a stable green
taxonomy and an honest instrument field would change what is answerable. The instrument
field is the cheapest fix and the most consequential: a flag distinguishing project
finance from ordinary venture equity would have made H3's emerging-market arm testable and
saved the venture-stage criterion this project had to abandon.

The second implication follows from the capital-intensity result. Emerging-market venture
capital in this period avoided capital-intensive sectors as a class, and cleantech's
position is explained by where it sits on that gradient rather than by anything about
being green. Policy aimed at closing a green-specific aversion would be aimed at something
the data does not show. What the data does show is a capital-structure problem: the
sectors that need the most money per firm over the longest horizon are the ones thin
markets serve worst. Concessional and blended capital bind at exactly that point, which is
the mechanism the missing-middle literature names and which this result is consistent
with.

For founders the implication is narrower and better evidenced within advanced economies,
where the sample supports it: green ventures lean harder on grants and debt than non-green
ones do, at {{h3.ae_green_nondilutive_pct}}% of deals against
{{h3.ae_nongreen_nondilutive_pct}}%, and green cheque sizes fell far faster than non-green
through the Cleantech 1.0 unwind even within the same stages. Neither result can be
extended to emerging markets from this data, and this paper does not extend them.

## 9. Limitations and threats to validity

**Coverage bias is the largest threat and is not fully mitigable.** Crunchbase 2013
under-covers non-US, non-English-language ecosystems, inflating the advanced-economy share
of everything. Three things limit the damage: the headline is a comparison *within* the
dataset, conditional on a company already being indexed, so it does not require the blocs
to be covered equally; the coverage gap is measured rather than disclaimed (§5.1); and the
taxonomy-richness check (§3) rules out the clerical version. What remains is selection
into the record itself. If the emerging-market companies that reach Crunchbase are
systematically less green than those that do not, the gap is overstated, and nothing in
this data can exclude that.

**The emerging-market green sample is {{h3.em_green_deals}} deals.** That forbids
essentially every disaggregation: by year, by sub-domain, by instrument, by country. The
minimum cell size of {{power.min_cell}} was fixed in config before any test was run, and
no emerging-market cell clears it. Every emerging-market quantity in this paper is
reported with its cell size printed, and no significance test is reported below that
minimum.

**The two-vintage join** bounds how much of the record is missing rather than resolving
it: roughly {{data.under_recording_pct}}% of deals appear to be under-recorded in the
relational dump. **Right-censoring** is handled by truncating at 2012-12-31, argued from
coverage growth rather than from the December artefact alone (§4.3, Figure M1).
**Undisclosed amounts** mean deal counts and deal dollars are reported as separate series
throughout; dollar series cover {{classifier.green_with_amount}} of
{{classifier.green_deals}} green deals. **Taxonomy anachronism** is a real risk: a 2013
snapshot's categories reflect 2013 ideas about what is green, and sub-domains that matter
now may be invisible.

**The audit is underdetermined, not reassuring.** Emerging-market and advanced-economy
false-positive rates are {{audit.em_fp_pct}}% and {{audit.ae_fp_pct}}% with p =
{{audit.p}}. That is an absence of power, not a demonstration of equality, and the
headline is therefore reported on raw classifier output, which is the symmetric choice.
**H5 has no causal identification**; the depth correlation is descriptive. **Multiple
comparisons** are handled by Benjamini–Hochberg across the full family of
{{robust.tests_total}} tests [@benjamini1995], of which {{robust.tests_significant}} remain
significant after adjustment; the full table is Appendix D.

## 10. Conclusion

Three findings. First, emerging markets hold {{measure.em_gdp_share_range}} of world GDP
and {{measure.em_deal_share_range}} of the open venture record, and conditional on being
in that record an emerging-market company is half as likely to be green as an
advanced-economy one — {{h1.em_rate_pct}}% against {{h1.ae_rate_pct}}%, a risk ratio of
{{h1.rr}} {{h1.rr_ci}}, stable across every green definition and bloc scheme tested.
Second, that gap is not green-specific: emerging-market representation falls roughly in
proportion to a sector's capital intensity, with an elasticity of {{h1b.elasticity}}
{{h1b.elasticity_ci}}, and cleantech sits above rather than below what that fit predicts.
Third, the structural questions the field asks about emerging-market green capital cannot
be answered from open data, and the six routes by which they fail are independent of one
another.

The implication is that the binding constraint on this field is measurement rather than
analysis. The concrete next step is narrow and actionable: an instrument field that
distinguishes project finance from venture equity. That single change would make the
instrument-mix question testable, restore the venture-stage criterion this project had to
abandon, and cost nothing to collect at the point the record is created.

## Appendix A. Green lexicon vetoes

Tier C exclusion patterns, with the number of companies each removed and the reason it
exists. Patterns are regular expressions over the concatenated taxonomy, tag and
description fields. The full lexicon, including the {{classifier.patterns}} Tier B
patterns and the ratified manual-exclusion decisions, is `config/green_lexicon.yaml`.

```{=typst}
#csvtable(
  "appendix_veto_counts.csv",
  cols: ("veto_pattern", "companies", "funded_companies", "reason"),
  head: ("Pattern", "Companies", "Funded", "Reason"),
  align-right: ("Companies", "Funded"),
)
```

## Appendix B. Country recovery

Recovery used the flat mirror's country field first and the company homepage's
country-code top-level domain second, under an explicit allow-list of
{{data.tld_accepted}} domains. {{data.tld_refused}} domains are refused because they are
sold as vanity domains worldwide; accepting them would have manufactured
{{data.fabrication_avoided}} company attributions, concentrated in exactly the countries
this paper reports as absent. The accepted and refused lists with per-domain reasons are
`config/blocs.yaml`.

The counts below are stated at the scale each is measured on. Company scale covers every
company in the snapshot, including the large majority that never raised a recorded round;
deal scale covers the {{data.deals_in_window}} in-window deals this paper analyses.

| Quantity | Scale | Count |
|---|---|---:|
| Companies in the snapshot | company | {{data.companies_total}} |
| Carrying no country code | company | {{data.blank_country_companies}} |
| Country recovered | company | {{data.country_recovered_companies}} ({{data.country_recovery_rate_pct}}%) |
| In-window deals | deal | {{data.deals_in_window}} |
| Country recovered | deal | {{data.country_recovered_deals}} |
| Still unattributable | deal | {{pop.unassigned_deals}} |
| — of which no country code | deal | {{data.unassigned_no_country}} |
| — of which an unmappable code | deal | {{data.unassigned_unmappable}} |

## Appendix C. Robustness

The headline risk ratio under four green definitions.

```{=typst}
#csvtable(
  "appendix_c_green_definitions.csv",
  cols: ("specification", "em_green", "em_rate_pct", "ae_green", "ae_rate_pct",
         "risk_ratio", "rr_lo", "rr_hi", "p_value"),
  head: ("Specification", "EM green", "EM %", "AE green", "AE %", "RR", "CI low",
         "CI high", "p"),
  align-right: ("EM green", "EM %", "AE green", "AE %", "RR", "CI low", "CI high", "p"),
  thousands: ("AE green",),
  digits: ("EM %": 2, "AE %": 2, "RR": 3, "CI low": 3, "CI high": 3),
  pvals: ("p",),
)
```

The same result under alternative bloc schemes, including a static present-day
classification.

```{=typst}
#csvtable(
  "appendix_c_bloc_schemes.csv",
  cols: ("scheme", "em_deals", "em_rate_pct", "ae_deals", "ae_rate_pct", "risk_ratio",
         "rr_lo", "rr_hi", "p_value"),
  head: ("Scheme", "EM deals", "EM %", "AE deals", "AE %", "RR", "CI low", "CI high", "p"),
  align-right: ("EM deals", "EM %", "AE deals", "AE %", "RR", "CI low", "CI high", "p"),
  thousands: ("EM deals", "AE deals"),
  digits: ("EM %": 2, "AE %": 2, "RR": 3, "CI low": 3, "CI high": 3),
  pvals: ("p",),
)
```

The three curation specifications. Raw applies no curation; curated applies the ratified
manual exclusions, which came from an asymmetric audit; bias-corrected applies each bloc's
own measured false-positive rate to its whole green population, so neither bloc is
penalised for having been audited harder.

```{=typst}
#csvtable(
  "appendix_c_three_specifications.csv",
  cols: ("spec", "em_rate_pct", "ae_rate_pct", "risk_ratio", "rr_ci"),
  head: ("Specification", "EM %", "AE %", "RR", "95% CI"),
  align-right: ("EM %", "AE %", "RR"),
  digits: ("EM %": 2, "AE %": 2, "RR": 3),
)
```

Endpoint sensitivity for the within-stage cheque-size result of §6.1. Every admissible
start-end pair, so the reader can see which choices reverse the sign rather than taking
the headline pair on trust.

```{=typst}
#csvtable(
  "appendix_c_cheque_endpoints.csv",
  cols: ("start", "end", "span", "green_pct", "non_green_pct", "difference_pp"),
  head: ("Start", "End", "Span", "Green %", "Non-green %", "Difference pp"),
  align-right: ("Start", "End", "Span", "Green %", "Non-green %", "Difference pp"),
  digits: ("Green %": 1, "Non-green %": 1, "Difference pp": 1),
)
```

## Appendix D. Test family and multiplicity correction

Every test run in this project, with raw and Benjamini-Hochberg adjusted p-values and an
effect size. {{robust.tests_significant}} of {{robust.tests_total}} survive correction.
Tests that could not be run because a cell fell below the minimum size are not listed here;
they are reported as unresolved in §6.

```{=typst}
#csvtable(
  "appendix_d_test_family.csv",
  cols: ("hypothesis", "test", "p_raw", "effect", "p_adjusted", "significant_after_bh"),
  head: ("H", "Test", "p raw", "Effect", "p adjusted", "Survives BH"),
  align-right: ("p raw", "p adjusted"),
  pvals: ("p raw", "p adjusted"),
  size: 7.0pt,
)
```

## Appendix E. Attrition ledger

Every filter applied between ingestion and the canonical deal table, with its own before
and after counts. The ledger is complete by construction: each filter is applied through a
ledger object that records its own effect, so a step cannot be omitted from this table
without being omitted from the pipeline.

```{=typst}
#csvtable(
  "appendix_e_attrition_ledger.csv",
  cols: ("step", "stage", "action", "reason", "rows_in", "rows_out", "rows_dropped"),
  head: ("#", "Stage", "Action", "Reason", "In", "Out", "Dropped"),
  align-right: ("#", "In", "Out", "Dropped"),
  thousands: ("In", "Out", "Dropped"),
  size: 7.0pt,
)
```

## Appendix F. Leave-one-out sensitivity

Each of the {{h1.loo_companies}} emerging-market green companies removed in turn, with the
effect on the emerging-market green rate and on green dollars. The dollar series moves by
{{h1.loo_usd_swing}} across the set, which is why dollar-denominated emerging-market
claims are not made in this report.

```{=typst}
#csvtable(
  "appendix_h1_em_leave_one_out.csv",
  cols: ("excluded_name", "excluded_country", "excluded_deals", "green_rate_pct",
         "green_rate_change_pp", "green_usd_change_pct"),
  head: ("Company removed", "Country", "Deals", "Green rate %", "Δ pp", "Δ USD %"),
  align-right: ("Deals", "Green rate %", "Δ pp", "Δ USD %"),
  digits: ("Green rate %": 3, "Δ pp": 3, "Δ USD %": 1),
  size: 7.0pt,
)
```

## Appendix G. Instrument field disagreements

The project normalises instruments from `funding_round_code`, not from
`funding_round_type`. The table below is why: every row is a case where the two fields
disagree, with the number of deals affected. It is the non-zero part of the full
type-by-code contingency table, which is `outputs/tables/appendix_instrument_type_x_code.csv`;
the zero cells are omitted because they carry nothing.

The two fields disagree on {{instrument.conflict_deals}} deals,
{{instrument.conflict_pct}}% of the source. Two rows carry the argument.
`funding_round_type` files {{instrument.seed_as_angel}} seed rounds under `angel`, so
reading instruments from that field would have collapsed seed into angel and made the
graduation funnel in §6.4 unmeasurable. It files {{instrument.debt_as_other}} debt and
{{instrument.grant_as_other}} grant rounds under `other`, so the non-dilutive share that H3
turns on would have been invisible. Neither collapse raises an error; both would have
silently changed a result.

```{=typst}
#csvtable(
  "appendix_instrument_conflicts.csv",
  cols: ("code_canonical", "type_canonical", "deals"),
  head: ("Code (used)", "Type (discarded)", "Deals"),
  align-right: ("Deals",),
  thousands: ("Deals",),
)
```

## Appendix H. Mirror vintage comparison

The two Crunchbase mirrors are different vintages. This table bounds what that costs: the
flat file records funding for companies the relational dump does not, implying
under-recording of roughly {{data.under_recording_pct}}% of deals.

```{=typst}
#csvtable(
  "appendix_mirror_vintage.csv",
  cols: ("metric", "value"),
  head: ("Metric", "Value"),
)
```

## References

::: {#refs}
:::
