/* fig08_crisis.js — deal volume indexed to the pre-crisis base year.
 *
 * Descriptive, and the figure says so. Green volume was already growing faster
 * than non-green before the event window, so parallel trends fail and no
 * difference-in-differences coefficient is reported. The emerging-market green
 * series is not drawn at all: its base year holds a single deal.
 */

import { renderLines } from "./lines.js";

export function render(container, spec, findings, options) {
  const series = spec.series.map((s) => ({
    ...s,
    points: s.points.map((p) => ({ ...p, value: p.indexed })),
  }));
  const byId = new Map(series.map((s) => [s.id, new Map(s.points.map((p) => [p.year, p]))]));

  renderLines(
    container,
    {
      series,
      axis: spec.axis,
      reference: 100,
      band: spec.crisis_window,
      label:
        "The crisis hit green venture funding and left non-green growing. " +
        series
          .map((s) => `${s.label}: ${s.points.map((p) => `${p.year} index ${p.indexed}`).join(", ")}`)
          .join("; "),
      tooltip: (year) =>
        series.map((s) => {
          const p = byId.get(s.id).get(year);
          return [s.label, p ? `index ${p.indexed} · ${p.deals} deals` : "no data", s.colour_role];
        }),
    },
    options
  );
}
