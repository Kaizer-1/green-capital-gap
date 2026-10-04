/* fig02_double_gap.js — green share of recorded deals by bloc.
 *
 * A dot-and-interval chart, not bars: the quantity is a rate with a confidence
 * interval, and bars imply a count. Each bloc is labelled directly, so colour
 * carries nothing the text does not.
 *
 * Two layouts, chosen by container width rather than by scaling one design
 * down. A 760-unit canvas squeezed into a 342px phone renders its labels at
 * about five pixels, which is not a smaller chart but an unreadable one.
 *
 * Static at this step. No animation, no interaction.
 */

import {
  colour,
  el,
  labelColour,
  renderError,
  scaleLinear,
  strokeColour,
  svg,
  ticks,
} from "./theme.js";

/** Below this container width, the compact layout is used. */
const COMPACT_BELOW = 560;

const WIDE = {
  // The shared canvas width. At 760 in a 736px column this figure rendered at
  // 0.97 and its 13px labels landed at 12.6px, under the desktop floor, while
  // every other figure sat at 1:1.
  width: 736,
  row: 62,
  padTop: 20,
  padBottom: 56,
  // Measured from the longest label at the rendered size rather than guessed.
  // The guess was 128, and "Advanced economies" was clipped to "vanced economies".
  labelGap: 12,
  gutter: 104, // reserved for the bracket, outside the plot
  labelAbove: false,
};

const COMPACT = {
  // Sized so the SVG scales at about 1:1 in a 390px viewport, which makes the
  // declared font size the rendered font size. At 360 units the chart scaled to
  // 0.95 and its 13px labels landed at 12.3px, under the 15px mobile floor.
  width: 340,
  // Taller rows than the wide layout: the bloc name sits above its mark rather
  // than beside it, so the row has to carry two lines of type plus the mark.
  row: 78,
  padTop: 16,
  // Room for the tick row AND the axis label beneath it. At 48 the two
  // overlapped once the compact type went up to 16px.
  padBottom: 64,
  labelGap: 0,
  gutter: 0,
  // The bloc name sits above its row, so the plot keeps the full width.
  labelAbove: true,
};

