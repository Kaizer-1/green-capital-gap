# WEB.md — The Green Capital Gap, web edition

> Build spec for the web version of the report. Read this fully before writing any
> code. `CLAUDE.md` still governs: no hand-typed numbers, no fabricated data, no
> recomputation outside the Python pipeline.
>
> This is a portfolio artefact, not a graded one. `report.pdf` is the submission.
> Nothing here changes that, and nothing here may change a number in it.

---

## 0. What this is

A standalone web version of the report that someone can read instead of the PDF,
and that a technical reader can skim in ninety seconds and come away with: this
person can do real analysis, and knows how to present it.

Two audiences, one page:

- **A reader who wants the findings.** Gets the full argument, in order, with
  figures that explain themselves. Never needs the PDF.
- **A reader assessing the engineer.** Gets §8, "How this was built", which is
  the methodology, the pre-registrations and the defect list. That section is
  the one that matters for this audience and it must not read as an appendix.

Deployed to GitHub Pages. No server, no build step, no bundler.

---

## 1. Non-negotiables

1. **Every number on the page comes from `findings.json`.** Same rule as the
   report, same enforcement. An element carrying a statistic uses
   `data-key="h1.rr"`, and a loader resolves it at runtime. A hard-coded
   statistic in HTML is a build failure.
2. **No recomputation in JavaScript.** Charts render pre-computed series exported
   by the Python pipeline. JS positions marks; it does not derive values. If a
   chart needs a number the export doesn't have, add it to the export — do not
   compute it in the browser.
3. **No synthetic or placeholder data.** If an export is missing, the chart fails
   loudly with a visible message. Never a plausible-looking stand-in.
4. **If `report.pdf` and the web version disagree on any number, the build is
   broken.** Both read the same `findings.json`; a disagreement means one of them
   stopped doing that.

---

## 2. Architecture

No framework, no bundler, no build step. Vanilla ES modules, D3 v7 from a pinned
CDN. This is deliberate: a toolchain is one more thing to debug in a one-shot
build, and this page does not need one.

```
web/
├── index.html
├── css/
│   ├── tokens.css          # the design system — colours, type, spacing
│   └── layout.css          # everything else
├── js/
│   ├── main.js             # entry: load data, resolve keys, wire observers
│   ├── data.js             # fetch + validate findings.json and series.json
│   ├── reveal.js           # IntersectionObserver animation triggers
│   ├── scrolly.js          # the one pinned sequence (§5)
│   └── charts/
│       ├── theme.js        # palette, scales, shared axis/label helpers
│       ├── fig01_coverage.js
│       ├── fig02_double_gap.js
│       ├── fig03_rate_by_year.js
│       ├── fig04_ladder.js
│       ├── fig05_share_crossover.js
│       ├── fig06_subdomain.js
│       ├── fig07_cycle.js
│       ├── fig08_crisis.js
│       ├── fig09_instruments.js
│       ├── fig10_depth_need.js
│       ├── fig11_power_wall.js
│       ├── fig12_continuity.js
│       ├── figM1_censoring.js
│       └── figM2_elasticity.js
├── data/
│   ├── findings.json       # copied from outputs/ by `make web`
│   └── series.json         # NEW export — see §3
└── test/
    ├── capture.mjs         # Playwright screenshot capture
    ├── checks.mjs          # Playwright automated assertions
    ├── rubric.md           # what to look for in the screenshots
    └── screens/            # output, gitignored
```

Add to the Makefile:

```make
web-data:   # export series.json + copy findings.json into web/data
web-test:   # node test/checks.mjs && node test/capture.mjs
web:        web-data web-test
```

---

## 3. The series export

New Python module `src/gcg/web/export_series.py`. It reads the same analysis
frames the figures read and writes `web/data/series.json`. It computes nothing
new — it reshapes what already exists into plot-ready arrays.

Shape, one key per figure:

```json
{
  "schema_version": 1,
  "generated_from_commit": "87c48f9",
  "fig02_double_gap": {
    "marks": [
      {"bloc": "Advanced economies", "rate": 5.43, "ci": [5.20, 5.66],
       "n": 37896, "green": 2056, "colour_role": "ae"}
    ],
    "annotations": [{"id": "em_vs_ae", "text_key": "h1.rr_formatted"}],
    "axis": {"x": {"domain": [0, 9], "unit": "%", "label": "..."}}
  }
}
```

Rules:
- Every mark carries everything its tooltip needs. No lookups across objects.
- `colour_role` is a semantic name (`em`, `ae`, `china`, `ldc`, `green`,
  `nongreen`, `cleantech`, `muted`) resolved against the palette in `theme.js`.
  Never a hex value — the palette lives in one place.
