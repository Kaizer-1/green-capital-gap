# Limitations and threats to validity

Written to be read by someone looking for the weakness this project missed. The ordering
is by how much damage each threat does, not by how comfortable it is to discuss.

The report's §9 carries a compressed version of this. This file is the long form, and
includes the threats that did not make the word budget.

---

## 1. Coverage bias — the largest threat, and not fully mitigable

Crunchbase 2013 systematically under-covers non-US, non-English-language ecosystems. It
is a US-centric, self-submission-driven database from a period when its international
coverage was thinnest. Every absolute emerging-market quantity in this project is
therefore an underestimate of the real world by an unknown factor.

**What limits the damage:**

- The headline result is a **ratio computed within the dataset**, conditional on a company
  already being indexed. It asks whether an indexed emerging-market company is less likely
  to be green than an indexed advanced-economy one. That question does not require the
  blocs to be covered equally.
- The coverage gap is **measured rather than disclaimed**: the report's §5.1 computes
  emerging-market share of recorded deals against emerging-market share of world GDP, over
  the same country set, year by year.
- The clerical version of the bias is **ruled out empirically**. If emerging-market
  companies were more thinly described, the classifier would under-detect them for reasons
  having nothing to do with green. They are not: emerging-market companies carry *more*
  taxonomy tags on average than advanced-economy ones, significant on a Mann–Whitney test.
  This is a negative result and it is reported as one.

**What remains, and cannot be excluded:** selection into the record itself. If the
emerging-market companies that make it into Crunchbase are systematically *less green*
than the ones that do not — for instance because the database's submission channels
reached consumer-internet founders before they reached infrastructure developers — then
the conditional gap is overstated. Nothing in this data can test that. It is the single
most important caveat on the headline, and no robustness check in the appendix addresses
it, because none can.

---

## 2. The emerging-market green sample is 34 deals

Thirteen years, 34 deals, 27 companies. This forbids essentially every disaggregation the
original research design assumed: by year, by sub-domain, by instrument, by country, by
stage.

A minimum cell size of 30 was fixed in `config/pipeline.yaml` **before any hypothesis was
tested**, and no emerging-market cell clears it. The consequences are reported as results
rather than hidden:

- No per-year emerging-market test is run; the largest year-cell holds 12 green deals.
- The instrument-mix comparison's emerging-market arm rests on 3 non-dilutive deals and is
  reported as a pre-registered null, not an estimate.
- The graduation model has **zero** emerging-market green seed entrants across the window.
- Every emerging-market figure prints its cell size on the chart.

The temptation this creates is to widen the green definition until the sample becomes
workable. That was tested and explicitly refused: Tier A alone gives 29 deals, the
headline 34, and Tier B with every veto removed also 34. The constraint is the record, not
the classifier, and widening the definition would have bought significance without buying
evidence.

---

## 3. Dollar-denominated emerging-market claims are not made

The leave-one-out appendix is the reason. Removing any single emerging-market green
company moves the emerging-market green dollar total by up to a fifth. A quantity that
one company can move that far is not a population quantity, and no dollar-denominated
emerging-market claim appears anywhere in the report. Deal counts are more stable and are
what the argument rests on.

---

## 4. The two-vintage join

The relational and flat Crunchbase mirrors are different vintages (2013-12-12 against
2015-01-01). The flat file records funding for companies the relational dump does not,
implying under-recording of a few per cent of deals.

This is **bounded, not resolved**. The bound is computed in
`outputs/tables/appendix_mirror_vintage.csv`. The flat file is used for taxonomy only, and
the analysis window closes well before either vintage boundary, so the effect on the
headline is small — but "small" here is an estimate from the same data, not an independent
check.

---

## 5. Right-censoring

The snapshot's final months are incomplete: deals are recorded with a lag, so the tail
looks like a crash that is a reporting artefact. The window is truncated at **2012-12-31**.

The usual argument for truncating is the lag, and in this project that argument is
**secondary**. The primary one is differential coverage growth: Crunchbase's coverage
expanded over the period and expanded faster for emerging markets than for the United
States, which saturated early. The final year is therefore the most
coverage-contaminated year for exactly the quantity the headline measures. Figure M1
establishes the censoring boundary by measurement rather than assumption, and shows that
the disclosed-amount rate is flat across the boundary so dollars are not differentially
censored either.

---

## 6. Undisclosed amounts

A large minority of rows carry no amount. Nothing is imputed. Deal counts and deal dollars
are reported as two independent series throughout, and every dollar figure states the
covered subsample.

