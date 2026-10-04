/* main.js — entry point.
 *
 * The page's statistics and its masthead are injected at build time by
 * gcg.web.inject, so they are in the HTML before this runs and survive with
 * scripts off. What is left for the browser is the part that genuinely needs
 * one: drawing the charts, checking the injected values still agree with
 * findings.json, and the progress rail.
 */

import { load, verifyKeys, figure } from "./data.js";
import { onReveal } from "./reveal.js";
import { initScrolly } from "./scrolly.js";
import * as fig01 from "./charts/fig01_coverage.js";
import * as fig02 from "./charts/fig02_double_gap.js";
import * as fig03 from "./charts/fig03_rate_by_year.js";
import * as fig05 from "./charts/fig05_share_crossover.js";
import * as fig06 from "./charts/fig06_subdomain.js";
import * as fig07 from "./charts/fig07_cycle.js";
import * as fig08 from "./charts/fig08_crisis.js";
import * as fig09 from "./charts/fig09_instruments.js";
import * as fig10 from "./charts/fig10_depth_need.js";
import * as fig11 from "./charts/fig11_power_wall.js";
import * as fig12 from "./charts/fig12_continuity.js";
import * as figM1 from "./charts/figM1_censoring.js";

/* Each figure's container id, the series.json key it reads, and its module.
   checks.mjs asserts this list covers every [data-figure] in the DOM, so a
   figure cannot reach the page without reaching the checks. */
const FIGURES = [
  { id: "fig01", key: "fig01_coverage", module: fig01 },
  { id: "fig02", key: "fig02_double_gap", module: fig02 },
  { id: "fig03", key: "fig03_rate_by_year", module: fig03 },
  { id: "fig05", key: "fig05_share_crossover", module: fig05 },
  { id: "fig06", key: "fig06_subdomain", module: fig06 },
  { id: "fig07", key: "fig07_cycle", module: fig07 },
  { id: "fig08", key: "fig08_crisis", module: fig08 },
  { id: "fig09", key: "fig09_instruments", module: fig09 },
  { id: "fig10", key: "fig10_depth_need", module: fig10 },
  { id: "fig11", key: "fig11_power_wall", module: fig11 },
  { id: "fig12", key: "fig12_continuity", module: fig12 },
  { id: "figM1", key: "figM1_censoring", module: figM1 },
];

async function boot() {
  const { findings, series } = await load();

  // The numbers are already on the page, injected at build time. This checks
  // them rather than writing them: a mismatch means index.html was published
  // against a stale injection.
  const stale = verifyKeys(document, findings);
  if (stale.length) {
    throw new Error(
      `${stale.length} stale statistic(s) on the page:\n  ${stale.join("\n  ")}\n` +
        "Re-run `make web-data`."
    );
  }

  // Built on reveal, not at load: fourteen SVGs constructed at once block the
  // main thread for a noticeable time, and the entrance only means anything if
  // the reader is looking at it.
  for (const { id, key, module } of FIGURES) {
    const container = document.querySelector(`[data-figure="${id}"]`);
    if (!container) continue;
    const spec = figure(series, key);
    onReveal(container, (node, options) => module.render(node, spec, findings, options));
  }

  // The pinned sequence. Its own controller: it is driven by which step block
  // is in view rather than by a single reveal, and it chooses between a pinned
  // and a stacked layout.
  // Built immediately rather than on reveal. The section is several viewports
  // tall, so 25% of it never fits the screen and a reveal observer on it would
  // never fire; its own step observers handle the rest.
  const scrolly = document.querySelector(".scrolly");
  if (scrolly) initScrolly(scrolly, figure(series, "fig04_ladder"), findings);

  // The progress rail. Position only; no section names, no labels.
  const fill = document.querySelector(".rail__fill");
  if (fill) {
    const update = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = scrollable > 0 ? window.scrollY / scrollable : 0;
      fill.style.height = `${Math.min(1, Math.max(0, ratio)) * 100}%`;
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update, { passive: true });
  }

  document.documentElement.dataset.ready = "true";
}

boot().catch((error) => {
  document.documentElement.dataset.ready = "error";
  console.error(error);
  const banner = document.createElement("div");
  banner.className = "figure__error";
  banner.setAttribute("role", "alert");
  banner.textContent = `This page failed to load its data: ${error.message}`;
  document.body.prepend(banner);
});
