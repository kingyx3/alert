import { chromium } from "playwright-core";
import { existsSync } from "node:fs";
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

const lazadaUrl = process.env.LAZADA_URL;
const monitorUrl = String(process.env.MONITOR_URL || "").replace(/\/$/, "");
const debugToken = process.env.DEBUG_TOKEN || "";
const ingestEnabled = String(process.env.INGEST_ENABLED || "false").toLowerCase() === "true";
const batchId = process.env.BATCH_ID || `local-${Date.now()}`;
const runnerSlot = process.env.PROBE_SLOT || "1";
const artifactsDir = path.resolve(process.env.PROBE_ARTIFACT_DIR || `probe-artifacts-${runnerSlot}`);
const tcgKeywords = String(process.env.TCG_KEYWORDS || "pokemon,pokémon,tcg,trading card")
  .split(",")
  .map((value) => value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim())
  .filter(Boolean);

if (!lazadaUrl) throw new Error("LAZADA_URL is not configured");
if (ingestEnabled && (!monitorUrl || !debugToken)) {
  throw new Error("MONITOR_URL/DEBUG_TOKEN are required when INGEST_ENABLED=true");
}

function parseBooleanSignal(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "1", "yes", "available", "in stock", "instock"].includes(normalized)) return true;
    if (["false", "0", "no", "unavailable", "out of stock", "sold out"].includes(normalized)) return false;
  }
  return null;
}

function inferInStock(item) {
  if (Object.prototype.hasOwnProperty.call(item, "inStock")) return parseBooleanSignal(item.inStock);
  if (Object.prototype.hasOwnProperty.call(item, "soldOut")) {
    const soldOut = parseBooleanSignal(item.soldOut);
    return soldOut === null ? null : !soldOut;
  }
  for (const key of ["stock", "stockCount", "quantity", "availableStock"]) {
    if (Object.prototype.hasOwnProperty.call(item, key)) {
      const value = Number(item[key]);
      if (Number.isFinite(value)) return value > 0;
    }
  }
  const availability = String(item.availability || item.stockStatus || item.status || "").toLowerCase();
  if (["out of stock", "sold out", "unavailable"].some((value) => availability.includes(value))) return false;
  if (["in stock", "available"].some((value) => availability.includes(value))) return true;
  return null;
}

function normalizeProduct(item) {
  let itemUrl = item.itemUrl || item.url || item.productUrl || "";
  if (typeof itemUrl === "string" && itemUrl.startsWith("//")) itemUrl = `https:${itemUrl}`;

  let price = item.price ?? item.salePrice ?? null;
  if (price !== null && price !== "") {
    const parsed = Number(price);
    price = Number.isFinite(parsed) ? parsed : null;
  } else {
    price = null;
  }

  return {
    name: String(item.name || item.title || item.productName || ""),
    price,
    priceShow: String(item.priceShow || item.originalPriceShow || item.salePriceShow || ""),
    inStock: inferInStock(item),
    sold: String(item.itemSoldCntShow || item.itemSoldCnt || item.sold || ""),
    url: itemUrl || null,
    image: item.image || item.imageUrl || null,
    skuId: item.skuId || item.itemId || item.productId || null,
    sku: item.sku || item.skuCode || null,
    sellerName: item.sellerName || null,
    sellerId: item.sellerId || null,
  };
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
      const items = value.filter((item) => item && typeof item === "object" && !Array.isArray(item));
      if (items.length) yield items;
    }
    yield* candidateItemLists(value, depth + 1);
  }
}

function parseProducts(sourceBody) {
  let payload = null;
  try {
    payload = JSON.parse(sourceBody);
  } catch {
    payload = extractEmbeddedJson(sourceBody);
  }
  if (!payload || typeof payload !== "object") {
    return { payloadFound: false, products: [], tcgProducts: [] };
  }

  let best = [];
  for (const items of candidateItemLists(payload)) {
    const normalized = items
      .map(normalizeProduct)
      .filter((product) => product.name && (product.url || product.skuId || product.sku));
    if (normalized.length > best.length) best = normalized;
  }

  const tcgProducts = best.filter((product) => {
    const name = product.name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    return tcgKeywords.some((keyword) => name.includes(keyword));
  });

  return { payloadFound: true, products: best, tcgProducts };
}

function chromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) throw new Error("No preinstalled Chrome/Chromium executable found");
  return found;
}

async function postSnapshot(snapshot) {
  const response = await fetch(`${monitorUrl}/snapshot`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${debugToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(snapshot),
  });
  const text = await response.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text.slice(0, 500) };
  }
  return { ok: response.ok && body?.ok === true, status: response.status, body };
}

