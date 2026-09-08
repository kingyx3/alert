import { asBool, asNumber, canonicalName, safeString } from "../../core/utils.js";

export const TCG_MARKET_GAMES = new Set([
  "pokemon", "one-piece", "magic", "lorcana", "yugioh", "digimon",
  "star-wars-unlimited", "flesh-and-blood", "riftbound",
]);

export function buildMarketQuery(name, games = []) {
  const cleaned = safeString(name, 120)
    .replace(/\b(?:takara tomy|pokemon tcg|one piece card game|magic: the gathering)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  const gameMap = {
    pokemon: "pokemon",
    "one-piece": "one-piece",
    magic: "magic",
    lorcana: "lorcana",
    yugioh: "yugioh",
    digimon: "digimon",
    "star-wars-unlimited": "star-wars-unlimited",
    "flesh-and-blood": "flesh-and-blood",
    riftbound: "riftbound",
  };
  const game = games.map((g) => gameMap[g]).find(Boolean) || null;
  return { q: cleaned || name, game };
}

function commonWordScore(a, b) {
  const aa = new Set(String(a).split(" ").filter((x) => x.length > 2));
  const bb = new Set(String(b).split(" ").filter((x) => x.length > 2));
  let hits = 0;
  for (const word of aa) if (bb.has(word)) hits += 1;
  return hits / Math.max(1, aa.size);
}

async function query(env, productName, games) {
  const { q, game } = buildMarketQuery(productName, games);
  if (!q || q.length < 2 || !game || !env.TCG_API_KEY) return null;
  const params = new URLSearchParams({ q, per_page: "8", sort: "relevance", game, type: "Sealed Products" });
  const headers = { "X-API-Key": env.TCG_API_KEY };
  let response = await fetch(`https://api.tcgapi.dev/v1/search?${params}`, { headers });
  if (!response.ok) throw new Error(`TCG API search HTTP ${response.status}`);
  let payload = await response.json();
  let rows = Array.isArray(payload.data) ? payload.data : [];

  if (!rows.length) {
    params.delete("type");
    response = await fetch(`https://api.tcgapi.dev/v1/search?${params}`, { headers });
    if (!response.ok) throw new Error(`TCG API search HTTP ${response.status}`);
    payload = await response.json();
    rows = Array.isArray(payload.data) ? payload.data : [];
  }
  if (!rows.length) return null;

  const target = canonicalName(productName);
  rows.sort((a, b) => {
    const aName = canonicalName(a.name);
    const bName = canonicalName(b.name);
    const aScore = target && aName ? (aName.includes(target) || target.includes(aName) ? 3 : 0) + commonWordScore(target, aName) : 0;
    const bScore = target && bName ? (bName.includes(target) || target.includes(bName) ? 3 : 0) + commonWordScore(target, bName) : 0;
    return bScore - aScore;
  });

  const best = rows[0];
  let sales30d = null;
  if (asBool(env.TCG_API_HISTORY_ENABLED, false) && best.id) {
    try {
      const historyResp = await fetch(`https://api.tcgapi.dev/v1/cards/${best.id}/history?range=month`, { headers });
      if (historyResp.ok) {
        const history = await historyResp.json();
        const points = Array.isArray(history.data) ? history.data : [];
        sales30d = points.reduce((sum, p) => sum + (Number(p.sales_volume) || 0), 0);
      }
    } catch { /* optional history should not fail the price lookup */ }
  }

  return {
    provider: "tcgapi.dev",
    id: best.id || null,
    name: best.name || productName,
    setName: best.set_name || best.set || null,
    game: best.game_slug || game || null,
    productType: best.product_type || null,
    marketUsd: asNumber(best.market_price ?? best.price, null),
    lowUsd: asNumber(best.low_price, null),
    medianUsd: asNumber(best.median_price, null),
    priceChange7d: asNumber(best.price_change_7d, null),
    priceChange30d: asNumber(best.price_change_30d, null),
    totalListings: asNumber(best.total_listings, null),
    sales30d,
  };
}

export const tcgApiProvider = {
  id: "tcgapi.dev",
  supports(env, _productName, games = []) {
    return Boolean(env.TCG_API_KEY) && games.some((game) => TCG_MARKET_GAMES.has(game));
  },
  query,
};
