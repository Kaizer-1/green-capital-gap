/* reveal.js — render and animate a figure when it first comes into view.
 *
 * Two jobs, and the second is the one that matters:
 *
 * 1. Charts are built on reveal rather than at load. Fourteen SVGs constructed
 *    at once block the main thread for a noticeable time (WEB.md §9).
 * 2. The entrance runs ONCE. A chart that re-animates every time it re-enters
 *    the viewport is the single most irritating pattern on the web, and the
 *    observer is disconnected after the first fire so scrolling back cannot
 *    retrigger it.
 *
 * With `prefers-reduced-motion: reduce` the figure is built in its final state
 * and nothing animates. That is checked, not assumed: `checks.mjs` asserts no
 * element reports a non-zero duration under that media query.
 */

const THRESHOLD = 0.25;

/** True when the reader has asked for less motion. */
export function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Call `render(element, { animate })` the first time `element` is 25% visible.
 *
 * Falls back to rendering immediately where IntersectionObserver is missing: a
 * missing chart is worse than an unanimated one.
 */
export function onReveal(element, render) {
  const animate = !reducedMotion();

  if (typeof IntersectionObserver !== "function") {
    render(element, { animate: false });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        // Disconnect BEFORE rendering: building the chart changes the element's
        // height, which can fire the observer again mid-render.
        observer.disconnect();
        render(element, { animate });
      }
    },
    { threshold: THRESHOLD }
  );
  observer.observe(element);
}

/**
 * Draw a line left to right by animating its dash offset.
 *
 * Linear, because a line being drawn is a process at constant speed; easing it
 * would imply the data arrives faster in the middle.
 */
export function drawLine(path, duration = 700) {
  const length = path.getTotalLength();
  path.style.strokeDasharray = `${length}`;
  path.style.strokeDashoffset = `${length}`;
  // Force layout so the transition has a starting value to animate from.
  path.getBoundingClientRect();
  path.style.transition = `stroke-dashoffset ${duration}ms linear`;
  path.style.strokeDashoffset = "0";
  // Clear the dash once drawn, so a dashed series keeps its own pattern.
  window.setTimeout(() => {
    path.style.strokeDasharray = "";
    path.style.transition = "";
  }, duration + 40);
}

/**
 * Grow a horizontal bar from the axis.
 *
 * Stagger is capped deliberately: at 100ms a twenty-bar chart takes two seconds
 * and the reader has moved on.
 */
export function growBar(rect, finalWidth, { index = 0, duration = 500, stagger = 50 } = {}) {
  rect.setAttribute("width", 0);
  window.setTimeout(() => {
    rect.style.transition = `width ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
    rect.setAttribute("width", finalWidth);
  }, index * stagger);
}

/** Fade an element in after a delay, for labels that follow their mark. */
export function fadeIn(node, { delay = 0, duration = 400 } = {}) {
  node.style.opacity = "0";
  window.setTimeout(() => {
    node.style.transition = `opacity ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
    node.style.opacity = "1";
  }, delay);
}
