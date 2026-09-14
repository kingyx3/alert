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

const scrapingSources = [
  { name: "SCRAPING_URL", url: String(process.env.SCRAPING_URL || "").trim() },
  { name: "SCRAPING_URL_2", url: String(process.env.SCRAPING_URL_2 || "").trim() },
];
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

const missingSources = scrapingSources.filter((source) => !source.url).map((source) => source.name);
if (missingSources.length) throw new Error(`${missingSources.join("/")} are not configured`);
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

function productKey(product) {
  for (const field of ["skuId", "sku", "url", "name"]) {
    const value = product[field];
    if (value !== null && value !== undefined && value !== "") return `${field}:${value}`;
  }
  return null;
}

function mergeProducts(productGroups) {
  const merged = new Map();
  for (const products of productGroups) {
    for (const product of products) {
      const key = productKey(product);
      if (!key) continue;
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, product);
        continue;
      }

      let inStock = null;
      if (existing.inStock === true || product.inStock === true) inStock = true;
      else if (existing.inStock === false || product.inStock === false) inStock = false;

      // Keep the first source's canonical fields, but treat an in-stock signal
      // from either endpoint as sufficient evidence that the SKU is available.
      merged.set(key, { ...product, ...existing, inStock });
    }
  }
  return [...merged.values()];
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
    `- Sources: ${diagnostics.sources.length}`,
    `- Products: ${diagnostics.productCandidates}`,
    `- TCG products after de-duplication: ${diagnostics.tcgCandidates}`,
    `- Source ready: ${diagnostics.sourceReadyMs ?? "unknown"} ms`,
    `- Ingest round trip: ${diagnostics.ingestRoundTripMs ?? "n/a"} ms`,
    `- Ingest enabled: ${ingestEnabled}`,
    `- Ingest OK: ${diagnostics.ingestOk ?? false}`,
    `- Restocked: ${diagnostics.ingestRestocked ?? 0}`,
    "",
    "### Sources",
  ];
  for (const source of diagnostics.sources) {
    lines.push(
      `- ${source.name}: ${source.result}; HTTP ${source.httpStatus ?? "unknown"}; ` +
        `${source.productCandidates} products / ${source.tcgCandidates} TCG; ` +
        `block=${source.blockMarker || "none"}`,
    );
  }
  await writeFile(process.env.GITHUB_STEP_SUMMARY, `${lines.join("\n")}\n`, { flag: "a" });
}