async function appendSummary(diagnostics) {
  if (!process.env.GITHUB_STEP_SUMMARY) return;
  const lines = [
    "## Lazada Playwright runner",
    "",
    `- Slot: ${runnerSlot}`,
    `- Result: **${diagnostics.result}**`,
    `- HTTP status: ${diagnostics.httpStatus ?? "unknown"}`,
    `- Block marker: ${diagnostics.blockMarker || "none"}`,
    `- Products: ${diagnostics.productCandidates}`,
    `- TCG products: ${diagnostics.tcgCandidates}`,
    `- Ingest enabled: ${ingestEnabled}`,
    `- Ingest OK: ${diagnostics.ingestOk ?? false}`,
    `- Restocked: ${diagnostics.ingestRestocked ?? 0}`,
  ];
  await writeFile(process.env.GITHUB_STEP_SUMMARY, `${lines.join("\n")}\n`, { flag: "a" });
}

await mkdir(artifactsDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: chromeExecutable(),
});
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

  // The Lazada AJAX endpoint normally returns the inventory JSON as the main
  // response. Parse that response first and submit it immediately. DOM capture,
  // screenshots, artifacts, and other runners must never sit on the alert path.
  const checkedAt = new Date().toISOString();
  const httpStatus = response?.status() ?? null;
  const finalUrl = page.url();
  const sourceBody = await response?.text().catch(() => "") || "";
  let title = "";
  let html = "";
  let bodyText = "";
  let lower = `${finalUrl}\n${sourceBody}`.toLowerCase();
  let blockMarker = BLOCK_MARKERS.find((marker) => lower.includes(marker)) || null;
  let parsed = parseProducts(sourceBody);

  // Only pay the DOM-inspection cost when the main response is blocked or is
  // not directly parseable. A clean JSON response reaches /snapshot first.
  if (blockMarker || !parsed.payloadFound || parsed.products.length === 0) {
    [title, html, bodyText] = await Promise.all([
      page.title().catch(() => ""),
      page.content().catch(() => ""),
      page.locator("body").innerText({ timeout: 5_000 }).catch(() => ""),
    ]);
    lower = `${finalUrl}\n${title}\n${bodyText}\n${html}`.toLowerCase();
    blockMarker = BLOCK_MARKERS.find((marker) => lower.includes(marker)) || null;
    if (!parsed.payloadFound || parsed.products.length === 0) {
      parsed = parseProducts(sourceBody || bodyText || html);
    }
  }

  let result = "success";
  if (blockMarker || [403, 429].includes(httpStatus)) {
    result = "blocked";
    exitCode = 2;
  } else if (!parsed.payloadFound || parsed.products.length === 0) {
    result = "unparseable";
    exitCode = 3;
  } else if (parsed.tcgProducts.length === 0) {
    result = "no-tcg-products";
    exitCode = 4;
  }

  let ingest = null;
  if (result === "success" && ingestEnabled) {
    ingest = await postSnapshot({
      batchId,
      runnerSlot,
      checkedAt,
      httpStatus,
      finalUrl,
      products: parsed.tcgProducts,
    });
    if (!ingest.ok) exitCode = 5;
  }

  const diagnosticBody = bodyText || sourceBody;
  const diagnosticHtml = html || sourceBody;
  const diagnostics = {
    checkedAt,
    batchId,
    runnerSlot,
    result,
    httpStatus,
    finalUrl,
    title,
    blockMarker,
    htmlBytes: Buffer.byteLength(diagnosticHtml),
    bodyPreview: diagnosticBody.replace(/\s+/g, " ").slice(0, 700),
    payloadFound: parsed.payloadFound,
    productCandidates: parsed.products.length,
    tcgCandidates: parsed.tcgProducts.length,
    ingestEnabled,
    ingestOk: ingest?.ok ?? false,
    ingestStatus: ingest?.status ?? null,
    ingestDuplicate: ingest?.body?.duplicate ?? null,
    ingestSuperseded: ingest?.body?.superseded ?? null,
    ingestRestocked: ingest?.body?.restocked ?? 0,
  };

  await writeFile(path.join(artifactsDir, "probe.json"), `${JSON.stringify(diagnostics, null, 2)}\n`);
  if (result !== "success") {
    if (!html) html = await page.content().catch(() => sourceBody);
    await Promise.all([
      writeFile(path.join(artifactsDir, "page.html"), html || sourceBody),
      page.screenshot({ path: path.join(artifactsDir, "screenshot.png"), fullPage: true }),
    ]);
  }
  await appendSummary(diagnostics);
  console.log(JSON.stringify(diagnostics, null, 2));
} finally {
  await browser.close();
}

process.exitCode = exitCode;
