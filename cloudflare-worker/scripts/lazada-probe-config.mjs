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

const officialSellerIds = String(process.env.LAZADA_OFFICIAL_SELLER_IDS || "1628720011")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);

const officialSellerNames = String(process.env.LAZADA_OFFICIAL_SELLER_NAMES || "Pokémon Store Online Singapore")
  .split(",")
  .map(normalizeSearchText)
  .filter(Boolean);

// SCRAPING_URL and SCRAPING_URL_2 are the two trusted Lazada listing feeds.
// Listing presence alone is NOT a stock signal: Lazada keeps sold-out products in
// listItems. Stock is derived from explicit fields first, with the out-of-stock
// badge and query-string stock value used only as defensive fallbacks.
// Products are restricted to the official Pokémon Store Online Singapore seller.
// SCRAPING_URL_3 remains disabled because its stock semantics are not trusted.
export const scrapingSources = [
  {
    name: "SCRAPING_URL",
    url: String(process.env.SCRAPING_URL || "").trim(),
    collectAllLists: false,
    keywords: tcgKeywords,
    sellerIds: officialSellerIds,
    sellerNames: officialSellerNames,
  },
  {
    name: "SCRAPING_URL_2",
    url: String(process.env.SCRAPING_URL_2 || "").trim(),
    collectAllLists: false,
    keywords: tcgKeywords,
    sellerIds: officialSellerIds,
    sellerNames: officialSellerNames,
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
