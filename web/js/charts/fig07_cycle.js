/* fig07_cycle.js — green deals and green dollars, by year.
 *
 * The toggle is the one place on this page where animation carries an argument
 * rather than decorating one. Dollars peak a year BEFORE deals do, and that is
 * visible in the transition: the tall bar slides one year left while the rest
 * of the distribution reshapes around it. Two static panels cannot show it, and
 * neither can a fade-out/fade-in, which destroys the correspondence between a
 * bar and itself.
 *
 * So the bars MORPH IN PLACE. The same rect elements persist across a toggle
 * and animate their y and height; nothing is removed and nothing is created.
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
  ticks,
  tooltipRows,
} from "./theme.js";
import { fadeIn, reducedMotion } from "../reveal.js";

const MORPH_MS = 600;

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

  const height = compact ? 330 : 300;
  const plot = {
    left: 52,
    right: L.width - L.padRight,
    top: L.padTop + 16,
    bottom: height - L.padBottom,
  };

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;

  const root = svg(container, {
    width: L.width,
    height,
    compact,
    label:
      "Green deal sizes fell far faster than non-green within the same stages. " +
      marks
        .map((m) => `${m.year}: ${m.deals} deals, ${m.usd_bn} billion dollars`)
        .join("; "),
  });

  const x = scaleLinear(spec.axis.x.domain, [plot.left, plot.right]);
  const bandWidth = ((plot.right - plot.left) / marks.length) * 0.68;

  // One y scale per view. Switching view switches scale, which is what lets the
  // same bars re-proportion rather than merely rescale.
  const scales = Object.fromEntries(
    spec.views.map((v) => {
      const max = Math.max(...marks.map((m) => m[v.field] ?? 0));
      return [v.id, scaleLinear([0, max * 1.12], [plot.bottom, plot.top])];
    })
  );

  let view = spec.views[0];

  // --- axis furniture, rebuilt on toggle --------------------------------
  const grid = el("g", { "aria-hidden": "true" });
  root.appendChild(grid);

  function drawAxis() {
    grid.replaceChildren();
    const y = scales[view.id];
    for (const t of ticks(y.domain, 4)) {
      grid.appendChild(
        el("line", { class: "gridline", x1: plot.left, x2: plot.right, y1: y(t), y2: y(t) })
      );
      grid.appendChild(
        el(
          "text",
          { class: "tick-label", x: plot.left - 8, y: y(t) + 4, "text-anchor": "end" },
          view.id === "dollars" ? `$${t}bn` : String(t)
        )
      );
    }
    const years = marks.map((m) => m.year);
    const shown = compact ? years.filter((yr) => yr % 4 === 0) : years.filter((yr) => yr % 2 === 0);
    for (const yr of shown) {
      const anchor = yr === shown[0] ? "start" : yr === shown.at(-1) ? "end" : "middle";
      grid.appendChild(
        el(
          "text",
          { class: "tick-label", x: x(yr), y: plot.bottom + 20, "text-anchor": anchor },
          String(yr)
        )
      );
    }
    grid.appendChild(
      el(
        "text",
        { class: "axis-label", x: 0, y: plot.top - 16, "text-anchor": "start" },
        view.id === "dollars"
          ? "Disclosed green funding, constant 2015 USD"
          : "Green deals recorded"
      )
    );
  }

  // --- the bars: created once, reshaped on every toggle ------------------
  const bars = marks.map((m) => {
    const rect = el("rect", {
      x: x(m.year) - bandWidth / 2,
      width: bandWidth,
      y: plot.bottom,
      height: 0,
      fill: colour(spec.views[0].colour_role),
    });
    root.appendChild(rect);
    return { rect, mark: m };
  });

  // The peak marker moves with the view. It is the finding: the dollar peak is
  // one year left of the deal peak.
  const peakLabel = el(
    "text",
    { class: "mark-label", "text-anchor": "middle", fill: colour("green") },
    ""
  );
  root.appendChild(peakLabel);

  function layout({ transition }) {
    const y = scales[view.id];
    const ms = transition && !reducedMotion() ? MORPH_MS : 0;
    for (const { rect, mark } of bars) {
      const value = mark[view.field] ?? 0;
      const top = y(value);
      rect.style.transition = ms
        ? `y ${ms}ms cubic-bezier(0.4, 0, 0.2, 1), height ${ms}ms cubic-bezier(0.4, 0, 0.2, 1)`
        : "";
      rect.setAttribute("y", top);
      rect.setAttribute("height", Math.max(0, plot.bottom - top));
    }
    const peak = marks.reduce((a, b) => ((b[view.field] ?? 0) > (a[view.field] ?? 0) ? b : a));
    peakLabel.style.transition = ms ? `opacity ${ms / 2}ms linear` : "";
    peakLabel.setAttribute("x", x(peak.year));
    peakLabel.setAttribute("y", y(peak[view.field]) - 10);
    peakLabel.textContent =
      view.id === "dollars" ? `peak dollars ${peak.year}` : `peak deals ${peak.year}`;
    drawAxis();
  }

  layout({ transition: false });
  if (animate) {
    // The entrance grows the bars from the axis; the toggle morphs them.
    window.setTimeout(() => layout({ transition: true }), 40);
    fadeIn(peakLabel, { delay: 500 });
  } else {
    layout({ transition: false });
  }

  // --- the toggle -------------------------------------------------------
  const controls = document.createElement("div");
  controls.className = "toggle";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "Show deal counts or disclosed dollars");
  for (const v of spec.views) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = v.label;
    button.setAttribute("aria-pressed", String(v.id === view.id));
    button.addEventListener("click", () => {
      if (v.id === view.id) return;
      view = v;
      for (const b of controls.querySelectorAll("button")) {
        b.setAttribute("aria-pressed", String(b.textContent === v.label));
      }
      layout({ transition: true });
    });
    controls.appendChild(button);
  }
  container.appendChild(controls);

  // --- hover ------------------------------------------------------------
  for (const { rect, mark } of bars) {
    const surface = el("rect", {
      x: x(mark.year) - bandWidth / 2,
      y: plot.top,
      width: bandWidth,
      height: Math.max(0, plot.bottom - plot.top),
      fill: "transparent",
      style: "touch-action: none",
    });
    const show = (e) =>
      showTooltip(
        tooltipRows(String(mark.year), [
          ["Green deals", mark.deals.toLocaleString(), "green"],
          ["Disclosed funding", `$${mark.usd_bn}bn`, "green"],
          ["With a disclosed amount", mark.disclosed.toLocaleString(), null],
        ]),
        e.clientX,
        e.clientY
      );
    surface.addEventListener("pointermove", show);
    surface.addEventListener("pointerdown", show);
    surface.addEventListener("pointerleave", hideTooltip);
    root.appendChild(surface);
    void rect;
  }

  return root;
}
