/* fig04_ladder.js — sector representation against capital intensity.
 *
 * The one genuinely sequential argument on the page, so the one place a pinned
 * graphic earns its keep. Four steps:
 *
 *   1. Observed      twenty-three sectors at their emerging-market
 *                    representation. Cleantech is already coloured but not yet
 *                    remarkable.
 *   2. The pattern   the x axis becomes capital intensity, the dots migrate,
 *                    and the fit draws left to right. The relationship appears.
 *   3. The prediction hollow markers drop in at each sector's predicted
 *                    position, and a residual segment grows from predicted to
 *                    observed, coloured by sign.
 *   4. The exception  everything else falls to 30%. Cleantech's residual stays
 *                    at full strength and its label and interval arrive.
 *
 * Step 4 is the payload. The whole sequence exists to deliver it, so the fade is
 * slow enough to read as emphasis rather than as the chart breaking, and the
 * label arrives after the fade has settled rather than with it.
 *
 * The y position never changes: representation is the quantity throughout, and
 * only the x axis re-scales. A dot that moved on both axes would read as a new
 * dot rather than the same sector seen another way.
 */

import {
  colour,
  el,
  hideTooltip,
  layoutFor,
  renderError,
  showTooltip,
  svg,
  tooltipRows,
} from "./theme.js";

const FADE = 0.3;
/* Residuals draw at full strength. They were at 0.75, which put a 1.6px teal
   line at 2.5:1 — and the residual is the finding here, not a supporting mark.
   They stay subordinate to the dots by width, as everything else on this page
   that needs a hierarchy does. */
const RESIDUAL = 1;
const MIGRATE_MS = 900;
const DRAW_MS = 900;
const FADE_MS = 700;

function logScale(domain, range) {
  const [d0, d1] = domain.map((v) => Math.log10(Math.max(v, 1e-9)));
  const [r0, r1] = range;
  const fn = (v) =>
    r0 + ((Math.log10(Math.max(v, 1e-9)) - d0) / (d1 - d0 || 1)) * (r1 - r0);
  fn.domain = domain;
  return fn;
}

/**
 * Build the graphic and return a handle.
 *
 * `setStep(n, { animate })` moves to a step; `setView(id)` switches between the
 * ladder and the scatter once the sequence has run.
 */
