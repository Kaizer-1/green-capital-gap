/* fig12_continuity.js — two instruments, two populations, never pooled.
 *
 * The panels share no axis and are drawn with their own scales, which is the
 * point: the taxonomies and amount conventions are not compatible, and a shared
 * axis would invite a comparison the data cannot support.
 */

import {
  colour,
  el,
  hideTooltip,
  layoutFor,
  renderError,
  scaleLinear,
  showTooltip,
  svg,
  tooltipRows,
} from "./theme.js";

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
  const height = compact ? 600 : 300;
  const gap = compact ? 48 : 48;
  const paneW = compact ? L.width : (L.width - gap) / 2;

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;
  const root = svg(container, {
    width: L.width,
    height,
    compact,
    label:
      "A later window in one large emerging market reproduces the same scarcity. " +
      spec.panels
        .map(
          (p) =>
            `${p.label}: ${p.marks.map((m) => `${m.year} ${m.green} green deals`).join(", ")}`
        )
        .join("; "),
  });

  spec.panels.forEach((panel, pi) => {
    const left = compact ? 0 : pi * (paneW + gap);
    const top = compact ? pi * (height / 2) + 56 : 56;
    const bottom = compact ? top + height / 2 - 110 : height - 54;
    const plot = { left: left + 30, right: left + paneW - 6, top, bottom };

    root.appendChild(
      el(
        "text",
        { class: "mark-label", x: left, y: top - 34, "text-anchor": "start", fill: "var(--ink)" },
        panel.label
      )
    );
    root.appendChild(
      el("text", { class: "mark-note", x: left, y: top - 12, "text-anchor": "start" }, panel.sublabel)
    );

    const max = Math.max(...panel.marks.map((m) => m.green), 1);
    const y = scaleLinear([0, max * 1.2], [bottom, top]);
    const band = ((plot.right - plot.left) / panel.marks.length) * 0.62;
    const x = scaleLinear(
      [panel.marks[0].year - 0.5, panel.marks.at(-1).year + 0.5],
      [plot.left, plot.right]
    );

    for (const t of [0, Math.round(max / 2), max]) {
      root.appendChild(
        el("line", { class: "gridline", x1: plot.left, x2: plot.right, y1: y(t), y2: y(t) })
      );
      root.appendChild(
        el(
          "text",
          { class: "tick-label", x: left, y: y(t) + 4, "text-anchor": "start" },
          String(t)
        )
      );
    }

    panel.marks.forEach((m, i) => {
      const h = Math.max(0, bottom - y(m.green));
      const rect = el("rect", {
        x: x(m.year) - band / 2,
        y: y(m.green),
        width: band,
        height: h,
        fill: colour(panel.colour_role),
      });
      root.appendChild(rect);
      if (animate) {
        rect.setAttribute("height", 0);
        rect.setAttribute("y", bottom);
        window.setTimeout(() => {
          rect.style.transition = "y 500ms cubic-bezier(0.4, 0, 0.2, 1), height 500ms cubic-bezier(0.4, 0, 0.2, 1)";
          rect.setAttribute("y", y(m.green));
          rect.setAttribute("height", h);
        }, pi * 120 + i * 50);
      }

      const surface = el("rect", {
        x: x(m.year) - band / 2,
        y: top,
        width: band,
        height: Math.max(0, bottom - top),
        fill: "transparent",
        style: "touch-action: none",
      });
      const show = (e) =>
        showTooltip(
          tooltipRows(`${panel.label} · ${m.year}`, [
            ["Green deals", String(m.green), panel.colour_role],
            ["All deals", m.deals.toLocaleString(), null],
          ]),
          e.clientX,
          e.clientY
        );
      surface.addEventListener("pointermove", show);
      surface.addEventListener("pointerdown", show);
      surface.addEventListener("pointerleave", hideTooltip);
      root.appendChild(surface);
    });

    const years = panel.marks.map((m) => m.year);
    for (const yr of [years[0], years.at(-1)]) {
      root.appendChild(
        el(
          "text",
          {
            class: "tick-label",
            x: x(yr),
            y: bottom + 18,
            "text-anchor": yr === years[0] ? "start" : "end",
          },
          String(yr)
        )
      );
    }
  });

  root.appendChild(
    el(
      "text",
      { class: "mark-note", x: 0, y: height - 6, "text-anchor": "start" },
      "The panels share no axis."
    )
  );

  return root;
}
