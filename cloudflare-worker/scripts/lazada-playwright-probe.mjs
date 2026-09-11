import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const BLOCK_MARKERS = [
  "captcha",
  "security check",
  "verify you are human",
  "access denied",
  "unusual traffic",
  "robot check",
  "are you a robot",
];
const TCG_KEYWORDS = ["pokemon", "pokémon", "tcg", "trading card"];
const artifactsDir = path.resolve(process.env.PROBE_ARTIFACT_DIR || "probe-artifacts");
const lazadaUrl = process.env.LAZADA_URL;

if (!lazadaUrl) {
  throw new Error("LAZADA_URL is not configured");
}

function parseJsonObjectAt(text, start) {
  if (text[start] !== "{") return null;
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < text.length; i += 1) {
    const char = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') inString = false;
      continue;
    }

    if (char === '"') inString = true;
    else if (char === "{") depth += 1;
    else if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        try {
          return JSON.parse(text.slice(start, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function extractEmbeddedJson(body) {
  for (const marker of ['{"templates"', '{"mods"', '{"modsData"', '{"data"']) {
    let start = body.indexOf(marker);
    while (start >= 0) {
      const parsed = parseJsonObjectAt(body, start);
      if (parsed && typeof parsed === "object") return parsed;
      start = body.indexOf(marker, start + marker.length);
    }
  }
  return null;
}

function* candidateItemLists(node, depth = 0) {
  if (depth > 12 || node === null || node === undefined) return;
  if (Array.isArray(node)) {
    for (const value of node) yield* candidateItemLists(value, depth + 1);
    return;
  }
  if (typeof node !== "object") return;

  for (const [key, value] of Object.entries(node)) {
    if (["listItems", "items", "products", "productList"].includes(key) && Array.isArray(value)) {
      const dictItems = value.filter((x) => x && typeof x === "object" && !Array.isArray(x));
      if (dictItems.length) yield dictItems;
    }
    yield* candidateItemLists(value, depth + 1);
  }
}

function productName(item) {
  return String(item?.name || item?.title || item?.productName || "");
}

function inspectPayload(sourceBody) {
  let payload = null;
  try {
    payload = JSON.parse(sourceBody);
  } catch {
    payload = extractEmbeddedJson(sourceBody);
  }

  if (!payload || typeof payload !== "object") {
    return { payloadFound: false, productCandidates: 0, tcgCandidates: 0 };
  }

  let best = [];
  for (const items of candidateItemLists(payload)) {
    const recognizable = items.filter((item) => {
      const name = productName(item);
      return Boolean(name && (item.itemUrl || item.url || item.productUrl || item.skuId || item.itemId || item.productId || item.sku));
    });
    if (recognizable.length > best.length) best = recognizable;
  }

  const tcgCandidates = best.filter((item) => {
    const name = productName(item).normalize("NFKD").toLowerCase();
    return TCG_KEYWORDS.some((keyword) => name.includes(keyword));
  }).length;

  return {
    payloadFound: true,
    productCandidates: best.length,
    tcgCandidates,
  };
}

async function appendSummary(diagnostics) {
  if (!process.env.GITHUB_STEP_SUMMARY) return;
  const lines = [
    "## Lazada Playwright probe",
    "",
    `- Result: **${diagnostics.result}**`,
    `- HTTP status: ${diagnostics.httpStatus ?? "unknown"}`,
    `- Final URL: ${diagnostics.finalUrl}`,
    `- Title: ${diagnostics.title || "(empty)"}`,
    `- Block marker: ${diagnostics.blockMarker || "none"}`,
    `- HTML bytes: ${diagnostics.htmlBytes}`,
    `- Embedded payload: ${diagnostics.payloadFound}`,
    `- Product candidates: ${diagnostics.productCandidates}`,
    `- TCG candidates: ${diagnostics.tcgCandidates}`,
  ];
  await writeFile(process.env.GITHUB_STEP_SUMMARY, `${lines.join("\n")}\n`, { flag: "a" });
}

await mkdir(artifactsDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
let exitCode = 0;

try {
  const context = await browser.newContext({
    locale: "en-SG",
    timezoneId: "Asia/Singapore",
    viewport: { width: 1440, height: 1200 },
  });
  const page = await context.newPage();

  const response = await page.goto(lazadaUrl, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(2_000);

  const html = await page.content();
  const title = await page.title();
  const finalUrl = page.url();
  const bodyText = await page.locator("body").innerText({ timeout: 5_000 }).catch(() => "");
  const lower = `${title}\n${bodyText}\n${html}`.toLowerCase();
  const blockMarker = BLOCK_MARKERS.find((marker) => lower.includes(marker)) || null;
  // Chromium wraps application/json responses in an HTML <pre>; body.innerText
  // recovers the original JSON string while page.content() is retained as an artifact.
  const payload = inspectPayload(bodyText || html);

  let result = "success";
  if (blockMarker || [403, 429].includes(response?.status())) {
    result = "blocked";
    exitCode = 2;
  } else if (!payload.payloadFound || payload.productCandidates === 0) {
    result = "unparseable";
    exitCode = 3;
  } else if (payload.tcgCandidates === 0) {
    result = "no-tcg-products";
    exitCode = 4;
  }

  const diagnostics = {
    checkedAt: new Date().toISOString(),
    result,
    httpStatus: response?.status() ?? null,
    finalUrl,
    title,
    blockMarker,
    htmlBytes: Buffer.byteLength(html),
    bodyPreview: bodyText.replace(/\s+/g, " ").slice(0, 1000),
    ...payload,
  };

  await Promise.all([
    writeFile(path.join(artifactsDir, "probe.json"), `${JSON.stringify(diagnostics, null, 2)}\n`),
    writeFile(path.join(artifactsDir, "page.html"), html),
    page.screenshot({ path: path.join(artifactsDir, "screenshot.png"), fullPage: true }),
    appendSummary(diagnostics),
  ]);

  console.log(JSON.stringify(diagnostics, null, 2));
} finally {
  await browser.close();
}

process.exitCode = exitCode;
