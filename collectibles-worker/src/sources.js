// Backward-compatible barrel. New code should import the focused modules directly.
export { DEFAULT_SOURCES, loadSources } from "./sources/index.js";
export {
  SG_LOCATION_TERMS,
  detectGames,
  extractLocationHint,
  extractTimingHint,
  normalize,
  reprintRiskScore,
  stripHtml,
  termScore,
  urgencyScore,
} from "./sources/detection.js";
export { extractProductsFromHtml, fetchText, parseProducts, PRODUCT_PARSERS } from "./sources/web.js";
