# Review pass 2

Pass 1's eight findings applied. Captures re-run and opened at all four
viewports: 4 full-page, 12 sections × 4, 13 figures × 4, the sequence states,
stacked, reduced-motion and no-JS. Where a rubric question can be measured it
was measured in the browser rather than judged from an image — spacing, left
edges, caption lengths, label-to-line association and baseline alignment below
are computed, not estimated.

Pass 1 was geometry. This pass was rhythm, and most of what it looked for came
back clean. Three findings, two of them severity 2.

| # | Where | Issue | Sev | Fix |
|---|---|---|---|---|
| 1 | measured, all viewports | `--mono` is not declared. Fifteen `<code>` elements naming dataset fields and quoting literal values fall through to the browser's bare `monospace` keyword — Menlo here, Courier New on Windows. A third typeface appears on the page that nobody chose, and it changes by platform, which also changes the line lengths around it. The stylesheet states this rule for colour and does not enforce it for type. | **2** | Declare `--mono` with a considered stack, applied to `code` at 0.92em since monospace runs optically large. |
| 2 | measured, 1440 | The `extra-wide` data table started at **288px** while every other element on the page — prose, all thirteen figure captions, all thirteen source lines and the leftmost ink of all thirteen charts — starts at **352px**. The shared left edge is this page's strongest alignment and exactly one element broke it, which reads as a mistake rather than as emphasis. | **2** | Break out to the right only, by the space actually available between the track's right edge and the gutter. |
| 3 | `1440-s-headermasthead` | The masthead's three metadata lines are identical: 15px, `--ink-muted`, 4px apart. Nothing marks the guidance line, which is the one an examiner looks for. | 3 | Guidance line to `--ink`; department and date stay secondary. Two tiers, no new size. |

## The weighted questions, answered

**Section-to-section spacing — clean.** All eleven sections compute
`padding-block: 96px` top and bottom with a 1px `--rule` top border. No section
type has grown its own spacing, including the three that differ most in content
(the scrollytelling section, the table-and-diagram section, and the colophon).

**Figure caption length — considered, not uneven.** Source lengths run 205–557
characters. Every one has the same structure: a bold sentence stating the
finding, then the unit and window, then the caveat that figure needs. The
variance tracks how much each figure has to explain rather than drifting — the
longest is Figure 1, which establishes the interval method and the bloc
definitions for everything after. No change.

**Monotony across the five `lines.js` time series — not a problem.** Figures 1,
3, 5, 8 and M1 were stacked into one sheet and read together. They are
differentiated by palette (grey/teal, ochre/teal, green/grey, green/grey with a
shaded event band, red against two greys), by x axis (four on years, M1 on
months), by annotation device (two carry a vertical rule and callout, one a
shaded band, two neither), by line style, and M1 carries three series rather
than two. They read as five exhibits, not one chart five times.

**Terminus labels — checked, correct.** Every label in all five sits within 2px
of its own line's end. The de-collision rule was a candidate for pulling a label
nearer a neighbour's line than its own; it does not.

**The §1 stat trio — fixed.** All three values share a baseline at y = 1282, all
three intervals occupy two lines, all three labels end at y = 1479. The
`p = 7.5×10⁻⁶` no longer breaks mid-expression.

**§9 and §10 against §1–8 — different in kind, not in document.** They are the
only sections with `h3` subheadings and the only ones with no figure, and
together they are a third of the page. That is real, and it is not fixed by
inventing exhibits for them: what makes a page cohere is the grid, and the grid
holds. They share the left edge, the 96px rhythm, the section numbering, the
type scale and the caption-free prose measure with everything before them. The
defect list has strong internal rhythm of its own — bold claim, prose, ruled
"Caught by" block, separator — which earns its difference instead of merely
having one. No change.

## Rubric 19 and 20, deferred from step 2

**19. One designed artefact, or a stack of components?** One artefact. The test
is whether the same decisions recur without being restated, and they do: one
left edge holding across every element at every viewport, one spacing interval
between all eleven sections, one palette with its roles fixed in `theme.py` and
shared with the PDF, six type sizes and no seventh, one caption structure in all
thirteen figures, and one rule — role is carried by geometry, not by contrast —
applied in four separate places (the step captions, the "Caught by" blocks, the
confidence intervals and the residuals). The page's weakest seam is the
transition from §8 to §9, where exhibits stop; the grid carries it.

**20. Would a hiring engineer think a person made this, or a template?** A
person. A template produces even surfaces; it does not produce the specific,
awkward, content-driven decisions here. Figure 2 draws the LDC row as a point
with no interval and says *0 of 13 deals: no usable interval* on the figure
itself rather than drawing a bar to 22.81 on a 0–9 axis. Figure 11 panel (b) is
deliberately inert because its finding is that there is nothing to explore, and
its caption says so. Figure 7's toggle morphs bars in place rather than
redrawing, because dollars peaking a year before deals is visible in the
transition and invisible in two static panels. The label tones are darkened
variants of the palette hues because direct labelling makes those hues text and
three of them fail as text. None of that is a default, and none of it is
decorative. §9 then shows the work by listing eleven defects, three of them
found in the instruments rather than the results.

The reservation: a reader who opens only §1 sees a well-set title page and three
statistics, and the page's strongest evidence of craft is a long way down.

## Clean across every capture

Rubric 1 (text overlap), 2 (clipping), 4 (right-edge cut-off), 5 (empty
regions), 6 (45–75 character measure), 7–8 (orphans and widows, after pass 1's
`text-wrap: balance`), 9 (type scale, now that the third family is declared),
10 (minimum sizes), 11 (off-palette colour), 12 (decoration), 13 (`--alert`
confined to thresholds and failures), 14 (series identifiable without colour),
15 (finding sentence and n on every figure), 16 (mobile legibility), 17 (no
rotated axis labels anywhere), 18 (the first viewport states what this is).
