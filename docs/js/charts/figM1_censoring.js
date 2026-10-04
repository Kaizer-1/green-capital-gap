/* figM1_censoring.js — monthly deals as a share of their own year.
 *
 * A methodology figure. Expressing each month as a share of its own year
 * removes the level difference between years, so the shapes are comparable and
 * the censored month is visible as a shape rather than asserted as a rule.
 */

import { renderLines } from "./lines.js";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function render(container, spec, findings, options) {
  const series = spec.series.map((s) => ({
    ...s,
    points: s.points.map((p) => ({ ...p, value: p.share })),
  }));
  const byId = new Map(series.map((s) => [s.id, new Map(s.points.map((p) => [p.month, p]))]));

  renderLines(
    container,
    {
      series,
      axis: spec.axis,
      xKey: "month",
      xFormat: (m) => MONTHS[Math.round(m) - 1] ?? String(m),
      label:
        "Only December 2013 is censored, which is why the window closes at 2012. " +
        series
          .map((s) => `${s.label}: ${s.points.map((p) => `${MONTHS[p.month - 1]} ${p.share}%`).join(", ")}`)
          .join("; "),
      tooltip: (month) =>
        series.map((s) => {
          const p = byId.get(s.id).get(month);
          return [s.label, p ? `${p.share}% · ${p.deals.toLocaleString()} deals` : "", s.colour_role];
        }),
    },
    options
  );
}
