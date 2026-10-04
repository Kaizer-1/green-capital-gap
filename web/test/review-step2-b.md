# Review 2 — after the review-1 fixes

Re-captured at all four viewports plus reduced-motion and no-JS. All twenty
screenshots opened and assessed against the §10.3 rubric. Capture clean: no
console errors or warnings, no horizontal overflow anywhere.

## Carried over from review 1

| # | Status |
|---|---|
| 1 clipped bloc labels | Fixed. Left margin is measured from the longest label instead of a constant. |
| 2 LDC interval off-canvas | Fixed. Clipped at the domain edge with an arrow cap, so the interval reads as continuing rather than stopping. |
| 3 clipped "below the minimum cell" note | Fixed. Removed from the plot; the detail is in the caption, where it belongs. |
| 4 22-character measure at 390 | Fixed, but not by the fix proposed in review 1 — see #12 below. Now ~60 characters at desktop, ~45 at mobile. |
| 5 unreadable figure at mobile | Fixed, in two stages — see #13. |
| 6 empty statistics with JS off | Fixed. Prose reads as sentences; statistic-bearing blocks are hidden by a flag set before first paint. |
| 7 bracket implying a four-way comparison | Fixed, then re-fixed — see #14. |
| 8 invisible link underlines | Fixed. `--ink-muted` instead of `--rule`. |
| 9 `<dd>` before `<dt>` | Fixed, and it broke the layout — see #15. |
| 10 "0.00%" crowding the row above | Fixed by the label-above layout change. |
| 11 empty right 40% at 1440 | Resolved by #2. The band is a centred 54rem measure; the margins are margins, not a crammed layout. |

## New findings this pass

| # | Screenshot | Issue | Sev | Fix |
|---|---|---|---|---|
| 12 | `1440-fig02` | The figure rendered in the compact layout at 1440. Its container measured 544px, not 864px: the grid item is the `<section>`, and review-1's fix capped the *section* at 34rem, so `.wide` on a figure inside it could never break out. The `minmax(0, 54rem)` track also sized itself to its content rather than its growth limit. | 1 | Two changes: a definite `min(100%, 54rem)` track, and move the measure cap from the grid item to the section's children so `.wide` has somewhere to go. Verified: figure 864px / prose 544px at 1440, both starting at x=288. |
| 13 | `390-fig02` | Even in the compact layout the figure text rendered at 12.3px, under the rubric's 15px mobile floor, because a 360-unit canvas scaled to 0.95 in a 342px container. | 1 | Compact canvas narrowed to 340 units so the SVG renders at about 1:1, and compact text set to 16px. Measured: 16.1px at 390, 14.8px at 1440, 13.4px at 834. |
| 14 | `1440-fig02` | The broken-spine bracket from review 1 read as two stray marks rather than as a bracket. | 2 | Restored a plain bracket with one spine and two arms. The "EM vs AE" label is what disambiguates which rows are compared; breaking the spine cost more legibility than the ambiguity was worth. |
| 15 | `1440-s-finding` | Reordering to `<dt>`-then-`<dd>` put each label above its value, and because the three labels run to different line counts the values no longer shared a baseline. | 1 | `.stats` is a three-column, three-row grid and `.stat` is `display: contents`, so values, intervals and labels each occupy one shared row. DOM order stays label-first for assistive technology. |
| 16 | `nojs-full` | With the statistic span hidden, one sentence ended "still leaves it ." — a stranded full stop. | 2 | Moved the word "open" outside the hidden span, so the sentence closes either way. |
| 17 | `390-full` | At mobile the stats read label-then-value, at desktop value-then-label. The same component, two reading orders. | 2 | Mobile `.stat` is a flex column with explicit `order`, matching the desktop sequence while keeping the DOM order. |
| 18 | `nojs-full` | The byline — authors, USNs, guide, institution — is absent with JS off, because it is read from `metadata.yaml` by way of `series.json`. | 3 | Not fixed, deliberately. Putting the names in the HTML would restate the file that the PDF title page, the README and this all read from, which is the duplication the single-source rule exists to prevent. The noscript banner now says the author list is resolved the same way and points at the PDF. |

## Rubric questions with nothing to report

1, 2 (no overlapping or clipped text at any viewport, verified in the figure
crops at all four widths), 3 (figure and prose share a left edge at every
viewport — measured, not eyeballed: x=288 at 1440, x=80 at 1024, x=24 at 834 and
390), 4 (no horizontal overflow; the capture asserts it), 6 (~60 characters at
desktop, ~45 at mobile), 7 and 8 (no orphans or widows in the current copy), 9
(six declared sizes, no one-off), 10 (nothing under the floor after #13), 11, 12,
13 (palette verified against computed styles; `--alert` appears only on the
noscript border), 14 (every series directly labelled), 16 (after #13), 17 (no
rotated axis labels anywhere), 18.

## Still not assessable

15 — true of Figure 2, but thirteen figures do not exist yet. 19 and 20 need more
than one section on screen before the question means anything. Both are held for
the review pass after §§2–10 are built.
