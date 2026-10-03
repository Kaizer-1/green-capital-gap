"""Make a figure's ink span its canvas exactly, without resizing the canvas.

The problem this solves: axes positions are set with `subplots_adjust` fractions
chosen by hand per figure. The fraction that leaves no slack depends on how wide
the y-tick labels and the y-axis label happen to render, which differs by figure
and by font. The result is that every figure in the document has a different
left and right margin, so no two share an edge and none lines up with the caption
beneath it.

`bbox_inches="tight"` fixes the symptom by cropping the canvas, which changes the
output width and therefore makes the figure scale when embedded. That is banned
for print variants (see print_mode).

This does the inverse: measure where the ink actually is, then move the axes out
to meet the canvas edges. Canvas size never changes, so a 6.22in figure stays
6.22in and every figure in the document shares the same ink extent.

Two passes by default. One pass is not enough: expanding the axes changes the
data limits slightly for autoscaled axes, which changes tick label widths, which
moves the ink. The second pass converges it. A third buys nothing measurable.

Usage, at the end of every figure function, after all artists are added:

    from gcg.viz.flush_fit import flush_fit
    flush_fit(fig)
    return fig

Incompatible with `constrained_layout` and `tight_layout`; both are asserted off.
"""

from __future__ import annotations

import logging

from matplotlib.figure import Figure

log = logging.getLogger(__name__)

# Keep a hair of padding so a glyph's antialiased edge is not clipped by the
# PDF bounding box. 0.01in at 300dpi is 3px; invisible, but enough.
EDGE_PAD_IN = 0.01

# If a pass wants to move a margin by more than this, something is wrong —
# usually an artist placed in figure coordinates far off-canvas. Warn loudly
# rather than silently producing a squashed figure.
MAX_SHIFT_IN = 2.0


def _layout_engine_active(fig: Figure) -> bool:
    engine = fig.get_layout_engine()
    return engine is not None and engine.__class__.__name__ != "PlaceHolderLayoutEngine"


def flush_fit(
    fig: Figure,
    *,
    passes: int = 2,
    pad_in: float = EDGE_PAD_IN,
    left: bool = True,
    right: bool = True,
    bottom: bool = True,
    top: bool = True,
) -> Figure:
    """Expand the subplot area so the figure's ink meets the canvas edges.

    Parameters
    ----------
    fig
        Figure whose axes are positioned by `subplots_adjust` (the default).
    passes
        Measure/adjust cycles. Two converges; one leaves a few points of slack
        on axes whose tick labels change width when the axes grows.
    pad_in
        Padding retained at each edge, in inches.
    left, right, bottom, top
        Per-edge opt-out. Switch an edge off when a figure deliberately reserves
        a gutter there — a right-hand label column, for instance.

    Returns
    -------
    The same figure, adjusted in place.
    """
    if _layout_engine_active(fig):
        raise RuntimeError(
            "flush_fit is incompatible with constrained_layout/tight_layout. "
            "Set layout=None on the Figure; flush_fit replaces them."
        )

    width_in, height_in = fig.get_size_inches()

    for pass_no in range(passes):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ink = fig.get_tightbbox(renderer)  # inches, origin at canvas bottom-left

        sp = fig.subplotpars
        new = {"left": sp.left, "right": sp.right, "bottom": sp.bottom, "top": sp.top}

        # Slack is the gap between the canvas edge and the outermost ink.
        # Positive slack means wasted space; negative means ink is overflowing
        # and the axes must come in rather than go out.
        if left:
            slack = ink.x0 - 0.0
            new["left"] = sp.left - (slack - pad_in) / width_in
        if right:
            slack = width_in - ink.x1
            new["right"] = sp.right + (slack - pad_in) / width_in
        if bottom:
            slack = ink.y0 - 0.0
            new["bottom"] = sp.bottom - (slack - pad_in) / height_in
        if top:
            slack = height_in - ink.y1
            new["top"] = sp.top + (slack - pad_in) / height_in

        for edge, value in new.items():
            span = width_in if edge in ("left", "right") else height_in
            shift_in = abs(value - getattr(sp, edge)) * span
            if shift_in > MAX_SHIFT_IN:
                log.warning(
                    "flush_fit: %s margin wants to move %.2fin on pass %d. "
                    "An artist is probably placed off-canvas in figure coords.",
                    edge,
                    shift_in,
                    pass_no,
                )

        # Guard against a degenerate axes if the measurement goes wrong.
        if new["left"] >= new["right"] or new["bottom"] >= new["top"]:
            log.warning(
                "flush_fit: computed margins would invert the axes "
                "(l=%.3f r=%.3f b=%.3f t=%.3f); leaving this pass unapplied.",
                new["left"],
                new["right"],
                new["bottom"],
                new["top"],
            )
            break

        fig.subplots_adjust(**new)

    return fig


def measure_slack(fig: Figure) -> dict[str, float]:
    """Slack at each edge in inches. Zero on all four means flush.

    Used by the render gate: a print variant with more than ~0.03in of slack on
    any edge did not get flush_fit applied, and will not line up with its
    neighbours in the document.
    """
    fig.canvas.draw()
    ink = fig.get_tightbbox(fig.canvas.get_renderer())
    width_in, height_in = fig.get_size_inches()
    return {
        "left": ink.x0,
        "right": width_in - ink.x1,
        "bottom": ink.y0,
        "top": height_in - ink.y1,
    }
