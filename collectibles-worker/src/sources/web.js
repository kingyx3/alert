import { normalize, stripHtml } from "./detection.js";

function absoluteUrl(value, baseUrl) {
  try { return new URL(value, baseUrl).toString(); } catch { return baseUrl; }
}

function numericPrice(value) {
  const cleaned = String(value ?? "").replace(/,/g, "").match(/(?:s\$|sgd|\$)?\s*(\d{1,5}(?:\.\d{1,2})?)/i);
  if (!cleaned) return null;
  const n = Number(cleaned[1]);
  return Number.isFinite(n) && n > 0 && n < 100000 ? n : null;
}

function walkJsonLd(node, rows, baseUrl) {
  if (!node) return;
  if (Array.isArray(node)) {
    for (const item of node) walkJsonLd(item, rows, baseUrl);
    return;
  }
  if (typeof node !== "object") return;
  const type = node["@type"];
  if (type === "Product" || (Array.isArray(type) && type.includes("Product"))) {
    const offers = Array.isArray(node.offers) ? node.offers[0] : node.offers || {};
    const name = node.name || node.headline || "";
    const priceSgd = numericPrice(offers.price ?? offers.lowPrice ?? node.price);
    const url = absoluteUrl(node.url || offers.url || "", baseUrl);
    if (name) rows.push({ name: stripHtml(name), priceSgd, url });
  }
  for (const value of Object.values(node)) walkJsonLd(value, rows, baseUrl);
}

export function extractProductsFromHtml(html, baseUrl) {
  const body = String(html || "");
  const rows = [];

  for (const match of body.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)) {
    try { walkJsonLd(JSON.parse(match[1]), rows, baseUrl); } catch { /* malformed JSON-LD */ }
  }

  const anchors = [...body.matchAll(/<a\b[^>]*href=["']([^"']*(?:\/products\/|\/product\/)[^"']*)["'][^>]*>([\s\S]{0,1800}?)<\/a>/gi)].slice(0, 120);
  for (const [, href, inner] of anchors) {
    const text = stripHtml(inner);
    if (text.length < 3) continue;
    const priceSgd = numericPrice(text);
    const name = text.replace(/(?:s\$|sgd|\$)\s*\d[\d,.]*/gi, " ").replace(/\s+/g, " ").trim().slice(0, 180);
    if (name) rows.push({ name, priceSgd, url: absoluteUrl(href, baseUrl) });
  }

  const seen = new Set();
  return rows.filter((row) => {
    const key = `${normalize(row.name)}|${row.url}`;
    if (!row.name || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 150);
}

export async function fetchText(url) {
  const response = await fetch(url, {
    method: "GET",
    redirect: "follow",
    headers: {
      "user-agent": "kingyx3-collectibles-monitor/1.0 (+https://github.com/kingyx3/alert)",
      accept: "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.7",
      "accept-language": "en-SG,en;q=0.9",
    },
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`Source HTTP ${response.status}`);
  if (body.length < 80) throw new Error("Source response was unexpectedly small");
  return { body, status: response.status, finalUrl: response.url || url, contentType: response.headers.get("content-type") || "" };
}

// Parser registry keeps retailer-specific parsing out of the monitor core.
export const PRODUCT_PARSERS = {
  generic: extractProductsFromHtml,
};

export function parseProducts(source, html, baseUrl) {
  const parser = PRODUCT_PARSERS[source.parser || "generic"] || PRODUCT_PARSERS.generic;
  return parser(html, baseUrl);
}
