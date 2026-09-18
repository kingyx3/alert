import path from "node:path";
import { normalizeSearchText } from "./lazada-product-parser.mjs";

export const BLOCK_MARKERS = [
  "captcha",
  "security check",
  "verify you are human",
  "access denied",
  "unusual traffic",
  "robot check",
  "are you a robot",
];

const tcgKeywords = String(process.env.TCG_KEYWORDS || "pokemon,pokémon,tcg,trading card")
  .split(",")
  .map(normalizeSearchText)
  .filter(Boolean);

// These two endpoints are Lazada product-listing feeds: products that are present
// in the listing are treated as available when Lazada omits an explicit stock
// field. Any explicit sold-out/out-of-stock signal still wins in the parser.
// SCRAPING_URL_3 remains disabled because its stock semantics are not trusted.
export const scrapingSources = [
  {
    name: "SCRAPING_URL",
    url: String(process.env.SCRAPING_URL || "").trim(),
    collectAllLists: false,
    listedMeansInStock: true,
    keywords: tcgKeywords,
  },
  {
    name: "SCRAPING_URL_2",
    url: String(process.env.SCRAPING_URL_2 || "").trim(),
    collectAllLists: false,
    listedMeansInStock: true,
    keywords: tcgKeywords,
  },
];

export const monitorUrl = String(process.env.MONITOR_URL || "").replace(/\/$/, "");
export const debugToken = process.env.DEBUG_TOKEN || "";
export const ingestEnabled = String(process.env.INGEST_ENABLED || "false").toLowerCase() === "true";
export const batchId = process.env.BATCH_ID || `local-${Date.now()}`;
export const runnerSlot = process.env.PROBE_SLOT || "1";
export const artifactsDir = path.resolve(process.env.PROBE_ARTIFACT_DIR || `probe-artifacts-${runnerSlot}`);

const missingSources = scrapingSources.filter((source) => !source.url).map((source) => source.name);
if (missingSources.length) throw new Error(`${missingSources.join("/")} are not configured`);
if (ingestEnabled && (!monitorUrl || !debugToken)) {
  throw new Error("MONITOR_URL/DEBUG_TOKEN are required when INGEST_ENABLED=true");
}
