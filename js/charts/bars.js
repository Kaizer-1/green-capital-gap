/* bars.js — the shared horizontal bar chart.
 *
 * Figures 9 and 11 are the same chart with different data: a labelled category
 * per row, one bar, an optional threshold line. Row labels are left-aligned and
 * the axis starts after the longest of them, so the figure's leftmost ink
 * shares the prose's left edge.
 */

import {
  colour,
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
import { fadeIn, growBar } from "../reveal.js";

export function renderBars(container, opts, { animate = true } = {}) {
  try {
    draw(container, opts, animate);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}

function draw(container, opts, animate) {
  const {
    marks, // [{ label, sublabel, value, display, colour_role, dim }]
    axis,
    label,
    threshold, // { value, label, colour_role }
    tooltip,
    rowHeight = 56,
  } = opts;

  const L = layoutFor(container);
  const compact = L.width < 500;
  const row = compact ? rowHeight + 42 : rowHeight;

  const left = compact
    ? 0
    : Math.ceil(
        Math.max(
          ...marks.map((m) =>
            Math.max(labelWidth(m.label, 13), labelWidth(m.sublabel ?? "", 13)),
          ),
        ),
      ) + 14;

  const height = L.padTop + marks.length * row + L.padBottom;
  const plot = {
    left,
    right: L.width - L.padRight - 44,
    top: L.padTop,
    bottom: L.padTop + marks.length * row,
  };

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;
  const root = svg(container, { width: L.width, height, compact, label });

  const x = scaleLinear(axis.x.domain, [plot.left, plot.right]);
  const rowY = (i) => plot.top + i * row + row * (compact ? 0.66 : 0.5);

  // Gridlines and ticks, behind everything.
  const grid = el("g", { "aria-hidden": "true" });
  const tickValues = ticks(axis.x.domain, compact ? 3 : 5);
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
        `${t}${axis.x.unit ?? ""}`,
      ),
    );
  }
  grid.appendChild(
    el(
      "text",
      { class: "axis-label", x: 0, y: height - 10, "text-anchor": "start" },
      axis.x.label,
    ),
  );
  root.appendChild(grid);

  // The threshold is drawn BEFORE the bars start growing. The whole argument of
  // the power wall is that nothing reaches the line, and watching five bars
  // fail to reach a line that is already there says it better than a caption.
  if (threshold) {
    const tx = x(threshold.value);
    const stroke = colour(threshold.colour_role ?? "alert");
    root.appendChild(
      el("line", {
        x1: tx,
        x2: tx,
        y1: plot.top - 6,
        y2: plot.bottom + 4,
        stroke,
        "stroke-width": 1.4,
      }),
    );
    root.appendChild(
      el(
        "text",
        {
          class: "mark-note",
          x: tx + 6,
          y: plot.top + 4,
          "text-anchor": "start",
          fill: labelColour(threshold.colour_role ?? "alert"),
        },
        threshold.label,
      ),
    );
  }

  const barHeight = compact ? 16 : 18;

  marks.forEach((m, i) => {
    const y = rowY(i);
    const g = el("g");
    const fill = colour(m.colour_role);
    // The bar is a filled area and the label is text, so they resolve through
    // different maps: --nongreen is 2.44:1 against white, fine as a 20px-tall
    // bar and unreadable as 13px type. See theme.js.
    const labelInk = labelColour(m.colour_role);

    g.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: 0,
          y: compact ? y - 42 : y - 4,
          "text-anchor": "start",
        },
        m.label,
      ),
    );
    if (m.sublabel) {
      g.appendChild(
        el(
          "text",
          {
            class: "mark-note",
            x: 0,
            y: compact ? y - 20 : y + 13,
            "text-anchor": "start",
          },
          m.sublabel,
        ),
      );
    }

    const w = Math.max(0, x(m.value) - x(axis.x.domain[0]));
    const rect = el("rect", {
      x: x(axis.x.domain[0]),
      y: y - barHeight / 2,
      width: w,
      height: barHeight,
      fill,
      opacity: m.dim ? 0.45 : 1,
    });
    g.appendChild(rect);
    if (animate) growBar(rect, w, { index: i });

    const value = el(
      "text",
      {
        class: "mark-label",
        x: x(axis.x.domain[0]) + w + 8,
        y: y + 4,
        "text-anchor": "start",
        fill: labelInk,
      },
      m.display ?? String(m.value),
    );
    g.appendChild(value);
    if (animate) fadeIn(value, { delay: 300 + i * 50 });

    if (tooltip) {
      const surface = el("rect", {
        x: plot.left,
        y: y - row / 2,
        width: Math.max(0, plot.right - plot.left + 44),
        height: row,
        fill: "transparent",
        style: "touch-action: none",
      });
      const show = (e) =>
        showTooltip(tooltipRows(m.label, tooltip(m)), e.clientX, e.clientY);
      surface.addEventListener("pointermove", show);
      surface.addEventListener("pointerdown", show);
      surface.addEventListener("pointerleave", hideTooltip);
      g.appendChild(surface);
    }

    root.appendChild(g);
  });

  return root;
}
