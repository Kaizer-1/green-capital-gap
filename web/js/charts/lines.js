/* lines.js — the shared two-series time-series chart.
 *
 * Figures 1, 3 and 5 are the same chart with different data: two series over
 * 2000–2012, directly labelled at their terminus, with a hover readout. They
 * are built from one function rather than three near-copies, because three
 * near-copies is how two of them come to disagree about a margin.
 *
 * Direct labelling at the terminus, never a legend: the label sits beside the
 * line it names, so colour carries nothing the text does not.
 */

import {
  axes,
  colour,
  el,
  labelColour,
  labelWidth,
  layoutFor,
  linePath,
  renderError,
  scaleLinear,
  strokeColour,
  svg,
  ticks,
  timeSeriesHover,
  tooltipRows,
} from "./theme.js";
import { drawLine, fadeIn } from "../reveal.js";

/**
 * @param {object} opts
 * @param {Array}  opts.series  [{ id, label, colour_role, dash, points:[{year,value,...}] }]
 * @param {object} opts.axis    the series.json axis block
 * @param {Function} opts.tooltip  (year) => [[label, value, colour_role], ...]
 * @param {Array}  opts.annotations  [{ year, text, colour_role }]
 * @param {Function} opts.pointNote  optional (point, seriesId) => string|null
 */