- Text that is a statistic is a `text_key` into `findings.json`, never a literal.
- `schema_version` is checked by the loader. A mismatch fails visibly.
- Round in Python using the existing `gcg.rounding` helper, so the web and the
  PDF round identically. This is the same defect that gave 5.42 against 5.43.

---

## 4. Design system

Inherit from `src/gcg/viz/theme.py` exactly. The web version and the PDF should
look like one project.

### Colour

```css
--ink:        #141413;   /* body text, primary marks */
--ink-muted:  #6E6E68;   /* captions, axis labels, secondary text */
--rule:       #E3E1DA;   /* hairlines, gridlines, borders */
--canvas:     #FFFFFF;   /* page */
--canvas-alt: #FAFAF7;   /* the one alternate band, used sparingly */

--em:         #0E7C7B;   /* emerging markets */
--ae:         #B5651D;   /* advanced economies */
--china:      #4A4A52;
--ldc:        #9C7B9B;
--green:      #3F7D3F;   /* green/cleantech series */
--nongreen:   #A8A69E;
--cleantech:  <read from theme.py>;  /* the ladder highlight */
--alert:      #B03A2E;   /* thresholds, failure markers — never decorative */
```

That is the entire palette. **No colour outside this list appears anywhere on the
page.** No gradient, no tint, no hover colour invented on the spot. A hover state
changes opacity or stroke width, not hue.

### Type

Two families, no more.

- Display and body: a serif — `"Charter", "Source Serif 4", Georgia, serif`
- UI, axis labels, captions, numbers in tables: a sans —
  `"Inter", "Source Sans 3", system-ui, sans-serif`

Load from Google Fonts with `display=swap` and a real fallback stack. Body 18px
at desktop, 17px at mobile, line-height 1.6, measure capped at **66 characters**
— set `max-width: 34rem` on prose blocks, not on the page.

Type scale, nothing between: 13 / 15 / 17–18 / 22 / 28 / 40.

### Layout

A single centred column for prose at 34rem. Figures break out to a wider
measure — up to 54rem — but **the figure's left edge aligns with the prose's left
edge**, never centred independently. That alignment is the single thing that
makes a page like this look composed rather than assembled.

Vertical rhythm on a 8px base. Section spacing 96px desktop / 56px mobile.

A thin fixed progress rail on the left at desktop, 2px wide, `--rule` track with
`--ink` fill. No circles, no labels, no section names. It disappears below
1100px.

### Banned outright

Gradients. Glassmorphism. Drop shadows on anything. Cards with rounded corners
and borders. A hero section with a background image or animated shapes. "Scroll
to explore" or a bouncing chevron. Counters that tick up from zero. Parallax.
Particles. A dark-mode toggle nobody asked for. Emoji. Icon fonts. More than two
typefaces. Any colour not in the list above. Full-bleed coloured section
backgrounds. Text over images. Centred body text. Justified text (the web
hyphenates badly).

---

## 5. Motion

Motion must carry meaning or it is decoration. The rule: an animation is
justified if removing it would cost the reader information about *order*,
*comparison* or *process*. Otherwise the element simply appears.

### Global

- Durations 400–900ms. Nothing faster (invisible), nothing slower (irritating on
  a second visit).
- Easing `cubic-bezier(0.4, 0.0, 0.2, 1)` for entrances; `linear` for line draws
  and progress. **No bounce, no elastic, no spring overshoot** — those read as
  decoration instantly.
- Stagger 40–60ms between sibling marks. Never more; a 20-bar chart staggered at
  100ms takes two seconds and the reader has moved on.
- Triggered once by `IntersectionObserver` at `threshold: 0.25`. **Never replays
  on scroll-back.** A chart that re-animates every time it enters the viewport is
  the single most annoying pattern on the web.
- `prefers-reduced-motion: reduce` → every duration to 0ms, final state rendered
  immediately, scrollytelling degrades to a static stack. Test this; it is an
  accessibility requirement, not a nicety.

### The one scrollytelling sequence

Section 4, the capital-intensity argument. This is the only place where a pinned
graphic earns its keep, because the argument is genuinely sequential and the
reader needs to watch a model get fitted and then beaten.

Graphic pins on the right (or above, at mobile). Four steps, text scrolls past:

1. **Observed.** 23 sector dots appear at their observed EM-representation
   positions, staggered. Cleantech is already coloured but not yet remarkable.
2. **The pattern.** The x-axis re-scales to capital intensity and the dots
   migrate to their scatter positions. Then the fit line draws, left to right,
   900ms linear. The reader watches the relationship appear.
