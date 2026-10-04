# Review pass 3

Pass 2's three findings applied. Captures re-run and opened at all four
viewports. One finding, severity 3, and it took three attempts to fix properly
because the first two fixed the symptom.

**No severity-1 or severity-2 findings. The stopping condition in WEB.md §10.3
is met.**

| # | Where | Issue | Sev | Fix |
|---|---|---|---|---|
| 1 | measured, 390 | The y tick labels are right-anchored to the axis, so the widest one reaches further left than the rest. In four of the five time series it reached **2.5px past the content edge**, breaking the single alignment the whole layout is built on. | 3 | Derive the left margin from the widest tick, measured on a real node. |

## Why that took three attempts

Worth recording, because the first two attempts both "worked" and both left the
defect in place.

1. **Size the margin from the widest tick.** No effect: `labelWidth` returned
   26.4px for a label the browser draws at 36.5, so the computed margin never
   exceeded the 42px constant it was meant to replace.
2. **Measure at the size the compact layout actually uses** — 16px, not the
   nominal 13. Closer: two figures of four fixed, two still spilling.
3. **Stop estimating.** `labelWidth` was `text.length * size * 0.55`. Canvas
   measurement was nearer but still short, because `.tick-label` sets
   `font-variant-numeric: tabular-nums` and canvas cannot apply it. The
   measurement now happens on an offscreen SVG text node carrying the same class
   as the label being measured, so it inherits every rule that will apply to the
   real one.

The pattern is the one §8 of the page catalogues: an instrument reporting a
number that was not the number asked for. Nothing failed at any point — the
margin was computed, the chart drew, the checks passed. It was wrong by 10px and
only measurement showed it.

## Verified across all four viewports

| Property | 1440 | 1024 | 834 | 390 |
|---|---|---|---|---|
| Distinct left edges across 93 elements | **1** (352px) | **1** (144px) | **1** (49px) | **1** (24px) |
| Horizontal overflow | 0 | 0 | 0 | 0 |
| Section spacing | 96px × 11 | 96px × 11 | 96px × 11 | 96px × 11 |
| Contrast floor (body ≥ 7:1, secondary ≥ 4.5:1) | pass | pass | pass | pass |
| Console errors or warnings | 0 | 0 | 0 | 0 |

The 93 elements are every section paragraph and heading, all thirteen figure
captions, all thirteen source lines, and the leftmost rendered ink of all
thirteen charts. One edge at each width, not a tolerance band.

## Rubric, third pass

Nothing new under 1–18. Specifically re-checked after pass 2's changes:

- **9, type scale.** `--mono` is now declared and `code` resolves to
  `ui-monospace` rather than the browser keyword. Three families, six sizes,
  no seventh.
- **3, shared left edge.** The `extra-wide` table breaks out to the right only
  and starts on the common edge at every width.
- **16, mobile legibility.** The wider left margin narrows the compact plots by
  about 7px. Checked on all five: tick labels, terminus labels and annotations
  all still read, and the in-plot labelling the compact layout uses instead of a
  gutter is unaffected.

**19 and 20** were answered in pass 2 and nothing here changes them. If
anything, this pass strengthens 20: the single left edge is the sort of thing
that is invisible when right and conspicuous when wrong, and it now holds by
measurement rather than by a constant that happened to work at desktop.

## What remains open, and is not a design finding

The reservation recorded in pass 2 stands: a reader who opens only §1 sees a
well-set title page and three statistics, and the page's strongest evidence of
craft — the sequence in §5, the toggle in §6, the defect list in §9 — is a long
way down. That is a consequence of the argument's order, which runs
denominator → gap → mechanism, and reordering it to lead with the most
impressive exhibit would put the qualifier before the claim. Left as is,
deliberately.
