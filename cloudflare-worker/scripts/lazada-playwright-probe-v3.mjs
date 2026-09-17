import { chromium } from "playwright-core";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { mergeProducts, parseProducts } from "./lazada-product-parser.mjs";
import {
  BLOCK_MARKERS,
  scrapingSources,
  monitorUrl,
  debugToken,
  ingestEnabled,
  batchId,
  runnerSlot,
  artifactsDir,
} from "./lazada-probe-config.mjs";

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
      waitUntil: "commit",
      timeout: 45_000,
    });

    const httpStatus = response?.status() ?? null;
    const finalUrl = page.url();
    sourceBody = (await response?.text().catch(() => "")) || "";
    const sourceReadyAt = Date.now();
    let lower = `${finalUrl}\n${sourceBody}`.toLowerCase();
    let blockMarker = BLOCK_MARKERS.find((marker) => lower.includes(marker)) || null;
    let parsed = parseProducts(sourceBody, source);

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
        parsed = parseProducts(sourceBody || bodyText || html, source);
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
