/* capture.mjs — screenshots for the review loop.
 *
 * Capturing is worthless unless the images are looked at. This writes them;
 * WEB.md §10.3 is the part that matters, and it is done by hand against the
 * rubric with every file opened.
 *
 * Serves the directory over http rather than file://, because ES modules and
 * fetch both behave differently under file:// and the point is to test what
 * ships.
 */

import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { mkdir, rm } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const OUT_SUFFIX = process.env.GCG_BASE_URL ? "-live" : "";
const OUT = join(ROOT, "test", `screens${OUT_SUFFIX}`);

export const VIEWPORTS = [
  { name: "1440", width: 1440, height: 900 },
  { name: "1024", width: 1024, height: 768 },
  { name: "834", width: 834, height: 1112 },
  { name: "390", width: 390, height: 844 },
];

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".pdf": "application/pdf",
  ".svg": "image/svg+xml",
};

/** A static file server rooted at web/, with ../report reachable for the PDF link. */
/**
 * The base URL the harness should test.
 *
 * Normally it starts its own server at the site root. When GCG_BASE_URL is set
 * — by `make web-deploy-check` — it tests the already-running server instead,
 * which serves the built tree under a `/<repo>/` prefix the way Pages does. The
 * same checks then run against both, so a deploy-only defect fails in the same
 * suite rather than needing a second one.
 */
export function baseURL() {
  return process.env.GCG_BASE_URL ?? null;
}

export function serve(root = ROOT) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    let path = decodeURIComponent(url.pathname);
    if (path.endsWith("/")) path += "index.html";
    const file = normalize(join(root, path));
    try {
      const body = await readFile(file);
      res.writeHead(200, {
        "content-type": TYPES[extname(file)] ?? "application/octet-stream",
      });
      res.end(body);
    } catch {
      res.writeHead(404, { "content-type": "text/plain" });
      res.end("not found");
    }
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () =>
      resolve({ server, port: server.address().port }),
    );
  });
}

/**
 * Scroll the whole page so everything built on reveal has rendered, then return
 * to the top.
 *
 * `behavior: "instant"` is load-bearing. The stylesheet sets
 * `scroll-behavior: smooth`, so a loop of `scrollTo` calls animates: each step
 * is still gliding when the next is issued, the position lags further behind on
 * every iteration, and the loop finishes near the top of a long page. Figures
 * below that point never entered the viewport and so were never built, which
 * read as "the reveal is broken" when the reveal was fine and the harness was
 * not.
 */
export async function scrollThrough(page) {
  // An escape hatch for auditing the checks themselves: with scrolling off,
  // any check about a rendered figure that still passes was passing without its
  // subject ever entering view.
  if (process.env.GCG_NO_SCROLL === "1") return 0;
  return page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    const settle = () => new Promise((r) => setTimeout(r, 80));
    let deepest = 0;
    for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
      window.scrollTo({ top: y, behavior: "instant" });
      await settle();
      deepest = Math.max(deepest, window.scrollY);
    }
    // Once more from the bottom: rendering changes the page's height, so the
    // first pass can stop short of content that moved down behind it.
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: "instant",
    });
    await settle();
    deepest = Math.max(deepest, window.scrollY);
    // How far down the page the scroll actually got, as a fraction. The caller
    // asserts this reached the bottom: the original defect was a scroll that
    // believed it had covered the page and had not, which made every
    // viewport-dependent check pass without its subject entering view.
    const reached =
      (deepest + window.innerHeight) / document.documentElement.scrollHeight;
    window.scrollTo({ top: 0, behavior: "instant" });
    await settle();
    return reached;
  });
}

