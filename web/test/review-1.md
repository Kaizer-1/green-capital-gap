# Review pass 1

Captures reviewed: 4 full-page (1440, 1024, 834, 390), 12 sections × 4 viewports,
13 figures × 4 viewports, 4 sequence steps + mid-transition, stacked and
reduced-motion states, no-JS. Geometry claims below are measured from the live
page, not estimated from the image.

As expected, this pass is mostly layout and geometry. Two findings are structural
rather than cosmetic: the active-step marker and the track width.

| # | Screenshot | Issue | Sev | Fix |
|---|---|---|---|---|
| 1 | `390-s-capital`, `scrolly-stacked-390` | The stacked sequence sets `data-active="true"` on all four steps, so the new active-step rule paints `--cleantech` down the entire section — beside the graphics as well as the captions. A marker that means "you are here" marks everywhere. Introduced by the step-9 contrast fix. | **1** | Scope the rule to `[data-layout="pinned"]`, where it discriminates. Drop the indent in the stacked layout too. |
| 2 | every 1440 prose section | The grid track is `--measure-extra` (54rem) but exactly one element uses that width — fig04's 6-column data table. Prose therefore sits 288px from the left edge and 608px from the right on a 1440 viewport. The asymmetry is deliberate (figures break right off a shared left edge) but 54rem overshoots what anything needs, and the surplus all lands on the right. | **2** | Track to `--measure-wide` (46rem) → 352/544. Give `.extra-wide` its own symmetric breakout so the one wide table keeps its width. |
| 3 | `1440-s-capital` | The pinned graphic is **352 × 446** on a 1440 viewport. It is the centrepiece of the page's central argument and the smallest figure on it; the column split is `1fr / 1.05fr` inside an 864px track, and the graphic does not fill its half. | **2** | Widen the sequence to the full track and rebalance the columns toward the graphic. |
| 4 | `1440-s-finding` | The third statistic's interval breaks mid-token: `p =` ends one line and `7.5×10⁻⁶` starts the next. A broken p-value reads as two numbers. | **2** | Non-breaking space inside the p-value; `text-wrap: pretty` on the interval line. |
| 5 | `1440-s-finding` | The three stat labels run to 3, 4 and 2 lines, leaving the row ragged along the bottom, and stat 2 orphans the word `deals` onto a line of its own. | 3 | `text-wrap: balance` on `.stat__label`. |
| 6 | `1440-s-headermasthead` | The department line wraps to leave `of Engineering` alone on the second line. | 3 | `text-wrap: balance` on the byline affiliation. |
| 7 | `1440-s-capital` | The pinned graphic carries no n and no finding sentence of its own (rubric 15). The four captions carry the finding, which is the point of the format, but the figure is unlabelled if read on its own. | 3 | Put the sector count on the axis label, from `findings.json`. |
| 8 | `1440-s-capital` | `gap: 60vh` between step blocks means roughly half a screen of empty left column between captions. The previously-active caption stays lit, so nothing is *broken*, but the static frame reads as a gap rather than as a pause. | 3 | Reduce to a value that keeps one caption near the graphic's vertical centre throughout. |

## Rubric questions with nothing to report

1 (text overlap), 2 (clipping), 4 (right-edge cut-off), 10 (type under 13/15px),
11 (colour off-palette), 13 (`--alert` misuse), 14 (series identifiable without
colour), 16 (mobile chart legibility), 17 (rotated axis labels) — all clean
across every capture. 3 (shared left edge) holds: figure axis labels and captions
start at the prose left edge in every figure checked.

## Carried forward

Rubric 19 and 20 — whether it reads as one designed artefact — are not yet
answerable. Pass 1 found geometry. The question of rhythm across section types,
and whether the prose-only sections (`limits`, `built`) read as designed or as a
document pasted into a page, is for pass 2.