3. **The prediction.** Hollow predicted-position markers drop in beneath each
   dot. Residual segments grow from predicted to observed, coloured by sign.
4. **The exception.** Everything else fades to 30% opacity. Cleantech's residual
   remains at full strength, and its label and interval appear. Beat. That is the
   finding.

At mobile the pin is unreliable across browsers — degrade to four stacked static
states, each revealed on scroll, with the same four captions. Do not attempt a
pinned graphic in a 390px viewport.

### Everything else

Figures animate once on reveal, in whatever way suits the mark type:

- Lines: stroke-dasharray draw, left to right, 700ms linear.
- Bars: grow from the axis, 500ms, staggered 50ms.
- Dots and CI whiskers: dot fades and scales from 0.6 to 1.0, 400ms; whisker
  extends from the dot outward, 400ms, 100ms after.
- Area fills: opacity 0 → final, 600ms, after the bounding lines have drawn.

Figure 11 (the power wall) gets one special touch and it is worth it: the bars
grow toward the `n = 30` threshold line **and visibly stop short**, with the
threshold line already drawn before they start. The whole argument of that figure
is "nothing reaches the line", and watching five bars fail to reach it says that
better than the caption does.

---

## 6. Content and structure

The web version carries the full argument. Someone who reads it should not need
the PDF.

```
0  Masthead          Title, subtitle, four authors + USNs, guide, institution,
                     date. One line on what the project is. A link to the PDF
                     and to the GitHub repo. No hero image, no tagline.

1  The finding       The abstract, rewritten for screen: shorter sentences,
                     the three headline numbers pulled out as large type with
                     their intervals beneath. Figure 2 (double gap) follows.

2  Why this is hard  The data problem. Why the open frontier stops in 2013 and
                     why that window is the right one. Figure 1 (coverage gap).

3  The double gap    §5.1-5.2 of the report. Figure 3 (rate by year).

4  Capital intensity THE SCROLLYTELLING SECTION. §5.3. Figures 4 and M2 become
                     one pinned sequence (§5 above).

5  What the record   §5.4 and §6 condensed. Figures 6, 7, 8, 9, 10.
   cannot say        Each hypothesis gets a verdict chip (see below).

6  Six routes        §6.6. Figure 11 (power wall) is the centrepiece.

7  Does it persist   §7. Figure 12 (continuity).

8  How this was      THE PORTFOLIO SECTION. Not an appendix — give it the same
   built             weight as the findings sections. Four parts:

                     (a) The pipeline. One diagram: sources → classifier →
                         bloc assignment → deal table → hypotheses → report.
                         Hand-authored SVG, not a chart library.
                     (b) Pre-registration. The five hypotheses with their
                         verdicts and the falsification condition each carried.
                         Make it legible that three failed and were kept.
                     (c) Defects this process caught. The five: the degenerate-
                         variance catch, the classify() leak, funding_round_code,
                         zeros-as-sentinel, COLUMN_IN scaling. Each one sentence
                         of what it was and one of how it surfaced. This is the
                         most impressive content on the page for a technical
                         reader.
                     (d) Reproducibility. Commit, Python version, seed, dataset
                         checksums, one command.

9  Limitations       §9, honestly, not softened for the web.

10 Colophon          Data sources with licences, tools, the figure design system,
                     a link to the repo and to report.pdf.
```

### Verdict chips

Each hypothesis shows a small inline chip: a 4px square in `--ink` for supported,
`--ink-muted` outline for partially supported, `--alert` outline for not
testable / underpowered, plus the word. **No green ticks, no red crosses, no
traffic lights.** Three of five are unresolved and the design must not make that
look like failure — it is the finding.

---

## 7. Interaction

Interactivity earns its place the same way motion does. Most figures need only
hover readouts. Four need more.

| Figure | Interaction |
|---|---|
| **4 / M2** | The pinned sequence. Plus: hover any sector for its name, observed, predicted and residual. A ladder ⇄ scatter toggle after the sequence completes, so the reader can switch views at will. |
| **7 cycle** | Toggle counts ⇄ dollars. Bars morph between the two series, 600ms. The finding — dollars peak a year before deals — is visible in the morph in a way two static panels cannot show. |
| **10 depth/need** | Hover a country for its name, green funding per capita and GDP per capita. Panel (b) stays deliberately static: the point is that there is nothing to explore. |
| **11 power wall** | Hover a bar for which test it blocks and what the cell contains. |

Everything else: hover readout only — a thin vertical rule on time series with
values at the cursor's year, a tooltip on categorical marks.

