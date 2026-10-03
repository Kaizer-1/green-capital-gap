/* theme.js — the chart house style.
 *
 * The palette mirrors src/gcg/viz/theme.py and tokens.css. A chart module never
 * writes a colour: it writes a semantic role, which series.json also uses, and
 * this resolves it. That is what keeps one palette in one place.
 */

/** colour_role, as emitted by export_series.py, to a CSS custom property. */
const ROLE_VAR = {
  em: "--em",
  ae: "--ae",
  china: "--china",
  ldc: "--ldc",
  green: "--green",
  nongreen: "--nongreen",
  cleantech: "--cleantech",
  muted: "--nongreen",
  alert: "--alert",
  ink: "--ink",
  "ink-muted": "--ink-muted",
  rule: "--rule",
};

/* Text drawn in a series colour, and lines drawn in one, resolve through their
 * own maps. See tokens.css for why: CLAUDE.md fixes the palette and requires
 * direct labelling rather than a legend, which makes three of those hues text
 * at under 4.5:1. The override is per-role and only where one is needed, so a
 * role with no entry falls through to the canonical colour. */
const LABEL_VAR = {
  ae: "--ae-label",
  ldc: "--ldc-label",
  nongreen: "--nongreen-label",
  muted: "--nongreen-label",
};

const STROKE_VAR = {
  nongreen: "--nongreen-stroke",
  muted: "--nongreen-stroke",
};

let computed = null;

/** Resolve a colour_role to its hex, read once from the document's tokens. */
export function colour(role) {
  if (!computed) computed = getComputedStyle(document.documentElement);
  const name = ROLE_VAR[role];
  if (!name) {
    throw new Error(
      `unknown colour_role "${role}"; add it to ROLE_VAR or fix the export`,
    );
  }
  return computed.getPropertyValue(name).trim();
}

/** The same series colour, dark enough to be read as text. */
export function labelColour(role) {
  if (!computed) computed = getComputedStyle(document.documentElement);
  const name = LABEL_VAR[role];
  return name ? computed.getPropertyValue(name).trim() : colour(role);
}

/** The same series colour, dark enough to be read as a line. */
export function strokeColour(role) {
  if (!computed) computed = getComputedStyle(document.documentElement);
  const name = STROKE_VAR[role];
  return name ? computed.getPropertyValue(name).trim() : colour(role);
}

/**
 * The ink for a label reversed out INSIDE a filled shape.
 *
 * Contrast is symmetric, so white on --nongreen fails at exactly the 2.44:1
 * that --nongreen on white does. Reversing out in --canvas is right on the
 * darker roles and wrong on the lighter ones, so the choice is made per fill
 * rather than once: whichever of --canvas and --ink the segment contrasts with
 * more.
 */
export function contrastInk(role) {
  if (!computed) computed = getComputedStyle(document.documentElement);
  const lum = (hex) => {
    const n = parseInt(hex.replace("#", ""), 16);
    const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const L = lum(colour(role));
  const onWhite = 1.05 / (L + 0.05);
  const onInk =
    (L + 0.05) / (lum(computed.getPropertyValue("--ink").trim()) + 0.05);
  return onWhite >= onInk ? "var(--canvas)" : "var(--ink)";
}

/** Figure margins. One set, so every chart's plot area starts at the same x. */
export const MARGIN = { top: 16, right: 24, bottom: 44, left: 128 };

/**
 * Create the SVG for a figure container.
 *
 * Uses a viewBox and no width/height, so the chart scales with its container
 * and the aspect ratio reserved in CSS holds. Nothing re-measures on resize.
 */
export function svg(container, { width, height, label, compact = false }) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  node.setAttribute("viewBox", `0 0 ${width} ${height}`);
  node.setAttribute("preserveAspectRatio", "xMinYMin meet");
  // Marks the compact layout so the stylesheet can raise the type: at mobile the
  // chart is nearly 1:1, so declared size is rendered size.
  if (compact) node.classList.add("compact");
  node.setAttribute("role", "img");
  node.setAttribute("aria-label", label);
  container.appendChild(node);
  return node;
}

/** Create an SVG element with attributes, because doing it inline is noise. */
export function el(name, attrs = {}, text = null) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  if (text !== null) node.textContent = text;
  return node;
}

