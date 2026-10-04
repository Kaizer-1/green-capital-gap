/* deployed.mjs — serve the built tree the way GitHub Pages serves it.
 *
 * Pages publishes a project site at `user.github.io/<repo>/`, not at the server
 * root. Everything the local harness does is rooted at `web/`, so a path that
 * only works at the root passes every local check and 404s once deployed. This
 * serves `docs/` under a `/<repo>/` prefix and nothing at the root, which makes
 * that class of defect fail here instead of in public.
 *
 * It then runs the full check suite against that URL. A failure here that
 * passed locally is the deploy, not the page.
 *
 * Usage: node test/deployed.mjs ../docs [repo-name]
 */

import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { spawn } from "node:child_process";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

const root = resolve(process.argv[2] ?? "../docs");
const repo = process.argv[3] ?? "green-capital-gap";
const prefix = `/${repo}/`;

/**
 * Case-sensitive file serving, which is what Pages does and what macOS does
 * not. A request is only answered if the path's spelling matches the entry on
 * disk, so a mis-cased reference 404s here as it would in production.
 */
async function resolveExact(relPath) {
  const parts = normalize(relPath).split("/").filter(Boolean);
  let here = root;
  for (const part of parts) {
    const { readdir } = await import("node:fs/promises");
    let names;
    try {
      names = await readdir(here);
    } catch {
      return null;
    }
    if (!names.includes(part)) return null;
    here = join(here, part);
  }
  return here;
}

const misses = [];

const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  let path = decodeURIComponent(url.pathname);

  if (!path.startsWith(prefix)) {
    // Pages serves nothing above the project path. A request that lands here
    // is a root-relative path that would break in production.
    misses.push(`${path}  (outside the project path ${prefix})`);
    res.writeHead(404).end("not found");
    return;
  }
  path = path.slice(prefix.length) || "index.html";
  if (path.endsWith("/")) path += "index.html";

  const file = await resolveExact(path);
  if (!file) {
    misses.push(`${path}  (no such file, case-sensitively)`);
    res.writeHead(404).end("not found");
    return;
  }
  try {
    const info = await stat(file);
    if (info.isDirectory()) {
      res.writeHead(404).end("not found");
      return;
    }
    const body = await readFile(file);
    res.writeHead(200, {
      "content-type": TYPES[extname(file)] ?? "application/octet-stream",
      "content-length": body.length,
    });
    res.end(body);
  } catch {
    misses.push(path);
    res.writeHead(500).end("error");
  }
});

await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;
const base = `http://127.0.0.1:${port}${prefix}`;
console.log(`serving ${root} at ${base}\n`);

const child = spawn(process.execPath, ["test/checks.mjs"], {
  stdio: "inherit",
  env: { ...process.env, GCG_BASE_URL: base, GCG_ROOT: root },
});

const code = await new Promise((r) => child.on("exit", r));
server.close();

if (misses.length) {
  console.error(`\n${misses.length} request(s) failed under the project path:`);
  for (const m of [...new Set(misses)]) console.error(`  - ${m}`);
  process.exit(1);
}
if (code !== 0) {
  console.error("\nchecks failed against the deployed tree");
  process.exit(code);
}
console.log("\ndeployed tree serves correctly from a project sub-path");
