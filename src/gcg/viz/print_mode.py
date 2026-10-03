"""Print variants of the figure set.

The screen variants are standalone exhibits: 7.2in wide, with a baked-in
finding-sentence title, a subtitle, and a 4-5 line source footer. Embedding one
of those in a 6.22in text column scales every glyph down by ~14%, which puts the
7pt source block at roughly 6pt and, in the 23-row sector ladder, collides the
category labels. The Typst caption then repeats the subtitle, so the figure is
titled twice.

Print variants fix both problems at the source:

  1. No chrome in the image. Title, subtitle and source note are emitted as
     caption text (see `caption_for`) and set by the Typst template in the
     document's own type. The image carries axes, data, annotations only.
  2. Rendered at the exact final width. Nothing is scaled in the document, so
     8pt in matplotlib is 8pt on the page. `\\includegraphics`-style scaling is
     never applied; Typst gets `width: 100%` against an image already sized to
     the column.

Both variants are built by `make figures`. Screen variants keep their chrome and
remain what gets published to the web version and shared standalone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import matplotlib as mpl
from matplotlib.figure import Figure

# The text column, derived rather than written down. It was written down, as
# 6.22in from a 2.6cm margin, while report/template.typ actually sets 2.9cm.
# The 0.24in difference did not fail anything: Typst embeds each figure at
# `width: 100%`, so every print variant was silently scaled to 96% and the type
# size chosen here landed at 10.1pt instead of 10.5pt. Deriving it from the same
# numbers the template uses removes the chance of that drifting again, and
# render.py checks the template still agrees.
PAGE_WIDTH_CM = 21.0  # A4
SIDE_MARGIN_CM = 2.9  # must equal report/template.typ's page margin
CM_PER_IN = 2.54
COLUMN_IN = (PAGE_WIDTH_CM - 2 * SIDE_MARGIN_CM) / CM_PER_IN

Size = Literal["standard", "tall", "full_page", "wide"]

# Height by role. `full_page` sits alone on its page and uses the full text
# height (24.2cm = 9.53in) less room for the caption.
HEIGHTS: dict[Size, float] = {
    "standard": 3.50,
    "tall": 4.60,
    "full_page": 7.90,
    "wide": 3.10,
}


@dataclass(frozen=True)
class PrintSpec:
    """How one figure is rendered for print, and what its caption says."""

    slug: str
    size: Size
    finding: str  # the sentence that was the image's title
    unit_window: str  # what was the subtitle
    source_note: str  # what was the baked-in source footer, tightened


def apply_print_rc() -> None:
    """Type scale for figures rendered at final size.

    Deliberately larger than the screen variant: at the text-column width with
    no downscaling,
    these land at the same optical size as the document's 10.5pt body, which is
    what makes an embedded figure read as part of the page rather than a
    pasted-in screenshot.
    """
    mpl.rcParams.update(
        {
            "font.size": 9.0,
            "axes.labelsize": 9.0,
            "axes.titlesize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": None,  # never "tight" — it silently reflows the canvas
            "savefig.pad_inches": 0.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def size_for(spec: PrintSpec) -> tuple[float, float]:
    return (COLUMN_IN, HEIGHTS[spec.size])


def caption_for(spec: PrintSpec) -> str:
    """Typst caption source for this figure.

    Three tiers, matching what the image used to carry internally:
    the finding sentence in document text, then the unit/window line, then the
    source note. The template styles all three; this only assembles them.
    """
    return (
        f'#text(fill: rgb("#141413"), weight: "medium")[{spec.finding}] '
        f"{spec.unit_window} {spec.source_note}"
    )


def save(fig: Figure, spec: PrintSpec, outdir: Path) -> Path:
    """Write the print variant as vector PDF at exact final size."""
    fig.set_size_inches(*size_for(spec))
    path = outdir / f"{spec.slug}_print.pdf"
    fig.savefig(path, format="pdf", bbox_inches=None, pad_inches=0.0)
    return path


# --------------------------------------------------------------------------
# Per-figure specs.
#
# `size` is the judgement call. Rules of thumb that produced these:
#   - a single panel with <=8 categorical rows  -> standard
#   - a time series with annotation callouts     -> tall
#   - two stacked panels, or >15 categorical rows-> full_page
#   - two side-by-side panels                    -> wide
# --------------------------------------------------------------------------

SPECS: dict[str, PrintSpec] = {
    # --- SPLIT. Previously one two-panel Figure 2. The panels are discussed in
    # two different subsections (5.2 and 5.3), and the 23-row ladder cannot be
    # read at half a page. Splitting lets each sit beside its own prose at full
    # size, and removes the "panel (b) of Figure 2" indirection from the text.
    "fig_01a_double_gap": PrintSpec(
        slug="fig_01a_double_gap",
        size="standard",
        finding="In the record, an emerging-market company is half as likely to be green.",
        unit_window="Green share of recorded venture deals by bloc, 2000–2012.",
        source_note=(
            "Crunchbase 2013 Snapshot (CC BY 4.0); authors' calculations. "
            "n = {{data.deals_in_window}} deals, {{classifier.green_deals}} green; "
            "bloc rows sum to the total. Intervals are Wilson score. The bracket "
            "marks the headline comparison: {{h1.em_rate_pct}}% against "
            "{{h1.ae_rate_pct}}%, risk ratio {{h1.rr}} {{h1.rr_ci}}, p = {{h1.p}}. "
            "Counting every "
            "unattributable deal as emerging-market, the most generous reading "
            "available, still leaves a rate of {{h1.ub_em_rate_pct}}% against "
            "{{h1.ae_rate_pct}}% and a risk ratio of {{h1.ub_rr}}. China is not "
            "distinguishable from advanced economies (risk ratio "
            "{{china.rr}}, p = {{china.p}}) and is reported separately throughout. "
            "Headline is raw classifier output; bias-corrected risk ratio "
            "{{h1.bias_rr}} {{h1.bias_rr_ci}}, curated {{robust.curated_rr}}, "
            "Tier A only {{robust.strict_rr}} (Appendix C)."
        ),
    ),
    "fig_01b_sector_ladder": PrintSpec(
        slug="fig_01b_sector_ladder",
        size="full_page",
        finding="Capital intensity drives the pattern, and green beats its prediction.",
        unit_window=(
            "Emerging-market representation relative to advanced economies "
            "across {{h1b.n_sectors}} sectors, 2000–2012."
        ),
        source_note=(
            "Capital intensity is median advanced-economy deal size in constant "
            "2015 USD, so the proxy cannot be contaminated by the emerging-market "
            "composition it explains. Segments run from predicted to observed; "
            "intervals are residual 95% CI. Cleantech sits "
            "{{h1b.cleantech_residual}} above its predicted position "
            "{{h1b.cleantech_residual_ci}}: capital intensity over-predicts the gap, "
            "and because the interval includes 1 the outperformance is not confirmed. "
            "Biotech is further under-represented than cleantech and also sits below "
            "its own prediction."
        ),
    ),
    "fig_02_coverage_gdp": PrintSpec(
        slug="fig_02_coverage_gdp",
        size="standard",
        finding=(
            "Emerging markets hold a fifth of world GDP and a fiftieth of the venture record."
        ),
        unit_window=(
            "Emerging-market share of world GDP against its share of recorded venture deals, "
            "2000–2012."
        ),
        source_note=(
            "GDP shares are computed over the same country set the bloc panel "
            "covers, so the two series are comparable by construction. Across the "
            "window emerging markets hold {{measure.em_gdp_share_range}} of world GDP "
            "against {{measure.em_deal_share_range}} of recorded venture deals, an "
            "under-representation of {{measure.under_rep_range}}. This is the "
            "denominator check: it establishes that the conditional green-rate gap "
            "is not this coverage gap restated."
        ),
    ),
    "fig_03_rate_by_year": PrintSpec(
        slug="fig_03_rate_by_year",
        size="tall",
        finding="The two rates met in 2008, at the peak of Cleantech 1.0, then diverged.",
        unit_window="Green share of recorded deals by bloc and year, 2000–2012.",
        source_note=(
            "No emerging-market year-cell reaches the minimum cell size of "
            "{{power.min_cell}} green deals; the largest is "
            "{{h2.em_largest_cell}}, in 2008. In that year the two rates converge, "
            "and the gap opens only after the crash. No per-year test is reported and "
            "this figure is descriptive only; counts are printed beside each "
            "emerging-market point so the reader can see the precision available."
        ),
    ),
    "fig_04_subdomain": PrintSpec(
        slug="fig_04_subdomain",
        size="standard",
        finding="The taxonomy cannot say what kind of green an emerging-market company is.",
        unit_window=(
            "Share of green deals resolved to a specific sub-domain, by bloc, 2000–2012."
        ),
        source_note=(
            "{{measure.em_unspecified_companies}} of the "
            "{{measure.em_green_companies}} emerging-market green companies carry no "
            'tag more specific than "Clean Technology", against '
            "{{measure.ae_unspecified_pct}}% of advanced-economy green deals. The "
            "{{classifier.subdomains}} specific sub-domains are solar, wind/hydro/geothermal, "
            "biofuels, storage, efficiency and smart grid, electric mobility, water, "
            "waste and circular, sustainable agriculture, green building, and "
            "environmental monitoring. This figure replaces the planned sub-domain "
            "mix comparison, which the measurement failure shown here makes impossible."
        ),
    ),
    "fig_05_cycle": PrintSpec(
        slug="fig_05_cycle",
        size="full_page",
        finding="Green deal sizes fell far faster than non-green within the same stages.",
        unit_window=(
            "Green deals and disclosed green funding, all blocs, 2000–2012. Constant 2015 USD."
        ),
        source_note=(
            "n = {{classifier.green_deals}} green deals, "
            "{{classifier.green_with_amount}} with a disclosed amount. Counts and "
            "dollars are separate series because undisclosed-amount rates differ by "
            "instrument and bloc. Dollars peak a year before deals do. The cheque-size "
            "claim is the within-stage comparison: green {{cheque.green_pct}}% against "
            "non-green {{cheque.nongreen_pct}}%, difference "
            "{{cheque.difference_pp}}pp {{cheque.ci}}, bootstrapped over "
            "{{repro.bootstrap_draws}} draws on clean stage codes. The pooled median "
            "falls alike in both and is composition-confounded for each. Robust to the "
            "start year, sensitive to the end year (§6.1)."
        ),
    ),
    "fig_06_share_crossover": PrintSpec(
        slug="fig_06_share_crossover",
        size="tall",
        finding="From 2005, green took a bigger share of venture dollars than of deals.",
        unit_window=(
            "Green as a share of all recorded deals and of all disclosed dollars, 2000–2012. "
            "Constant 2015 USD."
        ),
        source_note=(
            "A dollar share above the count share means the average green cheque "
            "exceeded the average cheque overall, which is consistent with green being "
            "capital-intensive; it does not test the cross-sector elasticity. The two "
            "series cross in 2005: before then a green deal was smaller than the "
            "average deal, and from 2005 on it was larger. The ordering reverses "
            "before 2005 on thin cells ({{measure.thin_cells_pre2005}})."
        ),
    ),
    "fig_07_crisis": PrintSpec(
        slug="fig_07_crisis",
        size="tall",
        finding="The crisis hit green venture funding and left non-green growing.",
        unit_window="Deal volume indexed to 2007, by bloc and green status, 2000–2012.",
        source_note=(
            "Across 2008–09 advanced-economy green contracted "
            "{{h2.crisis_ae_green_pct}}% while advanced-economy non-green grew "
            "{{h2.crisis_ae_non_green_pct}}%. The emerging-market green series is not "
            "drawn: its 2007 base year holds {{h2.em_base_deals}} deal, so the index "
            "would reach {{h2.em_index_2008}} in 2008. No difference-in-differences "
            "coefficient is shown: green volume was already growing "
            "{{h2.pretrend_coef}} log-points per year faster than non-green before the "
            "event window (p = {{h2.pretrend_p}}), so parallel trends fail, these "
            "series are descriptive, and the design does not identify a causal effect."
        ),
    ),
    "fig_08_instruments": PrintSpec(
        slug="fig_08_instruments",
        size="standard",
        finding="Green ventures lean harder on grants and debt than non-green ones do.",
        unit_window="Non-dilutive share of deals by bloc and green status, 2000–2012.",
        source_note=(
            "Non-dilutive instruments are grants, debt financing and post-IPO debt. "
            "Within advanced economies, green uses one on "
            "{{h3.ae_green_nondilutive_pct}}% of deals against "
            "{{h3.ae_nongreen_nondilutive_pct}}% for non-green: risk ratio "
            "{{h3.rr}} {{h3.rr_ci}}, p = {{h3.p}}. The emerging-market arm rests on "
            "{{h3.em_green_deals}} deals, "
            "of which {{h3.em_nondilutive_n}} are non-dilutive, and is reported as a "
            "pre-registered null rather than as an estimate. "
            "Project finance that is debt or concessional in substance but coded as an "
            "equity round understates the non-dilutive share on both sides, and more so "
            "for emerging markets, where utility-scale generation accounts for "
            "{{audit.utility_scale}} of {{audit.em_census_n}} green companies; that bias "
            "direction was stated before these numbers were computed."
        ),
    ),
    "fig_09_power_wall": PrintSpec(
        slug="fig_09_power_wall",
        size="standard",
        finding="Every emerging-market test fails on the same wall, for different reasons.",
        unit_window=(
            "Observations available against the pre-registered minimum cell size, across "
            "H2–H5."
        ),
        source_note=(
            "The minimum cell size of {{power.min_cell}} was fixed in config before "
            "any hypothesis was tested, and no bar clears it. These are five distinct "
            "failures rather than one repeated. The emerging-market green sample of "
            "{{h3.em_green_deals}} does itself clear the threshold; the non-dilutive "
            "cell the instrument test depends on holds {{h3.em_nondilutive_n}}. "
            "Three figures that would have plotted these quantities as estimates were "
            "cut rather than drawn."
        ),
    ),
    "fig_10_depth_need": PrintSpec(
        slug="fig_10_depth_need",
        size="wide",
        finding="Capital tracks market depth; whether it tracks need cannot be measured here.",
        unit_window=(
            "Green funding intensity across {{h5.depth_n}} countries with at "
            "least three green deals, 2000–2012."
        ),
        source_note=(
            "Spearman rank correlation {{h5.depth_rho}} {{h5.depth_ci}}, with a "
            "bootstrap interval over {{repro.bootstrap_draws}} draws. The planned "
            "small-multiple of need indicators is not drawn; panel (b) shows why. A "
            "scatter against a regressor on which {{h5.depth_zero_countries}} of "
            "{{h5.depth_n}} countries record exactly zero would read as a relationship "
            "and is not one. Green funding is highly concentrated: Gini {{h5.gini}}, "
            "top five countries hold {{h5.top5_pct}}% of green dollars."
        ),
    ),
    "fig_11_continuity": PrintSpec(
        slug="fig_11_continuity",
        size="wide",
        finding="A later window in one large emerging market reproduces the same scarcity.",
        unit_window=(
            "Green deals per year. Two different instruments measuring two different "
            "populations; the panels share no axis."
        ),
        source_note=(
            "Left: Crunchbase 2013 Snapshot, emerging markets excluding China and LDCs, "
            "{{h3.em_green_deals}} green deals. Right: the Indian startup funding "
            "scrape, {{india.deals}} dated deals of which {{india.green}} are green "
            "under the same lexicon. Never pooled: taxonomies and "
            "amount conventions are not compatible, and no category_code exists in the "
            "Indian data so Tier A cannot fire. 2020 is a partial year and is excluded."
        ),
    ),
    # --- Methodology exhibits. Rendered the same way, numbered M1/M2 by the
    # template's separate counter, and placed in §4 rather than the results flow.
    "fig_m1_censoring": PrintSpec(
        slug="fig_m1_censoring",
        size="tall",
        finding="Only December 2013 is censored, which is why the window closes at 2012.",
        unit_window="Monthly deals as a share of their own year, 2011–2013.",
        source_note=(
            "Expressing each month as a share of its own year removes the level "
            "difference between years so the shapes are comparable. December 2013 holds "
            "{{censor.dec_2013_pct}}% of its year against a "
            "{{censor.dec_baseline_pct}}% baseline; the snapshot was taken mid-December, "
            "so only that month is truncated. November 2013 is above both earlier years "
            "({{censor.nov_counts}}), so coverage was not decaying. The "
            "disclosed-amount rate is flat across these years "
            "({{censor.disclosed_by_year}}%), so dollars are not differentially "
            "censored either. The window still closes at 2012-12-31, on the "
            "coverage-growth argument rather than this one (§4)."
        ),
    ),
    "fig_m2_elasticity": PrintSpec(
        slug="fig_m2_elasticity",
        size="tall",
        finding=(
            "Emerging-market representation falls roughly in proportion to capital intensity."
        ),
        unit_window=(
            "{{h1b.n_sectors}} sectors, 2000–2012. Ordinary least squares on logs; "
            "the line is the model's fitted values."
        ),
        source_note=(
            "Elasticity {{h1b.elasticity}} {{h1b.elasticity_ci}}, R² = {{h1b.r2}}, "
            "p = {{h1b.p}}. Cleantech sits {{h1b.cleantech_residual}} above the fit "
            "{{h1b.cleantech_residual_ci}}. The proxy uses advanced-economy deals only. "
            "The secondary proxy, median cumulative funding per company, gives an "
            "elasticity of {{h1b.elasticity2}} with R² {{h1b.r2_secondary}}."
        ),
    ),
}
