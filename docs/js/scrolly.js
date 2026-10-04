/* scrolly.js — the one pinned sequence.
 *
 * Two layouts, chosen at build time rather than by CSS alone, so the JavaScript
 * and the stylesheet cannot disagree about which one is live:
 *
 *   PINNED   the graphic sticks while four blocks of text scroll past it. Used
 *            at desktop and tablet widths with motion allowed.
 *
 *   STACKED  four static states, each with its own graphic above its own
 *            caption, in order. Used at mobile widths AND under
 *            prefers-reduced-motion.
 *
 * The stack is not a degraded fallback that loses the argument. It carries the
 * same four captions in the same order, each beside the state it describes, so
 * a reader who never sees a transition reaches the same conclusion. The fourth
 * state is rendered in its emphasised form directly rather than arrived at.
 *
 * Mobile does not pin. A sticky graphic at 390px is unreliable across browsers
 * and its failure mode is a graphic that sticks or jumps, which is worse than
 * one that never pinned at all.
 */

import { createLadder } from "./charts/fig04_ladder.js";
import { reducedMotion } from "./reveal.js";

const STACK_BELOW = 760;

export function initScrolly(section, spec, findings = {}) {
  if (!section) return null;

  const steps = [...section.querySelectorAll(".scrolly__step")];
  if (!steps.length) return null;

  const stacked = window.innerWidth < STACK_BELOW || reducedMotion();
  section.dataset.layout = stacked ? "stacked" : "pinned";

  return stacked
    ? buildStack(section, spec, steps, findings)
    : buildPinned(section, spec, steps, findings);
}

/** Four static states, one per step, each above its own caption. */
function buildStack(section, spec, steps, findings) {
  const instances = steps.map((stepEl, i) => {
    const host = stepEl.querySelector(".scrolly__step-graphic");
    if (!host) return null;
    const ladder = createLadder(host, spec, { animate: false, height: 340, findings });
    // Rendered in its final state, not animated into it. Step 4 therefore has
    // to read as emphasis on arrival rather than as the end of a movement.
    ladder.setStep(i + 1, { animate: false });
    // NOTE: data-active means something different in each layout. Pinned, it
    // marks the ONE step a reader is on. Stacked, every step is equally
    // current, so all four carry it. Anything that styles or counts on
    // data-active must therefore be scoped to a layout — a rule that assumed
    // "exactly one" painted its active marker down the whole section here.
    stepEl.dataset.active = "true";
    return ladder;
  });
  return { layout: "stacked", instances: instances.filter(Boolean) };
}

/** One pinned graphic, driven by which step block is in view. */
function buildPinned(section, spec, steps, findings) {
  const host = section.querySelector("[data-figure='fig04']");
  if (!host) return null;

  // Taller than the default: the pinned column is narrow, and a log y axis
  // spanning two orders of magnitude needs the height to stay readable.
  const ladder = createLadder(host, spec, { animate: true, height: 430, findings });
  let active = 0;

  const activate = (step) => {
    if (step === active) return;
    // Only animate forwards. Scrolling back re-states the earlier step without
    // replaying its entrance, because a sequence that re-animates on every
    // scroll-back is the pattern this file exists to avoid.
    const forwards = step > active;
    active = step;
    ladder.setStep(step, { animate: forwards });
    for (const [i, el] of steps.entries()) {
      el.dataset.active = String(i + 1 === step);
    }
    section.dataset.step = String(step);
  };

  const observer = new IntersectionObserver(
    (entries) => {
      // The step whose block is nearest the middle of the viewport wins, so a
      // fast scroll lands on one state rather than flickering through several.
      const visible = entries.filter((e) => e.isIntersecting);
      if (!visible.length) return;
      const best = visible.reduce((a, b) =>
        Math.abs(b.intersectionRatio - 1) < Math.abs(a.intersectionRatio - 1) ? b : a
      );
      activate(steps.indexOf(best.target) + 1);
    },
    { rootMargin: "-45% 0px -45% 0px", threshold: [0, 0.5, 1] }
  );
  for (const el of steps) observer.observe(el);

  // Keyboard: every step reachable by Tab, operable by Enter and Space.
  steps.forEach((el, i) => {
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    el.setAttribute("aria-label", `Step ${i + 1} of ${steps.length}`);
    el.addEventListener("focus", () => activate(i + 1));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        activate(i + 1);
      }
    });
  });

  // The ladder ⇄ scatter toggle, available once the sequence has run. Before
  // that it would offer a view of a chart the reader has not been shown.
  const toggleHost = section.querySelector("[data-scrolly-toggle]");
  if (toggleHost) {
    const views = [
      { id: "scatter", label: "Against capital intensity" },
      { id: "ladder", label: "Ranked by representation" },
    ];
    for (const v of views) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = v.label;
      button.setAttribute("aria-pressed", String(v.id === "scatter"));
      button.addEventListener("click", () => {
        ladder.setView(v.id);
        for (const b of toggleHost.querySelectorAll("button")) {
          b.setAttribute("aria-pressed", String(b.textContent === v.label));
        }
      });
      toggleHost.appendChild(button);
    }
  }

  activate(1);
  return { layout: "pinned", ladder, steps };
}
