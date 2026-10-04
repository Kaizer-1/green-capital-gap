/* fig10_depth_need.js — green funding intensity against market depth, and the
 * need regressor that cannot be tested.
 *
 * Two panels, and they are deliberately NOT symmetric.
 *
 * Panel (a) is a scatter with a hover readout: there is a relationship, and a
 * reader should be able to interrogate it country by country.
 *
 * Panel (b) is inert. No hover, no tooltip, no focus target. The point of that
 * panel is that there is nothing to explore — all but two of the panel's
 * countries record an electricity deficit of exactly zero, so the regressor is
 * a dummy for one country. Giving it a readout "for consistency" would quietly
 * contradict its own caption: an interface that invites interrogation implies
 * there is something there to find.
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
import { fadeIn } from "../reveal.js";

export function render(container, spec, findings, options = {}) {
  try {
    draw(container, spec, options.animate !== false);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}

function logScale(domain, range) {
  const [d0, d1] = domain.map((v) => Math.log10(Math.max(v, 1e-6)));
  const [r0, r1] = range;
  const fn = (v) =>
    r0 + ((Math.log10(Math.max(v, 1e-6)) - d0) / (d1 - d0 || 1)) * (r1 - r0);
  fn.domain = domain;
  return fn;
}

function draw(container, spec, animate) {
  const L = layoutFor(container);
  const compact = L.width < 500;
  const marks = spec.marks;

  const height = compact ? 640 : 320;
  const gap = compact ? 44 : 34;
  // Panel (a) takes the larger share: it is the one with something in it.
  const paneW = compact ? L.width : (L.width - gap) * 0.62;
  const paneBW = compact ? L.width : L.width - gap - paneW;

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${height}`;
  const root = svg(container, {
    width: L.width,
    height,
    compact,
    label:
      "Capital tracks market depth; whether it tracks need cannot be measured here. " +
      `Spearman rho ${spec.depth.rho} across ${spec.depth.n} countries. ` +
      `${spec.need.non_trivial_values} of ${spec.depth.n} countries record any electricity deficit.`,
  });

  // ---- panel (a): depth -------------------------------------------------
  const aTop = 44;
  const aBottom = compact ? height * 0.44 : height - 54;
  // Ticks are left-aligned at x = 0 and the plot starts after them, so the
  // figure's leftmost ink is at the container edge like every other figure.
  const a = { left: 48, right: paneW - 10, top: aTop, bottom: aBottom };

  const gdp = marks.map((m) => m.gdp_per_capita).filter(Boolean);
  const cap = marks.map((m) => Math.max(m.green_usd_per_capita, 0.001));
  const ax = logScale(
    [Math.min(...gdp) * 0.85, Math.max(...gdp) * 1.15],
    [a.left, a.right],
  );
  const ay = logScale(
    [Math.min(...cap) * 0.7, Math.max(...cap) * 1.4],
    [a.bottom, a.top],
  );

  root.appendChild(
    el(
      "text",
      {
        class: "mark-label",
        x: 0,
        y: 12,
        "text-anchor": "start",
        fill: "var(--ink)",
      },
      `(a)  Depth: rho ${spec.depth.rho} across ${spec.depth.n} countries`,
    ),
  );

  for (const t of [1000, 10000, 100000]) {
    root.appendChild(
      el("line", {
        class: "gridline",
        x1: ax(t),
        x2: ax(t),
        y1: a.top,
        y2: a.bottom,
      }),
    );
    root.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: ax(t),
          y: a.bottom + 18,
          "text-anchor": "middle",
        },
        t >= 1000 ? `$${t / 1000}k` : `$${t}`,
      ),
    );
  }
  // The y axis. A scatter without one cannot be read: the reader can see that
  // the cloud rises but not by how much.
  const yTicks = [0.01, 0.1, 1, 10].filter(
    (t) => ay(t) > a.top + 6 && ay(t) < a.bottom - 18,
  );
  for (const t of yTicks) {
    root.appendChild(
      el("line", {
        class: "gridline",
        x1: a.left,
        x2: a.right,
        y1: ay(t),
        y2: ay(t),
      }),
    );
    root.appendChild(
      el(
        "text",
        { class: "tick-label", x: 0, y: ay(t) + 4, "text-anchor": "start" },
        `$${t}`,
      ),
    );
  }
  root.appendChild(
    el(
      "text",
      { class: "axis-label", x: 0, y: a.top - 2, "text-anchor": "start" },
      "Green funding per capita, log scale",
    ),
  );
  root.appendChild(
    el(
      "text",
      { class: "axis-label", x: 0, y: a.bottom + 40, "text-anchor": "start" },
      "GDP per capita, log scale",
    ),
  );

  marks.forEach((m, i) => {
    const dot = el("circle", {
      cx: ax(m.gdp_per_capita),
      cy: ay(Math.max(m.green_usd_per_capita, 0.001)),
      r: 4,
      fill: colour(m.colour_role),
      opacity: 0.85,
    });
    root.appendChild(dot);
    if (animate) fadeIn(dot, { delay: 40 + i * 14, duration: 400 });

    const surface = el("circle", {
      cx: ax(m.gdp_per_capita),
      cy: ay(Math.max(m.green_usd_per_capita, 0.001)),
      r: 11,
      fill: "transparent",
      style: "touch-action: none",
    });
    const show = (e) =>
      showTooltip(
        tooltipRows(m.country, [
          ["Green funding per capita", `$${m.green_usd_per_capita}`, "em"],
          ["GDP per capita", `$${m.gdp_per_capita.toLocaleString()}`, null],
          ["Green deals", m.green_deals.toLocaleString(), null],
        ]),
        e.clientX,
        e.clientY,
      );
    surface.addEventListener("pointermove", show);
    surface.addEventListener("pointerdown", show);
    surface.addEventListener("pointerleave", hideTooltip);
    root.appendChild(surface);
  });

  // ---- panel (b): the degenerate regressor, inert -----------------------
  const bLeft = compact ? 0 : paneW + gap;
  const bTop = compact ? height * 0.7 : aTop;
  const b = {
    left: bLeft + 10,
    right: bLeft + paneBW - 10,
    top: bTop,
    bottom: compact ? height - 54 : a.bottom,
  };

  root.appendChild(
    el(
      "text",
      {
        class: "mark-label",
        x: bLeft,
        y: bTop - 16,
        "text-anchor": "start",
        fill: "var(--ink)",
      },
      "(b)  Need: nothing to explore",
    ),
  );

  const deficits = marks.map((m) => m.electricity_deficit_pct ?? 0);
  const bx = scaleLinear(
    [0, Math.max(...deficits, 1) * 1.1],
    [b.left, b.right],
  );
  const lane = (b.bottom - b.top) / 2 + b.top;

  root.appendChild(
    el("line", {
      class: "gridline",
      x1: b.left,
      x2: b.right,
      y1: lane,
      y2: lane,
    }),
  );
  // Every country, on one axis. The pile at zero IS the figure.
  deficits.forEach((d, i) => {
    root.appendChild(
      el("circle", {
        cx: bx(d),
        cy: lane + ((i % 5) - 2) * 3.4,
        r: 3.2,
        fill: colour(d > 0.05 ? "alert" : "nongreen"),
        // Declared faint. These dots overplot each other — the pile at zero is
        // the figure — and alpha is what makes the density readable. The
        // contrast gate exempts this class by name so the exemption is a
        // decision in the chart, not a threshold tuned until it passed.
        class: d > 0.05 ? null : "mark-soft",
        opacity: d > 0.05 ? 0.95 : 0.55,
      }),
    );
  });
  for (const t of [0, Math.round(Math.max(...deficits))]) {
    root.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: bx(t),
          y: b.bottom + 18,
          "text-anchor": t === 0 ? "start" : "end",
        },
        `${t}%`,
      ),
    );
  }
  root.appendChild(
    el(
      "text",
      {
        class: "axis-label",
        x: bLeft,
        y: b.bottom + 40,
        "text-anchor": "start",
      },
      "Electricity-access deficit",
    ),
  );
  root.appendChild(
    el(
      "text",
      { class: "mark-note", x: bLeft, y: lane - 46, "text-anchor": "start" },
      `${spec.depth.n - spec.need.non_trivial_values} of ${spec.depth.n} sit at exactly zero`,
    ),
  );
  root.appendChild(
    el(
      "text",
      { class: "mark-note", x: bLeft, y: lane - 24, "text-anchor": "start" },
      `all variance is ${spec.need.variance_carriers.join(" and ")}`,
    ),
  );

  // No hover surface for panel (b), by design. See the module comment.
  return root;
}