export function createLadder(
  container,
  spec,
  { animate = true, height, findings = {} } = {},
) {
  const L = layoutFor(container);
  const compact = L.width < 500;
  const marks = [...spec.marks].sort((a, b) => a.observed - b.observed);

  const H = height ?? (compact ? 340 : 420);
  const plot = { left: 46, right: L.width - 16, top: 26, bottom: H - 52 };

  container.innerHTML = "";
  container.style.aspectRatio = `${L.width} / ${H}`;

  const root = svg(container, {
    width: L.width,
    height: H,
    compact,
    label:
      "Capital intensity drives the pattern, and green beats its prediction. " +
      `Across ${spec.fit.n_sectors} sectors the elasticity of emerging-market ` +
      `representation with respect to capital intensity is ${spec.fit.slope}. ` +
      `Cleantech sits ${spec.focus.residual_ratio} above its predicted position. ` +
      marks
        .map(
          (m) =>
            `${m.sector}: observed ${m.observed}, predicted ${m.predicted}`,
        )
        .join("; "),
  });

  // y is representation, in every step. Only x changes.
  const obs = marks.map((m) => m.observed);
  const pred = marks.map((m) => m.predicted);
  const y = logScale(
    [Math.min(...obs, ...pred) * 0.7, Math.max(...obs, ...pred) * 1.4],
    [plot.bottom, plot.top],
  );

  // Two x scales: the ladder's rank position, and capital intensity.
  const rankX = (i) =>
    plot.left + ((i + 0.5) / marks.length) * (plot.right - plot.left);
  const capitals = marks.map((m) => m.capital_intensity_usd);
  const capX = logScale(
    [Math.min(...capitals) * 0.8, Math.max(...capitals) * 1.25],
    [plot.left, plot.right],
  );

  // ---- static furniture ------------------------------------------------
  const grid = el("g", { "aria-hidden": "true" });
  root.appendChild(grid);
  for (const t of [0.1, 0.25, 1, 2.5]) {
    if (y(t) < plot.top || y(t) > plot.bottom) continue;
    grid.appendChild(
      el("line", {
        class: "gridline",
        x1: plot.left,
        x2: plot.right,
        y1: y(t),
        y2: y(t),
        "stroke-dasharray": t === 1 ? "3 3" : null,
      }),
    );
    grid.appendChild(
      el(
        "text",
        { class: "tick-label", x: 0, y: y(t) + 4, "text-anchor": "start" },
        `${t}×`,
      ),
    );
  }
  grid.appendChild(
    el(
      "text",
      { class: "axis-label", x: 0, y: 12, "text-anchor": "start" },
      "EM representation vs AE",
    ),
  );
  const xLabel = el(
    "text",
    { class: "axis-label", x: 0, y: H - 10, "text-anchor": "start" },
    "Sectors, ordered by representation",
  );
  root.appendChild(xLabel);

  const xTicks = el("g", { "aria-hidden": "true" });
  root.appendChild(xTicks);

  function drawCapitalTicks(show) {
    xTicks.replaceChildren();
    if (!show) return;
    for (const t of [1e6, 3e6, 7e6]) {
      if (capX(t) < plot.left || capX(t) > plot.right) continue;
      xTicks.appendChild(
        el(
          "text",
          {
            class: "tick-label",
            x: capX(t),
            y: plot.bottom + 20,
            "text-anchor": "middle",
          },
          `$${(t / 1e6).toFixed(0)}m`,
        ),
      );
    }
  }

  // ---- the fit line, drawn in step 2 -----------------------------------
  const fitLine = el("path", {
    d: `M ${capX(spec.fit.line[0].x)} ${y(spec.fit.line[0].y)} L ${capX(spec.fit.line[1].x)} ${y(spec.fit.line[1].y)}`,
    fill: "none",
    stroke: colour("alert"),
    "stroke-width": 1.4,
    opacity: 0,
  });
  root.appendChild(fitLine);

  // ---- residual segments and predicted markers, step 3 -----------------
  const residuals = marks.map((m) =>
    el("line", {
      x1: capX(m.capital_intensity_usd),
      x2: capX(m.capital_intensity_usd),
      y1: y(m.predicted),
      y2: y(m.predicted),
      stroke: colour(m.residual_sign === "over" ? "em" : "ae"),
      "stroke-width": 1.6,
      opacity: 0,
    }),
  );
  residuals.forEach((r) => root.appendChild(r));

  const predicted = marks.map((m) =>
    el("circle", {
      cx: capX(m.capital_intensity_usd),
      cy: y(m.predicted),
      r: 3.4,
      fill: "none",
      stroke: colour("ink-muted"),
      "stroke-width": 1.1,
      opacity: 0,
    }),
  );
  predicted.forEach((p) => root.appendChild(p));

  // ---- the sector dots -------------------------------------------------
  const dots = marks.map((m, i) =>
    el("circle", {
      cx: rankX(i),
      cy: y(m.observed),
      r: m.is_focus ? 6 : 4.2,
      fill: colour(m.is_focus ? "cleantech" : "nongreen"),
      opacity: 0,
    }),
  );
  dots.forEach((d) => root.appendChild(d));

  // ---- the focus label, step 4 -----------------------------------------
  const focusMark = marks.find((m) => m.is_focus);
  const focusGroup = el("g", { opacity: 0 });
  const fx = capX(focusMark.capital_intensity_usd);
  const fy = y(focusMark.observed);

  // The name stays on the mark. The numbers go to the bottom-left corner, which
  // is empty in every step, with a leader to the mark: anchored beside the dot
  // they ran back across the whole scatter.
  focusGroup.appendChild(
    el(
      "text",
      {
        class: "mark-label",
        x: fx - 10,
        y: fy - 12,
        "text-anchor": "end",
        fill: colour("cleantech"),
      },
      "cleantech",
    ),
  );

  const blockY = plot.bottom - 60;
  focusGroup.appendChild(
    el(
      "text",
      {
        class: "mark-label",
        x: plot.left,
        y: blockY,
        "text-anchor": "start",
        fill: colour("cleantech"),
      },
      `${spec.focus.residual_display} above its prediction`,
    ),
  );
  focusGroup.appendChild(
    el(
      "text",
      {
        class: "mark-note",
        x: plot.left,
        y: blockY + 21,
        "text-anchor": "start",
      },
      `${spec.focus.residual_ci_display}, which includes 1\u00d7`,
    ),
  );
  root.appendChild(focusGroup);

  // ---- hover, on every sector -------------------------------------------
  marks.forEach((m, i) => {
    const hit = el("circle", {
      cx: rankX(i),
      cy: y(m.observed),
      r: 12,
      fill: "transparent",
      style: "touch-action: none",
    });
    const show = (e) =>
      showTooltip(
        tooltipRows(m.sector, [
          ["Observed", `${m.observed}×`, m.is_focus ? "cleantech" : "nongreen"],
          ["Predicted", `${m.predicted}×`, "ink-muted"],
          [
            "Capital intensity",
            `$${(m.capital_intensity_usd / 1e6).toFixed(1)}m`,
            null,
          ],
          ["Emerging-market deals", String(m.em_deals), null],
        ]),
        e.clientX,
        e.clientY,
      );
    hit.addEventListener("pointermove", show);
    hit.addEventListener("pointerdown", show);
    hit.addEventListener("pointerleave", hideTooltip);
    root.appendChild(hit);
    m._hit = hit;
  });

  // ---- step machinery ---------------------------------------------------
  let current = 0;
  let view = "scatter";

  const ease = "cubic-bezier(0.4, 0, 0.2, 1)";

  function positionDots(toCapital, ms) {
    marks.forEach((m, i) => {
      const cx = toCapital ? capX(m.capital_intensity_usd) : rankX(i);
      dots[i].style.transition = ms ? `cx ${ms}ms ${ease}` : "";
      dots[i].setAttribute("cx", cx);
      m._hit.setAttribute("cx", cx);
    });
    xLabel.textContent = toCapital
      ? "Capital intensity: median AE deal size, log"
      : "Sectors, ordered by representation";
    drawCapitalTicks(toCapital);
  }

  function setStep(step, { animate: withMotion = true } = {}) {
    const ms = withMotion ? 1 : 0;
    current = step;

    // 1 — observed
    dots.forEach((d, i) => {
      d.style.transition = ms ? `opacity 400ms ${ease}` : "";
      d.style.transitionDelay = ms && step === 1 ? `${i * 40}ms` : "0ms";
      d.setAttribute("opacity", step >= 1 ? 1 : 0);
    });

    // 2 — the pattern: migrate, then draw the fit
    positionDots(step >= 2, ms && step >= 2 ? MIGRATE_MS : 0);
    if (step >= 2) {
      const length = fitLine.getTotalLength?.() ?? 0;
      if (ms && length) {
        fitLine.style.strokeDasharray = `${length}`;
        fitLine.style.strokeDashoffset = `${length}`;
        fitLine.getBoundingClientRect();
        fitLine.style.transition = `stroke-dashoffset ${DRAW_MS}ms linear, opacity 200ms linear`;
        fitLine.style.transitionDelay = `${MIGRATE_MS}ms`;
        fitLine.style.strokeDashoffset = "0";
      } else {
        fitLine.style.strokeDasharray = "";
        fitLine.style.transition = "";
      }
      fitLine.setAttribute("opacity", 1);
    } else {
      fitLine.setAttribute("opacity", 0);
    }

    // 3 — the prediction
    marks.forEach((m, i) => {
      const on = step >= 3;
      predicted[i].style.transition = ms ? `opacity 400ms ${ease}` : "";
      predicted[i].style.transitionDelay =
        ms && step === 3 ? `${i * 30}ms` : "0ms";
      predicted[i].setAttribute("opacity", on ? 0.9 : 0);

      residuals[i].style.transition = ms
        ? `y2 400ms ${ease}, opacity 300ms ${ease}`
        : "";
      residuals[i].style.transitionDelay =
        ms && step === 3 ? `${i * 30 + 120}ms` : "0ms";
      residuals[i].setAttribute("y2", on ? y(m.observed) : y(m.predicted));
      residuals[i].setAttribute("opacity", on ? RESIDUAL : 0);
    });

    // 4 — the exception. The payload. Everything that is not cleantech falls
    // away; cleantech's residual holds at full strength and its label arrives
    // AFTER the fade has settled, so the beat lands rather than competing with
    // the movement.
    const dim = step >= 4;
    // Step 4's recession is the argument, not a styling choice: everything but
    // cleantech's residual drops to 30% so the one mark that matters is the one
    // left at full strength. Those marks are therefore declared faint, and the
    // contrast gate exempts them by name. Nothing is lost by it — step 3 shows
    // the same marks at full strength, the stacked and reduced-motion paths
    // render all four states, and the data table below the figure carries every
    // value in full-contrast text.
    const soften = (node, on) => node.classList.toggle("mark-soft", on);
    marks.forEach((m, i) => {
      if (m.is_focus) return;
      const fade = ms ? `opacity ${FADE_MS}ms ${ease}` : "";
      dots[i].style.transition = fade;
      dots[i].style.transitionDelay = "0ms";
      dots[i].setAttribute("opacity", dim ? FADE : step >= 1 ? 1 : 0);
      soften(dots[i], dim);
      predicted[i].style.transition = fade;
      predicted[i].setAttribute(
        "opacity",
        dim ? FADE * 0.6 : step >= 3 ? 0.9 : 0,
      );
      soften(predicted[i], dim || step >= 3);
      residuals[i].style.transition = fade;
      residuals[i].setAttribute(
        "opacity",
        dim ? FADE * 0.5 : step >= 3 ? RESIDUAL : 0,
      );
      soften(residuals[i], dim || step >= 3);
    });
    fitLine.style.opacity = dim ? FADE : step >= 2 ? 1 : 0;
    soften(fitLine, dim);

    const focusIndex = marks.findIndex((m) => m.is_focus);
    if (focusIndex >= 0) {
      residuals[focusIndex].setAttribute("stroke-width", dim ? 2.6 : 1.6);
      dots[focusIndex].setAttribute("r", dim ? 7 : 6);
    }
    focusGroup.style.transition = ms ? `opacity ${FADE_MS}ms ${ease}` : "";
    focusGroup.style.transitionDelay = ms && dim ? `${FADE_MS}ms` : "0ms";
    focusGroup.setAttribute("opacity", dim ? 1 : 0);
  }

  function setView(id) {
    view = id;
    positionDots(id === "scatter", MIGRATE_MS);
    // The residual furniture only makes sense against capital intensity.
    const on = id === "scatter" && current >= 3;
    predicted.forEach((p) => p.setAttribute("opacity", on ? 0.9 : 0));
    residuals.forEach((r) => r.setAttribute("opacity", on ? RESIDUAL : 0));
    fitLine.setAttribute("opacity", id === "scatter" && current >= 2 ? 1 : 0);
  }

  setStep(animate ? 0 : 4, { animate: false });

  return {
    root,
    setStep,
    setView,
    get step() {
      return current;
    },
    get view() {
      return view;
    },
  };
}

/** Entry point used by main.js for the non-scrolly path (stacked states). */
export function render(container, spec, findings, options = {}) {
  try {
    return createLadder(container, spec, options);
  } catch (cause) {
    renderError(container, cause.message);
    throw cause;
  }
}