export function renderLines(container, opts, { animate = true } = {}) {
  try {
    draw(container, opts, animate);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}

function draw(container, opts, animate) {
  const {
    series,
    axis,
    label,
    tooltip,
    annotations = [],
    pointNote,
    // The x field is "year" for the window charts and "month" for the censoring
    // figure; the chart is otherwise identical, so it takes the key rather than
    // being copied.
    xKey = "year",
    xFormat = (t) => String(Math.round(t)),
    // A horizontal datum — an index base at 100, say — drawn behind the series.
    reference,
    // A shaded span on the x axis, for an event window.
    band,
  } = opts;
  const L = layoutFor(container);
  const compact = L.width < 500;

  // The terminus labels live in a right-hand gutter sized to the longest of
  // them, so the x axis can stop at the last year with data. Putting them
  // inside the plot is what made the PDF's charts run an axis to a year that
  // had nothing under it.
  const gutter = compact
    ? 0
    : Math.ceil(Math.max(...series.map((s) => labelWidth(s.label, 13)))) + 14;

  const yValues = series.flatMap((s) => s.points.map((p) => p.value));
  const yMax = axis.y?.domain?.[1] ?? Math.ceil(Math.max(...yValues) * 1.18);
  const yMin = axis.y?.domain?.[0] ?? 0;

  // Sized from the widest y tick label, the same way the right gutter is sized
  // from the widest terminus label. A constant worked at desktop and failed at
  // 390: the labels are right-anchored to the axis, so "25%" reaches 2.5px
  // further left than "5%" and spilled past the page's left edge — the one
  // alignment this layout is built on.
  const yUnit = axis.y?.unit ?? "";
  const yTickValues = ticks([yMin, yMax], 5);
  // At the stated size, not a nominal one: the compact layout raises every
  // string inside the SVG to 16px, so measuring at 13 under-reserved the margin
  // and the widest label still spilled.
  const tickPx = compact ? 16 : 13;
  const widestTick = Math.max(
    ...yTickValues.map((t) => labelWidth(`${t}${yUnit}`, tickPx, "tick-label"))
  );
  const leftPad = Math.max(42, Math.ceil(widestTick) + 8);
  // Room above the plot for the y-axis label.
  const height = compact ? 330 : 300;
  const plot = {
    left: leftPad,
    right: L.width - L.padRight - gutter,
    top: L.padTop + 16,
    bottom: height - L.padBottom,
  };

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;

  const root = svg(container, { width: L.width, height, label, compact });

  const x = scaleLinear(axis.x.domain, [plot.left, plot.right]);
  const y = scaleLinear([yMin, yMax], [plot.bottom, plot.top]);
  const fmt = (v) => `${v}${yUnit}`;

  axes(root, {
    x,
    y,
    plot,
    xTicks: ticks(axis.x.domain, compact ? 4 : 7).filter(
      (t) => t >= axis.x.domain[0] && t <= axis.x.domain[1],
    ),
    yTicks: yTickValues,
    xFormat,
    yFormat: fmt,
    yLabel: axis.y?.label,
  });

  // --- a reference datum and an event band, behind the series ------------
  if (band) {
    root.appendChild(
      el("rect", {
        x: x(band[0]),
        y: plot.top,
        width: Math.max(0, x(band[1]) - x(band[0])),
        height: Math.max(0, plot.bottom - plot.top),
        fill: "var(--rule)",
        opacity: 0.45,
      }),
    );
  }
  if (reference !== undefined) {
    root.appendChild(
      el("line", {
        x1: plot.left,
        x2: plot.right,
        y1: y(reference),
        y2: y(reference),
        stroke: "var(--ink-muted)",
        "stroke-width": 1,
        "stroke-dasharray": "3 3",
      }),
    );
  }

  // Terminus labels, placed before the series so collisions can be resolved
  // first: two series ending at similar values put their labels on top of each
  // other, which is what "Advanced economies, green" and "Advanced economies,
  // non-green" did.
  const termini = series.map((s) => {
    const last = s.points[s.points.length - 1];
    return { id: s.id, y: y(last.value), x: x(last[xKey]) };
  });
  const sorted = [...termini].sort((a, b) => a.y - b.y);
  for (let i = 1; i < sorted.length; i += 1) {
    // The compact layout sets 16px type, so a 16px gap is exactly touching.
    const gapNeeded = compact ? 22 : 16;
    if (sorted[i].y - sorted[i - 1].y < gapNeeded) {
      sorted[i].y = sorted[i - 1].y + gapNeeded;
    }
  }
  const labelY = new Map(termini.map((t) => [t.id, t.y]));

  // --- the series -------------------------------------------------------
  series.forEach((s, i) => {
    // The line and its label resolve separately: the subordinate series needs a
    // darker tone to be traceable as a 1.8px line, and a darker one still to be
    // read as text. See theme.js.
    const stroke = strokeColour(s.colour_role);
    const labelInk = labelColour(s.colour_role);
    const path = el("path", {
      d: linePath(
        s.points,
        x,
        y,
        (p) => p[xKey],
        (p) => p.value,
      ),
      fill: "none",
      stroke,
      "stroke-width": 1.8,
      "stroke-linejoin": "round",
      "stroke-linecap": "round",
      "stroke-dasharray": s.dash ?? null,
    });
    root.appendChild(path);
    if (animate) drawLine(path, 700);

    // A point marker wherever the series carries a note — a cell below the
    // pre-registered minimum, say — so the caveat is on the mark, not only in
    // the caption.
    if (pointNote) {
      for (const p of s.points) {
        const note = pointNote(p, s.id);
        if (!note) continue;
        root.appendChild(
          el("circle", {
            cx: x(p[xKey]),
            cy: y(p.value),
            r: 2.6,
            fill: stroke,
            opacity: 0.9,
          }),
        );
      }
    }

    // Terminus label, or an in-plot label at mobile where there is no gutter.
    const last = s.points[s.points.length - 1];
    const text = el(
      "text",
      {
        class: "mark-label",
        x: compact ? x(last[xKey]) - 4 : x(last[xKey]) + 10,
        y: labelY.get(s.id) + (compact ? -10 : 4),
        "text-anchor": compact ? "end" : "start",
        fill: labelInk,
      },
      s.label,
    );
    root.appendChild(text);
    if (animate) fadeIn(text, { delay: 700 + i * 60 });
  });

  // --- annotations ------------------------------------------------------
  for (const a of annotations) {
    if (compact && a.text.length > 40) continue; // no room; the caption carries it
    const note = el(
      "text",
      {
        class: "mark-note",
        x: x(a.year),
        y: plot.top + 14,
        "text-anchor":
          x(a.year) > (plot.left + plot.right) / 2 ? "end" : "start",
      },
      a.text,
    );
    root.appendChild(note);
    if (animate) fadeIn(note, { delay: 900 });
    root.appendChild(
      el("line", {
        x1: x(a.year),
        x2: x(a.year),
        y1: plot.top + 20,
        y2: plot.bottom,
        stroke: "var(--rule)",
        "stroke-width": 1,
        "stroke-dasharray": "2 3",
      }),
    );
  }

  // --- hover ------------------------------------------------------------
  const years = series[0].points.map((p) => p[xKey]);
  timeSeriesHover(root, {
    plot,
    x,
    years,
    rowsFor: (value) => tooltipRows(xFormat(value), tooltip(value)),
  });

  return root;
}
