/* fig03_rate_by_year.js — the green rate by bloc and year.
 *
 * Descriptive only. No emerging-market year-cell reaches the pre-registered
 * minimum, so no per-year test is reported and every cell below it is marked on
 * the line rather than only in the caption.
 */

import { renderLines } from "./lines.js";

export function render(container, spec, findings, options) {
  const series = spec.series.map((s) => ({
    ...s,
    points: s.points.map((p) => ({ ...p, value: p.rate })),
  }));
  const byId = new Map(series.map((s) => [s.id, new Map(s.points.map((p) => [p.year, p]))]));

  renderLines(
    container,
    {
      series,
      axis: spec.axis,
      label:
        "The two rates met in 2008, at the peak of Cleantech 1.0, then diverged. " +
        series
          .map((s) => `${s.label}: ${s.points.map((p) => `${p.year} ${p.rate}%`).join(", ")}`)
          .join("; "),
      annotations: spec.annotations.filter((a) => a.id === "parity_2008"),
      // A marker on every emerging-market cell below the minimum, which is all
      // of them: the figure should not need its caption to say so.
      pointNote: (p, id) => (id === "EM" && p.below_min_cell ? "below minimum" : null),
      tooltip: (year) =>
        series.map((s) => {
          const p = byId.get(s.id).get(year);
          if (!p) return [s.label, "no data", s.colour_role];
          const cell = p.below_min_cell ? ` · ${p.green} green deals, below the minimum` : "";
          return [s.label, `${p.rate}%${cell}`, s.colour_role];
        }),
    },
    options
  );
}