/** A linear scale. Positions marks; derives nothing. */
export function scaleLinear(domain, range) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  const fn = (v) => r0 + ((v - d0) / span) * (r1 - r0);
  fn.domain = domain;
  fn.range = range;
  return fn;
}

/**
 * Tick values across a domain, at a round step.
 *
 * Deliberately simple: the domains here are small and known, and a general
 * tick algorithm would be more code than the charts need.
 */
export function ticks(domain, count = 5) {
  const [d0, d1] = domain;
  const raw = (d1 - d0) / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step =
    [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw;
  const out = [];
  for (let v = Math.ceil(d0 / step) * step; v <= d1 + 1e-9; v += step) {
    out.push(Math.round(v * 1e6) / 1e6);
  }
  return out;
}

/** Render a figure's error state. Loud, and never a plausible stand-in. */
export function renderError(container, message) {
  container.innerHTML = "";
  const box = document.createElement("div");
  box.className = "figure__error";
  box.setAttribute("role", "alert");
  box.textContent = `This figure could not be rendered: ${message}`;
  container.appendChild(box);
}

/**
 * Build the visually-hidden data table that is the screen-reader path and the
 * no-JS fallback. Every chart gets one; it is not optional.
 */
export function dataTable(columns, rows, caption) {
  // The table goes INSIDE a hidden wrapper rather than carrying the class
  // itself. A <table> under auto layout expands to fit its content and ignores
  // `width: 1px`, so a table with the class on it kept a 610px box and pushed
  // the document's scrollWidth past the viewport at 390px.
  const wrapper = document.createElement("div");
  wrapper.className = "visually-hidden";
  const table = document.createElement("table");
  const cap = document.createElement("caption");
  cap.textContent = caption;
  table.appendChild(cap);

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const c of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = c;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const cell of row) {
      const td = document.createElement("td");
      td.textContent = cell === null || cell === undefined ? "" : String(cell);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

// ---------------------------------------------------------------------------
// Layout shared by every chart.
//
// One set of paddings, so the plot area of every figure begins and ends at the
// same place and the figures line up with each other down the page as well as
// with the prose.

export const WIDE = { width: 736, padTop: 22, padRight: 18, padBottom: 56 };
export const COMPACT = { width: 340, padTop: 18, padRight: 12, padBottom: 62 };

/** Below this container width a chart re-lays out rather than scaling down. */
export const COMPACT_BELOW = 560;

/** The layout a container's width calls for. */
export function layoutFor(container) {
  return (container.clientWidth || 0) < COMPACT_BELOW ? COMPACT : WIDE;
}

/**
 * Approximate rendered width of a label, in SVG units.
 *
 * The SVG is not in the document when margins have to be decided, so this
 * estimates from character count. Generous by design: over-reserving costs a
 * few units of plot, under-reserving clips a label.
 */
export function labelWidth(text, size = 13) {
  return text.length * size * 0.55;
}

/**
 * Draw gridlines, ticks and the axis label for a chart with a numeric y axis.
 *
 * Returns nothing; appends to `root`. Gridlines go on first so every mark sits
 * above them.
 */
export function axes(
  root,
  { x, y, plot, xTicks, yTicks, xFormat, yFormat, yLabel, xLabel },
) {
  const g = el("g", { "aria-hidden": "true" });
  for (const t of yTicks) {
    g.appendChild(
      el("line", {
        class: "gridline",
        x1: plot.left,
        x2: plot.right,
        y1: y(t),
        y2: y(t),
      }),
    );
    g.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: plot.left - 8,
          y: y(t) + 4,
          "text-anchor": "end",
        },
        yFormat(t),
      ),
    );
  }
  // The first and last ticks anchor inward. Centred, the leftmost one extends
  // past the axis and lands on the y tick beside it — "0%" and "2000" sat on
  // top of each other at 390px — and the rightmost one overhangs the canvas.
  const firstTick = xTicks[0];
  const lastTick = xTicks[xTicks.length - 1];
  for (const t of xTicks) {
    const anchor =
      t === firstTick ? "start" : t === lastTick ? "end" : "middle";
    g.appendChild(
      el(
        "text",
        {
          class: "tick-label",
          x: x(t),
          y: plot.bottom + 20,
          "text-anchor": anchor,
        },
        xFormat(t),
      ),
    );
  }
  if (yLabel) {
    // Clear of the topmost tick, which sits at plot.top: at -10 the label and
    // the highest y value overlapped.
    g.appendChild(
      el(
        "text",
        { class: "axis-label", x: 0, y: plot.top - 16, "text-anchor": "start" },
        yLabel,
      ),
    );
  }
  if (xLabel) {
    g.appendChild(
      el(
        "text",
        {
          class: "axis-label",
          x: 0,
          y: plot.bottom + 44,
          "text-anchor": "start",
        },
        xLabel,
      ),
    );
  }
  root.appendChild(g);
  return g;
}

