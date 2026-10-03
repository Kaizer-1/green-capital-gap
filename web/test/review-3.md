# Review 3 — masthead and §1, Figure 2 static

Third pass. All twenty screenshots opened and assessed against the §10.3 rubric,
plus two properties screenshots cannot show, measured in the browser instead.

**No severity-1 or severity-2 findings.** The stopping condition in WEB.md §10.3
is met for this step.

## Measured, not eyeballed

| Property | Result |
|---|---|
| Horizontal overflow | None at 1440, 1024, 834 or 390 |
| Console | No errors, no warnings at any viewport |
| Shared left edge (prose vs figure) | x = 288 / 288 at 1440, 80 / 80 at 1024, 24 / 24 at 834, 24 / 24 at 390 |
| Figure breakout | 864px against 544px of prose at 1440; 786 / 544 at 834 |
| Prose measure | ~60 characters at desktop, ~45 at mobile |
| Figure text, effective | 14.8px at 1440, 13.4px at 834, 16.1px at 390 |
| Body contrast on canvas | 18.43:1 (requirement ≥ 7:1) |
| Secondary text contrast | 5.13:1 (requirement ≥ 4.5:1) |
| Reduced motion | Zero elements with a non-zero transition or animation duration |

## Findings

| # | Screenshot | Issue | Sev | Fix |
|---|---|---|---|---|
| 19 | `*-fig02` | The "EM vs AE" bracket label sits at the vertical centre of its spine, which puts it level with the "No country recorded" row. A reader's eye can associate the label with that row rather than with the bracket. | 3 | Not fixed. Centring is the convention for a bracket label, and the alternatives are worse: at the top it reads as belonging to the advanced-economy row, and offsetting it breaks alignment with the other gutter content. Revisit if a second gutter annotation ever lands beside it. |
| 20 | `*-fig02` | The least-developed interval, clipped at 9% with an arrow, is the longest line in the chart and draws the eye to the least informative row. | 3 | Not fixed, deliberately. The interval genuinely runs to 22.81%; drawing it short, or omitting it, would make thirteen deals with no green ones look more precise than it is. The arrow is the honest rendering and the caption explains it. |
| 21 | `tokens.css` | `--canvas-alt` is declared and never used. | 3 | Left in place. It is the single alternate band colour and §6 of the build order has sections that will want it; an unused token is cheaper than a colour invented later outside the palette. |

## Rubric, question by question

*Layout.* 1 — no text overlaps text or a mark at any viewport. 2 — nothing
clipped; the two clipping defects from review 1 (bloc labels, the off-domain
interval) are gone, and the compact layout's first tick label now has room for
its own width. 3 — figures share the prose left edge, measured above. 4 —
nothing past the right edge; the capture asserts it. 5 — the page is a centred
54rem band; the margins either side are margins, not a crammed layout. 6 —
measure within range at both ends.

*Typography.* 7 — no orphans in the current copy. 8 — no widows; the sections
are short enough that nothing strands a line. 9 — six declared sizes, all used,
no one-off has crept in. 10 — nothing below the floor at any viewport after the
compact type fix.

*Colour and tone.* 11 — every colour on screen resolves to a token in §4's list,
verified against computed styles rather than by eye. 12 — nothing decorative:
the only non-text marks are the progress rail, the masthead rule, section rules
and the chart. 13 — `--alert` appears only on the noscript border; it marks
nothing decorative.

*Charts.* 14 — every series is labelled directly, so colour carries nothing on
its own. 15 — Figure 2 carries its finding sentence in the caption and its n on
every row. 16 — the compact layout re-lays out rather than scaling down. 17 — no
rotated axis labels.

*Overall.* 18 — the first viewport gives the title, the subtitle, one sentence on
what the project is, the authors and the links, without scrolling.

## Held until the page is complete

19 ("one designed artefact or a stack of components") and 20 ("would a hiring
engineer think a person made this") cannot be answered honestly with one section
and one figure on the page. There is not enough on screen for either question to
discriminate. Both are deferred to the review loop at build step 10, which is
where WEB.md puts them.

The same applies to rubric 15 as a general claim: it holds for Figure 2, and
thirteen figures do not exist yet.

## What changed across the three passes

Pass 1 found layout breaks: five severity-1 defects, of which the worst was that
the four-track grid gave its gutters priority and left a 22-character measure at
390px.

Pass 2 found that two of pass 1's fixes were wrong. Capping the grid item at the
prose measure stopped figures breaking out at all, and reordering `<dt>` before
`<dd>` broke the alignment of the three headline statistics. Both were caught by
looking at the screenshots rather than by trusting the change.

Pass 3 found nothing above severity 3. That is the point at which the rubric says
to stop.