export function render(container, spec, findings) {
  try {
    draw(container, spec, findings);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}

/**
 * Approximate rendered width of a label, in SVG units.
 *
 * The SVG is not in the document when the margin has to be decided, so this
 * estimates from character count at the known font size. Generous by design:
 * over-reserving costs a few pixels of plot, under-reserving clips a label.
 */
function labelWidth(text, size = 13) {
  return text.length * size * 0.55;
}

function draw(container, spec, findings) {
  const marks = spec.marks;
  const compact = (container.clientWidth || 0) < COMPACT_BELOW;
  const L = compact ? COMPACT : WIDE;

  // Left margin sized to the content, and the labels are LEFT-aligned within
  // it. Right-aligning them to the axis made the figure's leftmost ink a ragged
  // staircase — three labels, three different starting x — so the figure had no
  // left edge to share with the prose. Every categorical figure follows this.
  const left = L.labelAbove
    ? // Enough for half of the first tick label, which is centred on the axis
      // origin; at 8 the "0%" was sliced down the middle by the canvas edge.
      18
    : Math.ceil(
        Math.max(
          ...marks.map((m) =>
            Math.max(
              labelWidth(m.label),
              labelWidth(`n = ${m.n.toLocaleString()}`),
            ),
          ),
        ),
      ) + L.labelGap;

  const height = L.padTop + marks.length * L.row + L.padBottom;
  const plotLeft = left;
  const plotRight = L.width - L.gutter - (L.labelAbove ? 22 : 16);

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;

  const root = svg(container, {
    compact,
    width: L.width,
    height,
    label:
      "In the record, an emerging-market company is half as likely to be green. " +
      marks
        .map((m) => `${m.label}: ${m.rate}% of ${m.n.toLocaleString()} deals`)
        .join("; "),
  });

  const [d0, d1] = spec.axis.x.domain;
  const x = scaleLinear(spec.axis.x.domain, [plotLeft, plotRight]);
  const rowY = (i) =>
    L.padTop + i * L.row + (L.labelAbove ? L.row * 0.68 : L.row / 2);
  const plotBottom = L.padTop + marks.length * L.row;

  // --- gridlines and the x axis, behind everything ----------------------
  const grid = el("g", { "aria-hidden": "true" });
  for (const t of ticks(spec.axis.x.domain, compact ? 4 : 9)) {
    grid.appendChild(
      el("line", {
        class: "gridline",
        x1: x(t),
        x2: x(t),
        y1: L.padTop,
        y2: plotBottom,
      }),
    );
    grid.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: x(t),
          y: plotBottom + 20,
          "text-anchor": "middle",
        },
        `${t}%`,
      ),
    );
  }
  grid.appendChild(
    el(
      "text",
      {
        class: "axis-label",
        x: L.labelAbove ? 0 : plotLeft,
        y: height - 10,
        "text-anchor": "start",
      },
      spec.axis.x.label,
    ),
  );
  root.appendChild(grid);

  // --- one row per bloc --------------------------------------------------
  marks.forEach((m, i) => {
    const y = rowY(i);
    // Three resolutions of one role. The dot and its interval are thin marks
    // the reader has to trace, so they take the stroke tone; the value label is
    // text, so it takes the label tone; nothing here is a large filled area, so
    // the raw palette colour is unused. --nongreen at 2.44:1 is the role that
    // makes the difference visible.
    const fill = strokeColour(m.colour_role);
    const labelInk = labelColour(m.colour_role);
    const g = el("g");

    if (L.labelAbove) {
      g.appendChild(
        el(
          "text",
          // x = 0, not plotLeft: the row label is the figure's leftmost ink and
          // has to start where the prose starts. plotLeft exists only to keep
          // the first tick label inside the canvas.
          { class: "tick-label", x: 0, y: y - 46, "text-anchor": "start" },
          `${m.label}  ·  n = ${m.n.toLocaleString()}`,
        ),
      );
    } else {
      g.appendChild(
        el(
          "text",
          { class: "tick-label", x: 0, y: y - 3, "text-anchor": "start" },
          m.label,
        ),
      );
      g.appendChild(
        el(
          "text",
          { class: "mark-note", x: 0, y: y + 14, "text-anchor": "start" },
          `n = ${m.n.toLocaleString()}`,
        ),
      );
    }

    // Whether an interval is drawn is the export's decision, not this module's,
    // so the web and print variants of this figure cannot diverge. The
    // least-developed row has no green deals: its Wilson interval runs to 22.8%
    // on thirteen deals, and drawing it would imply a precision that does not
    // exist. It carries a note instead.
    const [lo, hi] = m.ci;
    if (m.draw_interval) {
      const loClamped = Math.max(lo, d0);
      const hiClamped = Math.min(hi, d1);
      if (hiClamped > loClamped) {
        g.appendChild(
          el("line", {
            x1: x(loClamped),
            x2: x(hiClamped),
            y1: y,
            y2: y,
            stroke: fill,
            // The interval reads at full strength and stays subordinate to the
            // point estimate by WIDTH, not by opacity. At 0.55 the teal
            // whisker fell to 2.3:1 — and on a figure whose argument is the
            // overlap of two intervals, the interval is not decoration.
            "stroke-width": 1.5,
            "stroke-linecap": "round",
          }),
        );
      }
      if (hi > d1) {
        const tip = x(d1);
        g.appendChild(
          el("path", {
            d: `M ${tip - 7} ${y - 4} L ${tip} ${y} L ${tip - 7} ${y + 4}`,
            fill: "none",
            stroke: fill,
            "stroke-width": 1.5,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          }),
        );
      }
    }

    g.appendChild(el("circle", { cx: x(m.rate), cy: y, r: 5.5, fill }));

    // The value label. Nudged away from the row above where the dot sits at the
    // axis, so it does not land level with the previous row's n.
    // The value sits above the dot in both layouts. Beside it collides with the
    // interval, and on the emerging-market row with the hollow upper-bound
    // marker; the compact layout buys the room by using taller rows instead.
    g.appendChild(
      el(
        "text",
        {
          class: "mark-label",
          x: x(m.rate),
          y: y - (L.labelAbove ? 16 : 13),
          "text-anchor": m.rate <= d0 + (d1 - d0) * 0.04 ? "start" : "middle",
          fill: labelInk,
        },
        `${m.rate.toFixed(2)}%`,
      ),
    );

    if (m.note) {
      g.appendChild(
        el(
          "text",
          {
            class: "mark-note",
            x: x(m.rate) + 14,
            y: y + 4,
            "text-anchor": "start",
            "font-style": "italic",
          },
          m.note,
        ),
      );
    }
    root.appendChild(g);
  });

  // --- the bracket -------------------------------------------------------
  // Marks the two rows the headline compares. It lives OUTSIDE the plot, in the
  // reserved gutter, so it never crosses a gridline — and it is drawn only
  // against the two rows it names, broken across the rows between them, so it
  // cannot be read as a four-way comparison.
  const from = marks.findIndex((m) => m.bloc === spec.bracket.from);
  const to = marks.findIndex((m) => m.bloc === spec.bracket.to);
  if (!compact && from >= 0 && to >= 0) {
    const y1 = rowY(from);
    const y2 = rowY(to);
    const bx = plotRight + 22;
    const stroke = colour("ink-muted");
    const arm = 7;
    const bracket = el("g", { "aria-hidden": "true" });
    // A plain bracket: one spine, one arm per compared row. An earlier version
    // broke the spine to avoid implying the rows between were included, and the
    // result read as two stray marks rather than as a bracket. The label names
    // the two blocs, which is what disambiguates it.
    bracket.appendChild(
      el("line", { x1: bx, x2: bx, y1, y2, stroke, "stroke-width": 1 }),
    );
    for (const yy of [y1, y2]) {
      bracket.appendChild(
        el("line", {
          x1: bx - arm,
          x2: bx,
          y1: yy,
          y2: yy,
          stroke,
          "stroke-width": 1,
        }),
      );
    }
    bracket.appendChild(
      el(
        "text",
        {
          class: "mark-note",
          x: bx + 8,
          y: (y1 + y2) / 2 + 4,
          "text-anchor": "start",
        },
        spec.bracket.label,
      ),
    );
    root.appendChild(bracket);
  }

  // --- the upper bound ---------------------------------------------------
  // A hollow marker on the emerging-market row: the most generous reading of
  // the unattributable deals, which still leaves the gap. Drawn last so it sits
  // above the filled dot it sits beside.
  const emIndex = marks.findIndex((m) => m.bloc === spec.upper_bound.bloc);
  if (emIndex >= 0) {
    root.appendChild(
      el("circle", {
        cx: x(spec.upper_bound.rate),
        cy: rowY(emIndex),
        r: 5.5,
        fill: colour("ink") === "#141413" ? "#ffffff" : "none",
        stroke: colour("em"),
        "stroke-width": 1.6,
      }),
    );
  }

  // No data table is built here. It is injected into the page at build time, so
  // it exists with scripts off too; the stylesheet decides whether it is shown.

  return { findings };
}