Tooltip rules: follows the cursor with 12px offset, flips at viewport edges,
`--canvas` background with a 1px `--rule` border, no shadow, no arrow, no
animation on appearance (it must feel instant), dismisses on mouse-out and on
Escape.

**Touch:** every hover readout must also work on tap. A chart that is dead on
mobile is a chart that half the portfolio audience never sees working.

---

## 8. Accessibility

Not optional, and a reviewer will check.

- Every chart: `role="img"` with an `aria-label` carrying the finding sentence,
  plus a visually-hidden `<table>` of the underlying series. The table is the
  screen-reader path and also the no-JS fallback.
- `<noscript>` block at the top explaining that charts need JS, with a link to
  the PDF.
- Keyboard: every toggle and every scrolly step reachable by Tab, operable by
  Enter/Space, with a visible focus ring (2px `--ink`, 2px offset — never
  `outline: none`).
- Contrast: body text ≥ 7:1 against canvas; axis labels and captions ≥ 4.5:1;
  chart marks ≥ 3:1. `--ink-muted` on `--canvas` is about 5.4:1, fine for
  captions, **not** fine for body text.
- Never encode a distinction by colour alone. Every series that is colour-coded
  is also labelled directly or differentiated by dash pattern.
- `prefers-reduced-motion` honoured throughout.

---

## 9. Performance

- Total page weight under 1.5MB including fonts.
- First contentful paint under 1.5s on simulated Fast 3G; largest contentful
  paint under 2.5s.
- D3 from a pinned CDN with SRI. Nothing else external except the fonts.
- Charts render on reveal, not all at load. Fourteen SVGs built at once blocks
  the main thread for noticeable time.
- No layout shift after load: every figure container has its aspect ratio
  reserved in CSS before the SVG exists.

---

## 10. Test protocol

This section is as important as the design. A one-shot build that is never looked
at is a one-shot build that ships broken.

### 10.1 Automated checks — `web/test/checks.mjs`

Playwright. Every one of these fails the build:

**Data integrity**
- [ ] Every `data-key` in the DOM resolves against `findings.json`. Report every
      unresolved key by name.
- [ ] Every chart module's required `series.json` key exists.
- [ ] `schema_version` matches.
- [ ] No digit-bearing text node inside a `.stat` element that did not come from
      a resolved key (the bare-number gate, ported).

**Rendering**
- [ ] Zero console errors and zero console warnings on load.
- [ ] All 14 figures present in the DOM with non-zero SVG bounding boxes.
- [ ] No horizontal overflow at 1440, 1024, 834, 768, 390 px widths —
      `document.documentElement.scrollWidth <= clientWidth` at each.
- [ ] No element's bounding box extends past the viewport's right edge.
- [ ] No two text nodes with overlapping bounding boxes inside any figure
      (catches collided labels — the defect class that plagued the PDF).

**Accessibility**
- [ ] Every `<svg>` has `role` and `aria-label`.
- [ ] Every chart has a sibling data table.
- [ ] Contrast ratios computed for every text/background pair; body ≥ 7:1,
      secondary ≥ 4.5:1.
- [ ] Tab order reaches every interactive control; focus ring visible on each.
- [ ] With `prefers-reduced-motion: reduce` emulated, no element has a non-zero
      `transition-duration` or `animation-duration`.
- [ ] Axe-core scan: zero violations at serious or critical.

**Behaviour**
- [ ] Each toggle changes the rendered output (compare SVG path data before and
      after; identical output means the toggle is wired to nothing).
- [ ] Tooltips appear on hover and on tap, and dismiss on Escape.
- [ ] Scrolling through the scrolly section and back does not re-trigger
      entrance animations.
- [ ] Page loads and renders with JS disabled, showing the noscript path and all
      data tables.

**Performance**
- [ ] Page weight under 1.5MB.
- [ ] LCP under 2.5s on simulated Fast 3G.
- [ ] Cumulative layout shift under 0.05.

### 10.2 Screenshot capture — `web/test/capture.mjs`

Capture to `web/test/screens/`:

**Viewports:** 1440×900, 1024×768, 834×1112, 390×844.

**Per viewport:**
- `{vp}-full.png` — full-page, scrolled through so lazy content renders
- `{vp}-s{n}.png` — each of the 11 sections, framed to fill the viewport
- `{vp}-fig{n}.png` — each of the 14 figures at its natural size

**Animation states** (desktop only, 1440×900):
- `scrolly-step{1..4}.png` — the pinned sequence at each step, captured after
  the transition settles
- `fig07-counts.png` / `fig07-dollars.png` — both toggle states
- `fig04-ladder.png` / `fig04-scatter.png` — both views
- `fig11-mid.png` — the power wall bars mid-growth, to check they read correctly
  while moving