async function probeSource(context, source, sourceIndex) {
  const page = await context.newPage();
  const navigationStartedAt = Date.now();
  let response = null;
  let sourceBody = "";
  let title = "";
  let html = "";
  let bodyText = "";

  try {
    response = await page.goto(source.url, {
      // The inventory payload is in the main response. Resolve as soon as the
      // response commits so both endpoints can be combined with minimal latency.
      waitUntil: "commit",
      timeout: 45_000,
    });

    const httpStatus = response?.status() ?? null;
    const finalUrl = page.url();
    sourceBody = await response?.text().catch(() => "") || "";
    const sourceReadyAt = Date.now();
    let lower = `${finalUrl}\n${sourceBody}`.toLowerCase();
    let blockMarker = BLOCK_MARKERS.find((marker) => lower.includes(marker)) || null;
    let parsed = parseProducts(sourceBody);

    if (blockMarker || !parsed.payloadFound || parsed.products.length === 0) {
      await page.waitForLoadState("domcontentloaded", { timeout: 8_000 }).catch(() => {});
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
    if (blockMarker || [403, 429].includes(httpStatus)) result = "blocked";
    else if (httpStatus !== null && (httpStatus < 200 || httpStatus >= 300)) result = "http-error";
    else if (!parsed.payloadFound || parsed.products.length === 0) result = "unparseable";

    if (result !== "success") {
      if (!html) html = await page.content().catch(() => sourceBody);
      await Promise.all([
        writeFile(path.join(artifactsDir, `source-${sourceIndex + 1}-page.html`), html || sourceBody),
        page.screenshot({
          path: path.join(artifactsDir, `source-${sourceIndex + 1}-screenshot.png`),
          fullPage: true,
        }).catch(() => {}),
      ]);
    }

    const diagnosticBody = bodyText || sourceBody;
    const diagnosticHtml = html || sourceBody;
    return {
      name: source.name,
      requestedUrl: source.url,
      result,
      httpStatus,
      finalUrl,
      title,
      blockMarker,
      sourceReadyMs: sourceReadyAt - navigationStartedAt,
      htmlBytes: Buffer.byteLength(diagnosticHtml),
      bodyPreview: diagnosticBody.replace(/\s+/g, " ").slice(0, 700),
      payloadFound: parsed.payloadFound,
      productCandidates: parsed.products.length,
      tcgCandidates: parsed.tcgProducts.length,
      tcgProducts: parsed.tcgProducts,
    };
  } catch (error) {
    const finalUrl = page.url();
    html = await page.content().catch(() => "");
    bodyText = await page.locator("body").innerText({ timeout: 3_000 }).catch(() => "");
    await Promise.all([
      writeFile(path.join(artifactsDir, `source-${sourceIndex + 1}-page.html`), html || String(error)),
      page.screenshot({
        path: path.join(artifactsDir, `source-${sourceIndex + 1}-screenshot.png`),
        fullPage: true,
      }).catch(() => {}),
    ]);
    return {
      name: source.name,
      requestedUrl: source.url,
      result: "navigation-error",
      httpStatus: response?.status() ?? null,
      finalUrl,
      title: await page.title().catch(() => ""),
      blockMarker: null,
      sourceReadyMs: Date.now() - navigationStartedAt,
      htmlBytes: Buffer.byteLength(html || ""),
      bodyPreview: (bodyText || String(error)).replace(/\s+/g, " ").slice(0, 700),
      payloadFound: false,
      productCandidates: 0,
      tcgCandidates: 0,
      tcgProducts: [],
      error: String(error?.message || error),
    };
  } finally {
    await page.close().catch(() => {});
  }
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

  const batchStartedAt = Date.now();
  const sourceResults = [];
  for (const [sourceIndex, source] of scrapingSources.entries()) {
    sourceResults.push(await probeSource(context, source, sourceIndex));
  }

  const checkedAt = new Date().toISOString();
  const products = mergeProducts(sourceResults.map((source) => source.tcgProducts));
  const blockedSource = sourceResults.find((source) => source.result === "blocked");
  const failedSource = sourceResults.find((source) => source.result !== "success");

  let result = "success";
  if (blockedSource) {
    result = "blocked";
    exitCode = 2;
  } else if (failedSource) {
    result = failedSource.result;
    exitCode = 3;
  } else if (products.length === 0) {
    result = "no-tcg-products";
    exitCode = 4;
  }

  let ingest = null;
  let ingestRoundTripMs = null;
  if (result === "success" && ingestEnabled) {
    const ingestStartedAt = Date.now();
    ingest = await postSnapshot({
      batchId,
      runnerSlot,
      checkedAt,
      httpStatus: sourceResults[0]?.httpStatus ?? null,
      finalUrl: sourceResults[0]?.finalUrl || scrapingSources[0].url,
      products,
    });
    ingestRoundTripMs = Date.now() - ingestStartedAt;
    if (!ingest.ok) exitCode = 5;
  }

  const diagnostics = {
    checkedAt,
    batchId,
    runnerSlot,
    result,
    httpStatus: sourceResults[0]?.httpStatus ?? null,
    finalUrl: sourceResults[0]?.finalUrl || scrapingSources[0].url,
    title: sourceResults[0]?.title || "",
    blockMarker: blockedSource?.blockMarker || null,
    sourceReadyMs: Date.now() - batchStartedAt,
    ingestRoundTripMs,
    htmlBytes: sourceResults.reduce((sum, source) => sum + Number(source.htmlBytes || 0), 0),
    bodyPreview: failedSource?.bodyPreview || sourceResults[0]?.bodyPreview || "",
    payloadFound: sourceResults.every((source) => source.payloadFound),
    productCandidates: sourceResults.reduce((sum, source) => sum + source.productCandidates, 0),
    tcgCandidates: products.length,
    ingestEnabled,
    ingestOk: ingest?.ok ?? false,
    ingestStatus: ingest?.status ?? null,
    ingestDuplicate: ingest?.body?.duplicate ?? null,
    ingestSuperseded: ingest?.body?.superseded ?? null,
    ingestRestocked: ingest?.body?.restocked ?? 0,
    sources: sourceResults.map(({ tcgProducts, ...source }) => source),
  };

  await writeFile(path.join(artifactsDir, "probe.json"), `${JSON.stringify(diagnostics, null, 2)}\n`);
  await appendSummary(diagnostics);
  console.log(JSON.stringify(diagnostics, null, 2));
} finally {
  await browser.close();
}

process.exitCode = exitCode;
