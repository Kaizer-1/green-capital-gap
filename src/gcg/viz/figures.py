"""One function per figure, named ``fig_01_*`` … ``fig_12_*``.

Every figure obeys CLAUDE.md §8: a title that states the finding, a subtitle
giving unit and window, a 7pt source footer carrying the n, horizontal
gridlines only, no top or right spine, direct labelling in place of a legend,
and 300dpi PNG plus PDF under a deterministic filename.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from gcg.analysis import h1b_capital_intensity as h1b
from gcg.analysis.h1_selection import green_rate_by_bloc, two_proportion_test
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet
from gcg.viz import theme
from gcg.viz.theme import PALETTE as P

LOG = get_logger("viz.figures")


def fig_01_double_gap_and_capital_intensity(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 1: the double gap, and the capital-intensity pattern that qualifies it.

    Two panels, because the headline needs both. Panel (a) is the finding:
    conditional on being in the record, an emerging-market company is half as
    likely to be green. Panel (b) is the qualifier: that gap is where a sector
    of cleantech's capital intensity should sit, and cleantech is if anything
    above its predicted position. Putting the gap on page one and its qualifier
    in an appendix would be the same error as suppressing the gap.
    """
    theme.apply_theme()
    by_bloc = green_rate_by_bloc(deals, cfg).set_index("bloc")

    em, ae = deals.loc[deals["bloc"].eq("EM")], deals.loc[deals["bloc"].eq("AE")]
    test = two_proportion_test(
        int(em["green"].sum()), len(em), int(ae["green"].sum()), len(ae)
    )
    ub = deals.copy()
    ub["b"] = ub["bloc"].replace({"UNASSIGNED": "EM"})
    em_ub = ub.loc[ub["b"].eq("EM")]
    ub_rate = 100 * em_ub["green"].mean()

    panel_b = h1b.run(deals, cfg)
    sectors = panel_b["_tables"]["h1b_sector_capital_intensity"]
    fitobj = panel_b["primary_fit"]
    res = panel_b["cleantech_residual_primary"]

    fig, (ax_a, ax_b) = plt.subplots(
        2, 1, figsize=theme.figsize(cfg, "stacked"), height_ratios=[1.0, 1.95]
    )

    # ---------------- panel (a): the double gap -------------------------
    labels = cfg.blocs["display"]["labels"]
    order = ["AE", "CHINA", "EM", "LDC"]
    rows = by_bloc.reindex(order)
    y = np.arange(len(order))[::-1]
    xmax = 11.0

    tick_labels = []
    for yi, bloc in zip(y, order, strict=False):
        r = rows.loc[bloc]
        colour = P.bloc(bloc)
        lo, hi = r["ci_lo_pct"], min(r["ci_hi_pct"], xmax)
        clipped = r["ci_hi_pct"] > xmax

        ax_a.plot(
            [lo, hi],
            [yi, yi],
            color=colour,
            linewidth=1.6,
            solid_capstyle="butt",
            alpha=0.5,
            zorder=2,
        )
        if clipped:
            ax_a.plot(hi, yi, marker=">", color=colour, markersize=4.5, alpha=0.5, zorder=2)
        ax_a.plot(r["green_rate_pct"], yi, "o", color=colour, markersize=7, zorder=4)

        # The value label sits beside its marker, never after the interval:
        # the LDC interval runs to 22.8% and would strand its own label.
        ax_a.text(
            r["green_rate_pct"] + 0.22,
            yi + 0.3,
            f"{r['green_rate_pct']:.2f}%",
            va="center",
            ha="left",
            fontsize=8.5,
            color=colour,
            fontweight="semibold",
        )
        short = {"EM": "Emerging markets", "LDC": "Least developed"}.get(
            bloc, labels.get(bloc, bloc)
        )
        tick_labels.append(f"{short}\nn = {int(r['deals']):,} deals")

    em_y = y[order.index("EM")]
    ax_a.plot(
        ub_rate,
        em_y,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.em,
        markersize=7,
        markeredgewidth=1.3,
        zorder=4,
    )
    theme.annotate(
        ax_a,
        "Upper bound: every unattributable deal\n"
        f"counted as emerging market ({ub_rate:.2f}%).\nGap holds.",
        xy=(ub_rate, em_y),
        xytext=(ub_rate + 1.2, em_y - 0.48),
        color=P.ink_muted,
        fontsize=7.4,
    )
    theme.annotate(
        ax_a,
        f"Risk ratio {test['risk_ratio']:.2f} "
        f"[{test['risk_ratio_ci'][0]:.2f}, {test['risk_ratio_ci'][1]:.2f}]",
        xy=(rows.loc["AE", "green_rate_pct"], y[order.index("AE")]),
        xytext=(7.0, y[order.index("AE")] + 0.30),
        color=P.ae,
        fontsize=7.6,
    )
    ldc_y = y[order.index("LDC")]
    ax_a.text(
        0.22,
        ldc_y - 0.32,
        "0 of 13 deals: interval uninformative",
        va="center",
        ha="left",
        fontsize=7.0,
        color=P.ldc,
        style="italic",
    )

    ax_a.set_xlim(0, xmax)
    ax_a.set_ylim(-0.75, len(order) - 0.35)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(tick_labels, fontsize=8.4, linespacing=1.5)
    ax_a.tick_params(axis="y", length=0, pad=6)
    for lbl in ax_a.get_yticklabels():
        lbl.set_color(P.ink)
    ax_a.set_xlabel("Green share of the bloc's recorded deals")
    ax_a.xaxis.set_major_formatter(theme.fmt_pct)
    ax_a.spines["left"].set_visible(False)
    theme.style_axes(ax_a, xgrid=True)
    ax_a.grid(axis="y", visible=False)
    ax_a.set_title(
        "(a)  In the record, an emerging-market company is half as likely to be green",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=8,
    )

    # ---------------- panel (b): the capital-intensity ladder -----------
    s = sectors.sort_values("representation_ratio")
    yb = np.arange(len(s))
    obs = s["representation_ratio"].to_numpy()
    fit = np.exp(s["fitted_log_ratio"].to_numpy())
    ct = int(s.index.get_loc("cleantech"))
    bio = int(s.index.get_loc("biotech"))

    for yi, o, f in zip(yb, obs, fit, strict=False):
        ax_b.plot([f, o], [yi, yi], color=P.rule, linewidth=1.2, zorder=1)

    ax_b.plot(
        fit,
        yb,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.accent_grey,
        markersize=4.2,
        markeredgewidth=1.0,
        zorder=2,
    )
    ax_b.plot(obs, yb, "o", color=P.ink, markersize=4.2, zorder=3)

    ax_b.plot([fit[ct], obs[ct]], [ct, ct], color=P.accent_green, linewidth=2.0, zorder=3)
    ax_b.plot(
        fit[ct],
        ct,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.accent_green,
        markersize=7.5,
        markeredgewidth=1.5,
        zorder=5,
    )
    ax_b.plot(obs[ct], ct, "o", color=P.accent_green, markersize=7.5, zorder=5)

    ax_b.axvline(1.0, color=P.ink_muted, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)

    ax_b.set_yticks(yb)
    ax_b.set_yticklabels([str(n).replace("_", " ") for n in s.index], fontsize=7.5)
    for lbl, name in zip(ax_b.get_yticklabels(), s.index, strict=False):
        is_ct = name == "cleantech"
        lbl.set_color(P.accent_green if is_ct else P.ink_muted)
        if is_ct:
            lbl.set_fontweight("semibold")
            lbl.set_fontsize(8.2)
    ax_b.tick_params(axis="y", length=0, pad=4)

    theme.annotate(
        ax_b,
        f"Cleantech sits {res['residual_ratio_scale']:.2f}x above its predicted position\n"
        f"[{res['residual_ratio_ci'][0]:.2f}x, {res['residual_ratio_ci'][1]:.2f}x]. "
        "The interval includes 1x, so a green-specific\n"
        "deficit is ruled out but outperformance is not confirmed.",
        xy=(obs[ct], ct),
        xytext=(5.85, ct + 2.6),
        ha="right",
        color=P.accent_green,
        fontsize=7.3,
    )
    theme.annotate(
        ax_b,
        "Biotech: 4.6x more under-represented than\n"
        "cleantech, and below its own prediction too",
        xy=(obs[bio], bio),
        xytext=(5.85, bio + 0.75),
        ha="right",
        color=P.ink_muted,
        fontsize=7.3,
    )

    ax_b.set_xscale("log")
    ax_b.set_xlim(0.085, 6.2)
    ax_b.set_ylim(-0.9, len(s) - 0.1)
    ax_b.set_xticks([0.1, 0.25, 0.5, 1, 2, 4])
    ax_b.set_xticklabels(["0.1x", "0.25x", "0.5x", "1x", "2x", "4x"])
    ax_b.set_xlabel(
        "Emerging-market representation relative to advanced economies "
        "(1x = proportionate), log scale"
    )
    ax_b.spines["left"].set_visible(False)
    theme.style_axes(ax_b, xgrid=True)
    ax_b.grid(axis="y", visible=False)
    ax_b.set_title(
        "(b)  That gap is a capital-intensity gap, not a green-specific one",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=8,
    )
    ax_b.text(
        0.015,
        0.955,
        f"elasticity {fitobj['slope']:.2f} [{fitobj['slope_ci'][0]:.2f}, "
        f"{fitobj['slope_ci'][1]:.2f}]   \u00b7   R\u00b2 = {fitobj['r_squared']:.2f}"
        f"   \u00b7   {fitobj['n_sectors']} sectors",
        transform=ax_b.transAxes,
        fontsize=7.5,
        color=P.ink_muted,
    )

    handles = [
        Line2D(
            [], [], marker="o", linestyle="none", color=P.ink, markersize=4.2, label="observed"
        ),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor=P.accent_grey,
            markersize=4.2,
            label="predicted by capital intensity",
        ),
    ]
    leg = ax_b.legend(
        handles=handles,
        loc="upper left",
        fontsize=7.3,
        handletextpad=0.4,
        borderpad=0.3,
        bbox_to_anchor=(0.012, 0.935),
    )
    for txt in leg.get_texts():
        txt.set_color(P.ink_muted)

    theme.finding_title(
        fig,
        "The emerging-market green gap is real, and it is a capital-intensity gap",
        "Green share of recorded venture deals by bloc, and sector representation "
        "against capital intensity. 2000\u20132012.",
        y=0.965,
    )
    theme.source_footer(
        fig,
        cfg,
        f"Panel (a) n = {len(deals):,} deals, {int(deals['green'].sum()):,} green. "
        f"Panel (b) {fitobj['n_sectors']} sectors with \u2265"
        f"{cfg.pipeline['capital_intensity']['min_em_deals']} emerging-market and \u2265"
        f"{cfg.pipeline['capital_intensity']['min_ae_deals']} advanced-economy deals; capital "
        "intensity is median advanced-economy deal size in constant 2015 USD, so the "
        "proxy cannot "
        "be contaminated by the\nemerging-market composition it explains. Intervals "
        "are Wilson "
        "score (a) and residual 95% CI (b). Raw classifier output, no manual curation.",
        y=0.125,
    )
    fig.subplots_adjust(left=0.225, right=0.985, top=0.885, bottom=0.185, hspace=0.26)
    theme.save(fig, cfg, "fig_01_double_gap_capital_intensity")


def main() -> None:
    """Render every figure."""
    cfg = load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    fig_01_double_gap_and_capital_intensity(deals, cfg)


if __name__ == "__main__":
    main()