**States:**
- `reduced-motion-full.png` — full page with reduced motion emulated
- `nojs-full.png` — full page with JS disabled
- `tooltip-fig10.png` — a tooltip open near the right viewport edge, to verify
  it flips rather than overflowing

### 10.3 The self-review loop — this is the part that matters

Capturing screenshots is worthless unless they are looked at. After capture,
**open every screenshot with the `view` tool and assess it against the rubric
below.** Not a sample — every one. Write the findings into
`web/test/review-{iteration}.md` as a table: screenshot, issue, severity, fix.

Then fix, re-capture, re-review. **Three iterations minimum.** The first pass
always finds layout breaks, the second finds alignment and rhythm problems, and
the third is where the page starts looking designed rather than assembled. Stop
when a pass produces no severity-1 or severity-2 findings.

**Rubric — check each screenshot for all of these:**

*Layout*
1. Does any text overlap any other text or any mark?
2. Is any label, tick or annotation clipped at a figure edge?
3. Do all figures share a left edge with the body text? Draw the line mentally
   down the screenshot — do they line up?
4. Is anything cut off at the viewport's right edge?
5. Is any region of the page more than 60% empty, with content crammed elsewhere?
6. Are prose line lengths between 45 and 75 characters?

*Typography*
7. Any orphan — a single word alone on the last line of a paragraph or heading?
8. Any widow — one line of a paragraph alone at the top of a screen?
9. Is the type scale consistent, or has a one-off size crept in?
10. Any text under 13px at desktop or under 15px at mobile?

*Colour and tone*
11. Any colour on screen that is not in §4's list?
12. Does anything read as decorative rather than informational?
13. Is `--alert` used anywhere it is not marking a threshold or a failure?

*Charts*
14. Is every series identifiable without relying on colour?
15. Does every figure carry its finding sentence and its n?
16. At mobile, is any chart squashed to the point of illegibility?
17. Are axis labels rotated anywhere they could have been avoided?

*Overall*
18. Does the first viewport say what this is and why it matters, without
    scrolling?
19. Does it look like one designed artefact or a stack of components?
20. **Would a hiring engineer think a person made this, or a template?**

Question 20 is the one to be honest about. If the answer is uncertain, the
problem is usually too many section types, inconsistent spacing between sections,
or a figure that is centred when everything else is left-aligned.

---

## 11. Build order

Checkpoints are not optional. Stop and report at each.

1. `export_series.py` + `make web-data`. Print the key list and one sample
   object. **Stop: show the user.**
2. `tokens.css` + `layout.css` + the masthead and §1 only, with Figure 2 static
   (no animation, no interaction). **Stop: capture at all four viewports, review
   against the rubric, show the user.** The design system is agreed here or it is
   re-litigated fourteen figures later.
3. `data.js` + key resolution + the data-integrity checks. Prove no hand-typed
   numbers.
4. `theme.js` + `reveal.js`, then figures 1, 3, 5, 6 — the simple ones — with
   entrance animation and hover readouts.
5. Figures 7, 9, 10, 11, 12, M1 — including the two toggles and the power-wall
   growth.
6. The scrollytelling sequence (figures 4 / M2). This is the hardest piece; do it
   when everything around it is stable. **Stop: capture all four steps, review.**
7. §8 "How this was built", including the hand-authored pipeline SVG.
8. Remaining prose sections, colophon, noscript path, data tables.
9. Full `checks.mjs`. Fix until green.
10. Review iterations: capture → view every screenshot → `review-1.md` → fix →
    repeat. Minimum three. **Stop: show the user `review-3.md` and the final
    full-page screenshots at all four viewports.**
11. GitHub Pages deploy. Verify the live URL renders identically to local —
    relative paths and case-sensitive filenames break on Pages and not locally.

---

## 12. Done means

- [ ] `make web` green: data export, all checks, all captures
- [ ] Three review iterations completed, final pass with no severity-1 or -2
- [ ] Every number traced to `findings.json`; zero hand-typed statistics
- [ ] No number on the page disagrees with `report.pdf`
- [ ] Renders correctly at 1440, 1024, 834 and 390
- [ ] Works with JS disabled (tables + PDF link) and with reduced motion
- [ ] Axe-core clean at serious and critical
- [ ] Under 1.5MB, LCP under 2.5s on Fast 3G
- [ ] Live on GitHub Pages, verified against local
- [ ] README links to it; the page links back to the repo and to `report.pdf`

---

## 13. If something is ambiguous

Default to less. Fewer colours, fewer animations, fewer section types, more
whitespace. Every piece of this that reads as designed will read that way because
something was left out, not because something was added.