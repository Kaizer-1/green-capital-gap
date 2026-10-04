/* fig06_subdomain.js — how much of each bloc's green is resolved to a sub-domain.
 *
 * A stacked bar, because the two parts are shares of one whole and the question
 * is how that whole divides. The unresolved segment is the finding: the record
 * cannot say what KIND of green an emerging-market company is.
 *
 * Row labels are left-aligned and the axis starts after the longest of them, so
 * the figure's leftmost ink shares the prose's left edge.
 */

import {
  colour,
  contrastInk,
  el,
  hideTooltip,
  labelColour,
  labelWidth,
  layoutFor,
  renderError,
  scaleLinear,
  showTooltip,
  svg,
  ticks,
  tooltipRows,
} from "./theme.js";
import { growBar, fadeIn } from "../reveal.js";

const ROW = 64;

export function render(container, spec, findings, options = {}) {
  try {
    draw(container, spec, options.animate !== false);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}

function draw(container, spec, animate) {
  const L = layoutFor(container);
  const compact = L.width < 500;
  const marks = spec.marks;

  const left = compact
    ? 0
    : Math.ceil(Math.max(...marks.map((m) => labelWidth(m.label, 13)))) + 14;

  const rowHeight = compact ? ROW + 22 : ROW;
  // The legend sits ABOVE the plot. Below, it landed on top of the axis label.
  const legendHeight = 26;
  const height =
    L.padTop + legendHeight + marks.length * rowHeight + L.padBottom;
  const plot = {
    left,
    right: L.width - L.padRight,
    top: L.padTop + legendHeight,
    bottom: L.padTop + legendHeight + marks.length * rowHeight,
  };

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;

  const root = svg(container, {
    width: L.width,
    height,
    compact,
    label:
      "The taxonomy cannot say what kind of green an emerging-market company is. " +
      marks
        .map(
          (m) =>
            `${m.label}: ${m.unspecified_pct}% unresolved of ${m.n} green deals`,
        )
        .join("; "),
  });

  const x = scaleLinear(spec.axis.x.domain, [plot.left, plot.right]);
  const rowY = (i) =>
    plot.top + i * rowHeight + rowHeight * (compact ? 0.62 : 0.5);

  // Gridlines behind everything.
  const grid = el("g", { "aria-hidden": "true" });
  // First and last ticks anchor inward: centred, the leftmost one extends past
  // the axis and, in the compact layout where the axis starts at zero, past the
  // canvas edge.
  const tickValues = ticks(spec.axis.x.domain, 4);
  for (const t of tickValues) {
    grid.appendChild(
      el("line", {
        class: "gridline",
        x1: x(t),
        x2: x(t),
        y1: plot.top,
        y2: plot.bottom,
      }),
    );
    const anchor =
      t === tickValues[0]
        ? "start"
        : t === tickValues.at(-1)
          ? "end"
          : "middle";
    grid.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: x(t),
          y: plot.bottom + 20,
          "text-anchor": anchor,
        },
        `${t}%`,
      ),
    );
  }
  grid.appendChild(
    el(
      "text",
      { class: "axis-label", x: 0, y: height - 10, "text-anchor": "start" },
      spec.axis.x.label,
    ),
  );
  root.appendChild(grid);

  const barHeight = 18;

  marks.forEach((m, i) => {
    const y = rowY(i);
    const g = el("g");

    g.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: 0,
          y: compact ? y - 26 : y - 4,
          "text-anchor": "start",
        },
        compact ? `${m.label}  ·  n = ${m.n.toLocaleString()}` : m.label,
      ),
    );
    if (!compact) {
      g.appendChild(
        el(
          "text",
          { class: "mark-note", x: 0, y: y + 13, "text-anchor": "start" },
          `n = ${m.n.toLocaleString()}`,
        ),
      );
    }

    // Two segments, in order: resolved, then the unresolved remainder.
    let cursor = 0;
    spec.segments.forEach((seg, si) => {
      const value = m[seg.id];
      const w = x(value) - x(0);
      const rect = el("rect", {
        x: x(cursor),
        y: y - barHeight / 2,
        width: w,
        height: barHeight,
        fill: colour(seg.colour_role),
      });
      rect.dataset.label = seg.label;
      rect.dataset.value = `${value}%`;
      g.appendChild(rect);

      if (animate) growBar(rect, w, { index: i * spec.segments.length + si });

      // The value is written inside its segment where it fits, and outside where
      // it does not — unless there is no room for it anywhere, which happens at
      // mobile where two narrow segments' labels would land on each other. The
      // tooltip and the data table carry the number either way.
      // Inside the segment where it fits. Outside only in the wide layout: at
      // mobile the two segments are close enough that an outside label for one
      // lands on the inside label of the other, so a segment too narrow to
      // carry its own number simply goes unlabelled. The tooltip and the data
      // table carry it either way.
      const inside = w > 54;
      if (!inside && compact) {
        cursor += value;
        return;
      }
      const label = el(
        "text",
        {
          class: "mark-label",
          x: inside ? x(cursor) + 8 : x(cursor + value) + 8,
          y: y + 4,
          "text-anchor": "start",
          // Inside the bar the label sits on the segment's own fill, so its
          // ink is chosen against that fill. Outside it sits on white, where
          // the raw series colour is not readable as text.
          fill: inside
            ? contrastInk(seg.colour_role)
            : labelColour(seg.colour_role),
        },
        `${value}%`,
      );
      g.appendChild(label);
      if (animate) fadeIn(label, { delay: 320 + i * 50 });

      cursor += value;
    });

    // Hover and tap both work; a chart dead on a phone is a chart half the
    // audience never sees working.
    const rows = () =>
      tooltipRows(
        `${m.label} · n = ${m.n.toLocaleString()} green deals`,
        spec.segments.map((seg) => [
          seg.label,
          `${m[seg.id]}%`,
          seg.colour_role,
        ]),
      );
    const surface = el("rect", {
      x: plot.left,
      y: y - rowHeight / 2,
      width: Math.max(0, plot.right - plot.left),
      height: rowHeight,
      fill: "transparent",
      style: "touch-action: none",
    });
    const show = (e) => showTooltip(rows(), e.clientX, e.clientY);
    surface.addEventListener("pointermove", show);
    surface.addEventListener("pointerdown", show);
    surface.addEventListener("pointerleave", hideTooltip);
    g.appendChild(surface);

    root.appendChild(g);
  });

  // Two swatches and two words, above the plot. Not a key in a box.
  const legend = el("g");
  let lx = 0;
  spec.segments.forEach((seg) => {
    legend.appendChild(
      el("rect", {
        x: lx,
        y: L.padTop,
        width: 9,
        height: 9,
        fill: colour(seg.colour_role),
      }),
    );
    legend.appendChild(
      el(
        "text",
        {
          class: "mark-note",
          x: lx + 14,
          y: L.padTop + 9,
          "text-anchor": "start",
        },
        seg.label,
      ),
    );
    lx += 14 + labelWidth(seg.label, 13) + 22;
  });
  root.appendChild(legend);

  return root;
}