/** An SVG path `d` through points, in order. */
export function linePath(points, x, y, fx, fy) {
  return points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${x(fx(p)).toFixed(2)} ${y(fy(p)).toFixed(2)}`,
    )
    .join(" ");
}

// ---------------------------------------------------------------------------
// The tooltip.
//
// One node for the whole page, moved and refilled rather than created per
// chart. It must feel instant, so it has no entrance animation: a tooltip that
// fades in is a tooltip that lags the cursor.

let tip = null;

function tooltipNode() {
  if (tip) return tip;
  tip = document.createElement("div");
  tip.className = "tooltip";
  tip.setAttribute("role", "status");
  tip.hidden = true;
  document.body.appendChild(tip);
  // Escape dismisses, as it should for anything transient.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideTooltip();
  });
  return tip;
}

/**
 * Show the tooltip near a client-space point.
 *
 * Flips at the viewport edges rather than overflowing, which is the behaviour
 * the capture checks at the right-hand edge.
 */
export function showTooltip(html, clientX, clientY) {
  const node = tooltipNode();
  node.innerHTML = html;
  node.hidden = false;

  const pad = 12;
  const box = node.getBoundingClientRect();
  let left = clientX + pad;
  let top = clientY + pad;
  if (left + box.width > window.innerWidth - 8)
    left = clientX - box.width - pad;
  if (top + box.height > window.innerHeight - 8)
    top = clientY - box.height - pad;
  node.style.left = `${Math.max(8, left)}px`;
  node.style.top = `${Math.max(8, top)}px`;
}

export function hideTooltip() {
  if (tip) tip.hidden = true;
}

/**
 * Wire a hover readout over a time series: a vertical rule at the nearest year
 * and a tooltip of that year's values.
 *
 * Pointer events, not mouse events, so a tap works the same as a hover. A chart
 * that is dead on a phone is a chart half the audience never sees working.
 */
export function timeSeriesHover(root, { plot, x, years, rowsFor }) {
  const rule = el("line", {
    class: "hover-rule",
    y1: plot.top,
    y2: plot.bottom,
    stroke: "var(--rule)",
    "stroke-width": 1,
    opacity: 0,
  });
  root.appendChild(rule);

  const surface = el("rect", {
    x: plot.left,
    y: plot.top,
    width: Math.max(0, plot.right - plot.left),
    height: Math.max(0, plot.bottom - plot.top),
    fill: "transparent",
    style: "touch-action: none",
  });

  const nearest = (clientX) => {
    const box = root.getBoundingClientRect();
    const scale = box.width / root.viewBox.baseVal.width;
    const local = (clientX - box.left) / scale;
    return years.reduce((best, yr) =>
      Math.abs(x(yr) - local) < Math.abs(x(best) - local) ? yr : best,
    );
  };

  const move = (event) => {
    const year = nearest(event.clientX);
    rule.setAttribute("x1", x(year));
    rule.setAttribute("x2", x(year));
    rule.setAttribute("opacity", 1);
    showTooltip(rowsFor(year), event.clientX, event.clientY);
  };

  surface.addEventListener("pointermove", move);
  surface.addEventListener("pointerdown", move);
  surface.addEventListener("pointerleave", () => {
    rule.setAttribute("opacity", 0);
    hideTooltip();
  });
  root.appendChild(surface);
}

/** Tooltip markup: a title and label/value rows. */
export function tooltipRows(title, rows) {
  const body = rows
    .map(
      ([label, value, role]) =>
        `<div class="tooltip__row">` +
        `<span class="tooltip__swatch"${role ? ` style="background:${colour(role)}"` : ""}></span>` +
        `<span class="tooltip__label">${label}</span>` +
        `<span class="tooltip__value">${value}</span></div>`,
    )
    .join("");
  return `<div class="tooltip__title">${title}</div>${body}`;
}
