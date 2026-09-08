import { asNumber, safeString } from "../../core/utils.js";

let lastRequestAt = 0;

async function query(env, productName) {
  if (!env.PRICECHARTING_TOKEN) return null;
  const waitMs = Math.max(0, 1100 - (Date.now() - lastRequestAt));
  if (waitMs) await new Promise((resolve) => setTimeout(resolve, waitMs));
  lastRequestAt = Date.now();

  const q = safeString(productName, 120);
  if (q.length < 2) return null;
  const params = new URLSearchParams({ t: env.PRICECHARTING_TOKEN, q });
  const response = await fetch(`https://www.pricecharting.com/api/product?${params}`);
  if (!response.ok) throw new Error(`PriceCharting HTTP ${response.status}`);
  const row = await response.json();
  if (row?.status !== "success" || !row["product-name"]) return null;

  const newPriceCents = asNumber(row["new-price"], null);
  const loosePriceCents = asNumber(row["loose-price"], null);
  const salesYear = asNumber(row["sales-volume"], null);
  return {
    provider: "pricecharting.com",
    id: row.id || null,
    name: row["product-name"],
    category: row["console-name"] || row.genre || null,
    productType: "Collectible",
    marketUsd: newPriceCents !== null ? newPriceCents / 100 : (loosePriceCents !== null ? loosePriceCents / 100 : null),
    lowUsd: null,
    medianUsd: null,
    priceChange7d: null,
    priceChange30d: null,
    totalListings: null,
    sales30d: salesYear !== null ? Math.round((salesYear / 12) * 10) / 10 : null,
    salesYear,
  };
}

export const priceChartingProvider = {
  id: "pricecharting.com",
  supports(env) { return Boolean(env.PRICECHARTING_TOKEN); },
  query,
};