The undisclosed rate differs systematically by instrument and by bloc, which means the
disclosed subsample is not a random sample of deals. Any dollar comparison across blocs
inherits that bias. This is why the cheque-size result in §6.1 is restricted to advanced
economies and to named stages.

---

## 7. Taxonomy anachronism

A 2013 snapshot's categories reflect 2013 ideas about what counts as green. Sub-domains
that matter now — grid-scale storage chemistry, hydrogen electrolysis, direct air capture,
alternative proteins — are either absent or buried in a generic `cleantech` bucket. The
classifier cannot find a category the source never had.

This cuts in a specific direction: it understates green in later years of the window more
than earlier years, and understates it for technologies that were pre-commercial in 2013.

---

## 8. The taxonomy cannot resolve sub-domains in emerging markets

88.2% of emerging-market green deals carry no sub-domain more specific than "Clean
Technology", against 67.9% in advanced economies; at company level, 23 of the 27
emerging-market green companies carry no more specific tag at all.

This is reported as a finding rather than a limitation, because it is one — the record
cannot say what *kind* of green an emerging-market company is. But it is also a limitation,
and it killed the planned sub-domain mix comparison outright.

---

## 9. The audit is underdetermined, not reassuring

The emerging-market green set was audited exhaustively, company by company. The
advanced-economy set was audited on a random sample of 60 drawn with the project seed. The
asymmetry biases toward finding a gap, because false positives were removed more
thoroughly from one bloc than the other.

The measured false-positive rates are 22.2% and 15.0%, p = 0.409. **That is an absence of
power, not a demonstration of equality.** At 27 and 60 companies the comparison cannot
detect a seven-point difference, and the risk-ratio interval admits a wide range in both
directions.

The response is to report the headline on **raw classifier output**, which applies no
curation to either bloc and is therefore symmetric by construction. The curated and
bias-corrected specifications are in Appendix C; curation *widens* the gap, so the raw
headline is the conservative choice. This was stated before the numbers were computed.

---

## 10. No causal identification

**H2** fails its identifying assumption outright: green deal volume was already growing
faster than non-green before the 2008 event window, so parallel trends do not hold and no
difference-in-differences coefficient is reported. The series are shown as descriptive.

**H5** is a rank correlation between green funding intensity and market depth. It is not
identified, no causal claim is made, and the need limb could not be tested at all because
20 of the 22 panel countries record an electricity deficit of exactly zero.

The capital-intensity regression in §5.3 is cross-sectional across sectors. It establishes
that emerging-market representation falls with capital intensity and that cleantech does
not sit below that line. It does not establish why thin markets avoid capital-intensive
sectors, and the report does not claim it does.

---

## 11. Taxonomy and classifier sensitivity

The headline risk ratio is reported under four green definitions and three bloc schemes,
all in Appendix C. It is stable across all of them. A permutation test over shuffled green
labels places the observed ratio outside the null distribution.

What that does *not* establish is that the lexicon is correct in some absolute sense. It
establishes that the result does not depend on the particular lexicon chosen. A
systematically different conception of "green" — one that excluded biofuels, say, or
admitted nuclear — would be a different study. The nuclear and fossil-fuel vetoes are
judgement calls, recorded with reasons in `config/green_lexicon.yaml` and run both ways.

---

## 12. The pre-commitment that turned out to be wrong

H4's pre-registered falsification condition assumed the binding constraint would be a
direction in the data. It was power: the advanced-economy Series A to Series B pool holds
13 companies. The pre-commitment is recorded as **void on its own assumption** rather than
quietly treated as satisfied, and the verdict is "Underpowered — cannot determine" rather
than a null.

Two further corrections went the other way, and both are recorded in the report's
reproducibility statement: an H5 falsifier was accepted on a degenerate regressor before a
variance check caught it, and a cheque-size finding was retracted prematurely on a power
argument before the machinery to test it properly was run. The error pattern is
non-directional — two overclaimed refutation, one overclaimed support — which is the
honest way to describe it.

---

## 13. What this project does not attempt

It does not measure the emerging-market green capital regime. It demonstrates that the
regime cannot be measured in open data, which is a different and smaller claim. It does
not establish that emerging-market green ventures raise through concessional or
development-finance instruments; that mechanism is argued from external evidence and is
explicitly not identified here. The competing explanation — that emerging-market
ecosystems in 2000–2012 were genuinely less green — cannot be excluded with this dataset,
and the report says so.