async function main() {
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  // Against a deployed URL when one is given, so the published site is captured
  // by the same harness that captures the local build and the two are
  // comparable rather than merely similar. Screenshots land in a separate
  // directory so a live run cannot overwrite the local reference set.
  const external = baseURL();
  const { server, port } = external ? { server: null, port: 0 } : await serve();
  const browser = await chromium.launch();
  const base = external ? `${external}index.html` : `http://127.0.0.1:${port}/index.html`;
  const problems = [];

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 2,
    });
    const page = await context.newPage();
    page.on("console", (m) => {
      if (m.type() === "error" || m.type() === "warning") {
        problems.push(`${vp.name}: console ${m.type()}: ${m.text()}`);
      }
    });
    page.on("pageerror", (e) =>
      problems.push(`${vp.name}: pageerror: ${e.message}`),
    );

    await page.goto(base, { waitUntil: "networkidle" });
    await page
      .waitForSelector('html[data-ready="true"]', { timeout: 10_000 })
      .catch(() => {
        problems.push(`${vp.name}: page never reached data-ready="true"`);
      });
    await scrollThrough(page);

    await page.screenshot({
      path: join(OUT, `${vp.name}-full.png`),
      fullPage: true,
    });

    // Every section, framed to the viewport, so the review sees what a reader
    // sees rather than a full-page strip nothing is read at. Discovered from
    // the DOM rather than listed, so a section added later is captured without
    // anyone remembering to add it here.
    const sections = await page.$$eval(
      "header.masthead, main > section[id]",
      (nodes) => nodes.map((n) => (n.id ? `#${n.id}` : "header.masthead")),
    );
    for (const sel of sections) {
      const node = await page.$(sel);
      if (!node) continue;
      await node.scrollIntoViewIfNeeded();
      await page.waitForTimeout(150);
      const name = sel.replace(/[^a-z0-9]/gi, "") || "x";
      await page.screenshot({ path: join(OUT, `${vp.name}-s-${name}.png`) });
    }

    // Each figure at its natural size. A container that is not displayed is
    // skipped rather than waited on: the pinned sequence's host is hidden in
    // the stacked layout, and scrollIntoViewIfNeeded never resolves on it.
    for (const node of await page.$$("[data-figure]")) {
      const id = await node.getAttribute("data-figure");
      const box = await node.boundingBox();
      if (!box || box.width === 0 || box.height === 0) continue;
      await node.scrollIntoViewIfNeeded();
      await page.waitForTimeout(150);
      await node.screenshot({ path: join(OUT, `${vp.name}-${id}.png`) });
    }

    // Horizontal overflow is a hard failure, not a judgement call.
    const overflow = await page.evaluate(() => {
      const d = document.documentElement;
      return { scrollWidth: d.scrollWidth, clientWidth: d.clientWidth };
    });
    if (overflow.scrollWidth > overflow.clientWidth) {
      problems.push(
        `${vp.name}: horizontal overflow, scrollWidth ${overflow.scrollWidth} > clientWidth ${overflow.clientWidth}`,
      );
    }
    await context.close();
  }

  // --- the pinned sequence ----------------------------------------------
  // Each step settled, plus step 3 to 4 MID-TRANSITION. The fade to 30% is
  // where that step either reads as emphasis or as the chart breaking, and the
  // settled frame cannot tell you which.
  const seq = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const seqPage = await seq.newPage();
  await seqPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(seqPage);

  const stepBlocks = await seqPage.locator(".scrolly__step").all();
  const graphic = seqPage.locator("[data-figure='fig04']");
  for (const [i, block] of stepBlocks.entries()) {
    await block.scrollIntoViewIfNeeded();
    await seqPage.waitForTimeout(2200); // let the migration and draw settle
    await graphic.screenshot({ path: join(OUT, `scrolly-step${i + 1}.png`) });

    // Mid-transition into step 4, caught while the fade is still running. The
    // wait is anchored to the step actually changing, not to a guess: timed
    // from the scroll it caught step 3 settled, because the observer had not
    // fired yet.
    if (i === stepBlocks.length - 2) {
      await stepBlocks[i + 1].scrollIntoViewIfNeeded();
      await seqPage.waitForFunction(
        () => document.querySelector(".scrolly")?.dataset.step === "4",
        null,
        { timeout: 5000 },
      );
      await seqPage.waitForTimeout(320); // ~45% through a 700ms fade
      // A CLIPPED PAGE screenshot, not an element one: element.screenshot waits
      // for the element to stop animating, which is precisely the frame being
      // asked for. Timed captures of a transition have to bypass that.
      const clip = await graphic.boundingBox();
      await seqPage.screenshot({
        path: join(OUT, "scrolly-step3to4-mid.png"),
        clip,
      });
      await seqPage.waitForTimeout(2200);
    }
  }

  // Both views of the ladder, after the sequence has run.
  const views = await seqPage.locator("[data-scrolly-toggle] button").all();
  for (const [i, button] of views.entries()) {
    await button.click();
    await seqPage.waitForTimeout(1200);
    await graphic.screenshot({
      path: join(OUT, i === 0 ? "fig04-scatter.png" : "fig04-ladder.png"),
    });
  }
  await seq.close();

  // The stacked variant, which is what mobile and reduced motion get.
  const stack = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
  });
  const stackPage = await stack.newPage();
  await stackPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(stackPage);
  const stackSection = stackPage.locator(".scrolly");
  await stackSection.scrollIntoViewIfNeeded();
  await stackPage.waitForTimeout(400);
  await stackSection.screenshot({ path: join(OUT, "scrolly-stacked-390.png") });
  await stack.close();

  // Reduced motion and no-JS, at desktop.
  const rm1 = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    reducedMotion: "reduce",
  });
  const rmPage = await rm1.newPage();
  await rmPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(rmPage);
  await rmPage.screenshot({
    path: join(OUT, "reduced-motion-full.png"),
    fullPage: true,
  });
  // The sequence under reduced motion: four static states, in order, with the
  // fourth rendered in its emphasised form rather than arrived at.
  const rmScrolly = rmPage.locator(".scrolly");
  await rmScrolly.scrollIntoViewIfNeeded();
  await rmPage.waitForTimeout(300);
  await rmScrolly.screenshot({ path: join(OUT, "scrolly-reduced-motion.png") });
  await rm1.close();

  const nojs = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    javaScriptEnabled: false,
  });
  const nojsPage = await nojs.newPage();
  await nojsPage.goto(base, { waitUntil: "load" });
  await nojsPage.screenshot({
    path: join(OUT, "nojs-full.png"),
    fullPage: true,
  });
  await nojs.close();

  await browser.close();
  server?.close();

  if (problems.length) {
    console.error(`\n${problems.length} problem(s) during capture:`);
    for (const p of problems) console.error(`  ${p}`);
    process.exitCode = 1;
  } else {
    console.log("capture clean: no console errors, no horizontal overflow");
  }
  console.log(`screenshots in ${OUT}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
