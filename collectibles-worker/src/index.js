import { opportunityScore, clamp } from "./scoring.js";
import {
  detectGames,
  extractLocationHint,
  extractProductsFromHtml,
  extractTimingHint,
  fetchText,
  loadSources,
  reprintRiskScore,
  stripHtml,
  urgencyScore,
} from "./sources.js";

const MAX_EVENTS = 120;
const MAX_OPPORTUNITIES = 100;
const MAX_MARKET_CACHE = 500;
const DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS = 900;
const DEFAULT_ALERT_COOLDOWN_SECONDS = 6 * 60 * 60;
const DEFAULT_USD_SGD = 1.30;
const DEFAULT_MARKET_CACHE_SECONDS = 6 * 60 * 60;
const DEFAULT_MARKET_NEGATIVE_CACHE_SECONDS = 15 * 60;
const DEFAULT_MAX_MARKET_LOOKUPS_PER_RUN = 24;
let lastPriceChartingRequestAt = 0;

function nowIso() { return new Date().toISOString(); }
function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}
function asInt(value, fallback, min = 1, max = Number.MAX_SAFE_INTEGER) {
  const n = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
}
function asNumber(value, fallback) {
  if (value === null || value === undefined || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}
function asBool(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  const v = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(v)) return true;
  if (["0", "false", "no", "off"].includes(v)) return false;
  return fallback;
}
function safeString(value, max = 500) { return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max); }
function bearerToken(request) {
  const match = (request.headers.get("authorization") || "").match(/^Bearer\s+(.+)$/i);
  return match ? match[1] : "";
}
function constantTimeEqual(a, b) {
  const left = String(a || ""); const right = String(b || "");
  if (!left || !right || left.length !== right.length) return false;
  let diff = 0;
  for (let i = 0; i < left.length; i += 1) diff |= left.charCodeAt(i) ^ right.charCodeAt(i);
  return diff === 0;
}
function hashString(text) {
  let hash = 2166136261;
  for (const ch of String(text || "").slice(0, 250000)) {
    hash ^= ch.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}
function canonicalName(value) {
  return safeString(value, 180)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\b(pre order|preorder|new|sale|offer|singapore|sg)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
function sourceHealth(source, state = {}) {
  return {
    id: source.id,
    name: source.name,
    kind: source.kind,
    status: state.consecutiveFailures ? "degraded" : state.lastSuccessAt ? "ok" : "unknown",
    lastCheckAt: state.lastCheckAt || null,
    lastSuccessAt: state.lastSuccessAt || null,
    consecutiveFailures: state.consecutiveFailures || 0,
    nextDueAt: state.nextDueAt || null,
    lastError: state.lastError || null,
    observations: state.observations || 0,
  };
}

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

async function queryTcgApi(env, productName, games) {
  if (!env.TCG_API_KEY) return null;
  const { q, game } = buildMarketQuery(productName, games);
  if (!q || q.length < 2 || !game) return null;
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
    } catch { /* history is optional */ }
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

async function queryPriceCharting(env, productName) {
  if (!env.PRICECHARTING_TOKEN) return null;
  const waitMs = Math.max(0, 1100 - (Date.now() - lastPriceChartingRequestAt));
  if (waitMs) await new Promise((resolve) => setTimeout(resolve, waitMs));
  lastPriceChartingRequestAt = Date.now();
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

const TCG_MARKET_GAMES = new Set(["pokemon", "one-piece", "magic", "lorcana", "yugioh", "digimon", "star-wars-unlimited", "flesh-and-blood", "riftbound"]);
async function queryMarket(env, productName, games) {
  if (games.some((g) => TCG_MARKET_GAMES.has(g))) {
    const tcg = await queryTcgApi(env, productName, games);
    if (tcg?.marketUsd) return tcg;
  }
  const pc = await queryPriceCharting(env, productName);
  if (pc?.marketUsd) return pc;
  return null;
}

async function fetchXPosts(env, account, sinceId = null) {
  if (!env.X_BEARER_TOKEN || !account?.username) return [];
  const auth = { authorization: `Bearer ${env.X_BEARER_TOKEN}` };
  const userResp = await fetch(`https://api.x.com/2/users/by/username/${encodeURIComponent(account.username)}`, { headers: auth });
  if (!userResp.ok) throw new Error(`X user lookup HTTP ${userResp.status}`);
  const user = await userResp.json();
  const id = user?.data?.id;
  if (!id) return [];
  const params = new URLSearchParams({ max_results: "10", exclude: "retweets,replies", "tweet.fields": "created_at,public_metrics,entities" });
  if (sinceId) params.set("since_id", sinceId);
  const postResp = await fetch(`https://api.x.com/2/users/${id}/tweets?${params}`, { headers: auth });
  if (!postResp.ok) throw new Error(`X posts HTTP ${postResp.status}`);
  const payload = await postResp.json();
  return (payload.data || []).map((p) => ({
    id: p.id,
    text: p.text || "",
    createdAt: p.created_at || nowIso(),
    url: `https://x.com/${account.username}/status/${p.id}`,
    metrics: p.public_metrics || {},
    source: account.name || `@${account.username}`,
    location: account.location || "Singapore",
  }));
}

function loadXAccounts(env) {
  if (!env.X_ACCOUNTS_JSON) return [];
  try {
    const rows = JSON.parse(env.X_ACCOUNTS_JSON);
    return Array.isArray(rows) ? rows.filter((x) => x?.username).slice(0, 100) : [];
  } catch { return []; }
}

async function sendTelegram(env, alert) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) return { skipped: true };
  const s = alert.scoring || {};
  const heading = alert.signalType === "SUPPLY"
    ? "📦 SUPPLY SIGNAL"
    : alert.signalType === "DROP" && s.action === "PASS"
      ? "🚨 DROP SIGNAL"
      : s.action === "BUY" ? "🔥 BUY OPPORTUNITY" : "👀 WATCH";
  const lines = [`${heading} · Score ${s.score ?? 0}/100`, alert.name, `Source: ${alert.sourceName}`];
  if (alert.location) lines.push(`Where: ${alert.location}`);
  if (alert.timingHint) lines.push(`When: ${alert.timingHint}`);
  if (alert.retailSgd) lines.push(`Retail: S$${alert.retailSgd.toFixed(2)}`);
  if (alert.marketSgd) lines.push(`Market est.: S$${alert.marketSgd.toFixed(2)}`);
  if (s.netMarginPct !== null && s.netMarginPct !== undefined) lines.push(`Est. net margin: ${s.netMarginPct}% (gross ${s.grossMarginPct}%)`);
  lines.push(`Demand ${s.demandScore ?? 0}/100 · Dead inventory risk ${s.deadInventoryRisk ?? 0}/100`);
  if (alert.market?.sales30d !== null && alert.market?.sales30d !== undefined) lines.push(`30d sales velocity: ${alert.market.sales30d}`);
  if (alert.market?.totalListings !== null && alert.market?.totalListings !== undefined) lines.push(`Active market listings: ${alert.market.totalListings}`);
  if (alert.market?.provider) lines.push(`Market data: ${alert.market.provider}`);
  if (alert.reason?.length) lines.push(`Why: ${alert.reason.slice(0, 4).join("; ")}`);
  if (alert.url) lines.push(alert.url);

  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHANNEL_ID, text: lines.join("\n"), disable_web_page_preview: false }),
  });
  if (!resp.ok) throw new Error(`Telegram HTTP ${resp.status}: ${(await resp.text()).slice(0, 180)}`);
  return { skipped: false };
}

function scoringConfig(env) {
  return {
    usdSgd: asNumber(env.USD_SGD_RATE, DEFAULT_USD_SGD),
    minNet: asNumber(env.MIN_NET_MARGIN_PCT, 22),
    minDemand: asNumber(env.MIN_DEMAND_SCORE, 62),
    minBuy: asNumber(env.MIN_BUY_SCORE, 76),
    minWatch: asNumber(env.MIN_WATCH_SCORE, 58),
    platformFee: asNumber(env.SELL_PLATFORM_FEE_PCT, 4),
    shipping: asNumber(env.SELL_SHIPPING_SGD, 4.5),
    riskBuffer: asNumber(env.SELL_RISK_BUFFER_PCT, 5),
  };
}

function rankRows(rows) {
  return [...rows].sort((a, b) => {
    const actionWeight = { BUY: 3, WATCH: 2, PASS: 1 };
    const aw = actionWeight[a?.scoring?.action] || 0;
    const bw = actionWeight[b?.scoring?.action] || 0;
    if (aw !== bw) return bw - aw;
    const scoreDiff = Number(b?.scoring?.score || 0) - Number(a?.scoring?.score || 0);
    if (scoreDiff) return scoreDiff;
    return Date.parse(b?.observedAt || 0) - Date.parse(a?.observedAt || 0);
  });
}

export class CollectiblesMonitor {
  constructor(state, env) { this.state = state; this.env = env; }

  async load() {
    const [meta, sourceStates, opportunities, alerts, marketCache] = await Promise.all([
      this.state.storage.get("meta"),
      this.state.storage.get("sourceStates"),
      this.state.storage.get("opportunities"),
      this.state.storage.get("alerts"),
      this.state.storage.get("marketCache"),
    ]);
    return {
      meta: meta || { recentEvents: [], lastCheckAt: null, lastSuccessAt: null, consecutiveFailures: 0 },
      sourceStates: sourceStates || {},
      opportunities: opportunities || [],
      alerts: alerts || {},
      marketCache: marketCache || {},
      marketLookupsThisRun: 0,
      marketBudgetExhausted: false,
    };
  }

  log(meta, event, fields = {}) {
    const row = { ts: nowIso(), event, ...fields };
    console.log(JSON.stringify(row));
    meta.recentEvents = [...(meta.recentEvents || []), row].slice(-MAX_EVENTS);
  }

  async persist(data) { await this.state.storage.put(data); }

  async marketLookup(productName, games, snapshot) {
    const key = hashString(`${canonicalName(productName)}|${[...games].sort().join(",")}`);
    const cache = snapshot.marketCache || (snapshot.marketCache = {});
    const positiveTtlMs = asInt(this.env.MARKET_CACHE_SECONDS, DEFAULT_MARKET_CACHE_SECONDS, 900, 7 * 86400) * 1000;
    const negativeTtlMs = asInt(this.env.MARKET_NEGATIVE_CACHE_SECONDS, DEFAULT_MARKET_NEGATIVE_CACHE_SECONDS, 60, positiveTtlMs / 1000) * 1000;
    const cached = cache[key];
    const ttlMs = cached?.data ? positiveTtlMs : negativeTtlMs;
    if (cached?.at && Date.now() - Date.parse(cached.at) < ttlMs) return cached.data || null;

    const maxLookups = asInt(this.env.MAX_MARKET_LOOKUPS_PER_RUN, DEFAULT_MAX_MARKET_LOOKUPS_PER_RUN, 1, 200);
    if (snapshot.marketLookupsThisRun >= maxLookups) {
      snapshot.marketBudgetExhausted = true;
      return null;
    }
    snapshot.marketLookupsThisRun += 1;

    const data = await queryMarket(this.env, productName, games);
    cache[key] = { at: nowIso(), data };
    const entries = Object.entries(cache).sort((a, b) => Date.parse(b[1]?.at || 0) - Date.parse(a[1]?.at || 0));
    snapshot.marketCache = Object.fromEntries(entries.slice(0, MAX_MARKET_CACHE));
    return data;
  }

  scoreInput(overrides = {}) {
    const cfg = scoringConfig(this.env);
    return {
      platformFeePct: cfg.platformFee,
      shippingSgd: cfg.shipping,
      riskBufferPct: cfg.riskBuffer,
      minNetMarginPct: cfg.minNet,
      minDemandScore: cfg.minDemand,
      minBuyScore: cfg.minBuy,
      minWatchScore: cfg.minWatch,
      ...overrides,
    };
  }

  async maybeAlert(row, snapshot, allowSignalOnly = false) {
    const cooldown = asInt(this.env.ALERT_COOLDOWN_SECONDS, DEFAULT_ALERT_COOLDOWN_SECONDS, 300, 7 * 86400) * 1000;
    const prior = snapshot.alerts[row.id];
    const canAlert = !prior || Date.now() - Date.parse(prior) >= cooldown;
    const actionable = row.scoring?.action === "BUY" || row.scoring?.action === "WATCH";
    const signalOnly = allowSignalOnly && row.signalType && (row.scoring?.urgencyScore >= 44 || row.supplyRisk >= 44);
    if ((actionable || signalOnly) && canAlert) {
      await sendTelegram(this.env, row);
      snapshot.alerts[row.id] = nowIso();
      this.log(snapshot.meta, "telegram.sent", { action: row.scoring?.action, signalType: row.signalType || null, score: row.scoring?.score, name: row.name, sourceId: row.sourceId });
    }
  }

  async processRetailProduct(source, product, pageText, snapshot) {
    const name = safeString(product.name, 180);
    if (!name) return null;
    const games = [...new Set([...(source.games || []), ...detectGames(`${name} ${pageText.slice(0, 12000)}`)])];
    if (!games.length || (games.length === 1 && games[0] === "collectibles")) return null;

    let market = null;
    try { market = await this.marketLookup(name, games, snapshot); } catch (error) {
      this.log(snapshot.meta, "market.lookup.error", { sourceId: source.id, name, message: safeString(error.message) });
    }

    const cfg = scoringConfig(this.env);
    const marketSgd = market?.marketUsd ? market.marketUsd * cfg.usdSgd : null;
    const text = `${name} ${pageText.slice(0, 30000)}`;
    const urgency = urgencyScore(text);
    const reprintRisk = reprintRiskScore(text);
    const socialHeat = Math.min(100, urgency * 0.7 + (source.kind === "community" ? 20 : 0));
    const confidence = marketSgd && product.priceSgd ? 88 : product.priceSgd ? 58 : 45;

    const scoring = opportunityScore(this.scoreInput({
      retailSgd: product.priceSgd,
      marketSgd,
      sales30d: market?.sales30d,
      priceChange7d: market?.priceChange7d,
      priceChange30d: market?.priceChange30d,
      totalListings: market?.totalListings,
      socialHeat,
      retailerSelloutHeat: /out of stock|unavailable|sold out/i.test(pageText) ? 60 : 20,
      urgencyScore: urgency,
      confidenceScore: confidence,
      reprintRisk,
      supplyBreadth: 0,
    }));

    const reason = [];
    if (scoring.netMarginPct !== null) reason.push(`${scoring.netMarginPct}% est. net margin`);
    if (market?.sales30d !== null && market?.sales30d !== undefined) reason.push(`${market.sales30d} market sales in 30d`);
    if (urgency >= 35) reason.push("time-sensitive drop/restock language");
    if (market?.priceChange7d > 8) reason.push(`market +${market.priceChange7d}% / 7d`);
    if (reprintRisk >= 35) reason.push("reprint/supply expansion risk detected");

    const row = {
      id: hashString(`${source.id}|${canonicalName(name)}|${product.priceSgd}|${marketSgd}`),
      observedAt: nowIso(), name, games, sourceId: source.id, sourceName: source.name,
      sourceKind: source.kind, location: extractLocationHint(text, source.location || null), timingHint: extractTimingHint(text),
      url: product.url || source.url, retailSgd: product.priceSgd || null, marketSgd, market, scoring, reason,
    };
    await this.maybeAlert(row, snapshot, false);
    return row;
  }

  async checkWebsiteSource(source, state, snapshot) {
    const result = await fetchText(source.url);
    const fingerprint = hashString(result.body);
    const text = stripHtml(result.body);
    const changed = Boolean(state.fingerprint && state.fingerprint !== fingerprint);
    const products = source.kind === "retailer" ? extractProductsFromHtml(result.body, result.finalUrl) : [];
    const games = detectGames(text);
    const urgency = urgencyScore(text);
    const reprintRisk = reprintRiskScore(text);
    const cfgStamp = hashString(JSON.stringify({
      ...scoringConfig(this.env),
      tcgApi: Boolean(this.env.TCG_API_KEY),
      priceCharting: Boolean(this.env.PRICECHARTING_TOKEN),
    }));
    const marketTtlMs = asInt(this.env.MARKET_CACHE_SECONDS, DEFAULT_MARKET_CACHE_SECONDS, 900, 7 * 86400) * 1000;
    const lastScoredMs = state.lastScoredAt ? Date.parse(state.lastScoredAt) : 0;
    const periodicRescore = !lastScoredMs || Date.now() - lastScoredMs >= marketTtlMs;
    const rescore = changed || !state.fingerprint || state.scoringConfigStamp !== cfgStamp || periodicRescore;

    const observations = [];
    if (rescore) {
      if (source.kind === "retailer") {
        for (const product of products.slice(0, 30)) {
          const row = await this.processRetailProduct(source, product, text, snapshot);
          if (row) observations.push(row);
        }
      } else if (games.length && (urgency > 0 || reprintRisk > 0)) {
        const scoring = opportunityScore(this.scoreInput({
          urgencyScore: urgency,
          socialHeat: urgency,
          confidenceScore: source.priority || 70,
          reprintRisk,
          scarcityScore: 50,
        }));
        const row = {
          id: hashString(`${source.id}|${fingerprint}`), observedAt: nowIso(), name: `${source.name} signal`, games,
          sourceId: source.id, sourceName: source.name, sourceKind: source.kind,
          signalType: reprintRisk >= urgency ? "SUPPLY" : "DROP",
          supplyRisk: reprintRisk,
          location: extractLocationHint(text, source.location || null), timingHint: extractTimingHint(text),
          url: result.finalUrl, retailSgd: null, marketSgd: null, market: null, scoring,
          reason: [urgency ? `drop urgency ${urgency}/100` : null, reprintRisk ? `supply/reprint risk ${reprintRisk}/100` : null].filter(Boolean),
        };
        observations.push(row);
        await this.maybeAlert(row, snapshot, true);
      }
    }

    return {
      fingerprint,
      scoringConfigStamp: cfgStamp,
      changed,
      rescore,
      rescoreComplete: !snapshot.marketBudgetExhausted,
      products: products.length,
      games,
      urgency,
      reprintRisk,
      observations,
      finalUrl: result.finalUrl,
    };
  }

  async checkXAccount(account, state, snapshot) {
    const posts = await fetchXPosts(this.env, account, state.lastPostId || null);
    const observations = [];
    const sorted = [...posts].sort((a, b) => String(a.id).localeCompare(String(b.id)));
    for (const post of sorted) {
      const games = detectGames(post.text);
      if (!games.length) continue;
      const urgency = urgencyScore(post.text);
      const scoring = opportunityScore(this.scoreInput({ urgencyScore: urgency, socialHeat: clamp(45 + urgency), confidenceScore: 82, scarcityScore: 55 }));
      const row = {
        id: hashString(`x|${post.id}`), observedAt: post.createdAt, name: safeString(post.text, 140), games,
        sourceId: `x:${account.username}`, sourceName: account.name || `@${account.username}`, sourceKind: "social", signalType: "DROP",
        location: extractLocationHint(post.text, account.location || "Singapore"), timingHint: extractTimingHint(post.text),
        url: post.url, retailSgd: null, marketSgd: null, market: null, scoring,
        reason: ["social drop signal", urgency ? `urgency ${urgency}/100` : null].filter(Boolean),
      };
      observations.push(row);
      await this.maybeAlert(row, snapshot, true);
    }
    return { observations, lastPostId: posts.map((p) => p.id).sort().pop() || state.lastPostId || null, posts: posts.length };
  }

  async ingestSocial(payload) {
    const snapshot = await this.load();
    const rows = Array.isArray(payload) ? payload : [payload];
    const observations = [];
    for (const item of rows.slice(0, 50)) {
      const text = safeString(item?.text || item?.caption || item?.title || "", 6000);
      if (!text) continue;
      const name = safeString(item?.productName || item?.title || text, 160);
      const games = [...new Set([...(Array.isArray(item?.games) ? item.games : []), ...detectGames(`${name} ${text}`)])];
      if (!games.length) continue;
      const urgency = urgencyScore(text);
      const reprintRisk = reprintRiskScore(text);
      let market = null;
      try { market = await this.marketLookup(name, games, snapshot); } catch (error) {
        this.log(snapshot.meta, "market.lookup.error", { sourceId: item?.sourceId || "social-ingest", name, message: safeString(error.message) });
      }
      const cfg = scoringConfig(this.env);
      const marketSgd = asNumber(item?.marketSgd, null) ?? (market?.marketUsd ? market.marketUsd * cfg.usdSgd : null);
      const retailSgd = asNumber(item?.retailSgd, null);
      const sales30d = asNumber(item?.sales30d, null) ?? market?.sales30d;
      const totalListings = asNumber(item?.totalListings, null) ?? market?.totalListings;
      const scoring = opportunityScore(this.scoreInput({
        retailSgd, marketSgd,
        sales30d,
        priceChange7d: asNumber(item?.priceChange7d, null) ?? market?.priceChange7d,
        priceChange30d: asNumber(item?.priceChange30d, null) ?? market?.priceChange30d,
        totalListings,
        carousellInterest: asNumber(item?.carousellInterest, null),
        socialHeat: clamp(asNumber(item?.socialHeat, 45 + urgency)),
        retailerSelloutHeat: clamp(asNumber(item?.retailerSelloutHeat, 30)),
        urgencyScore: urgency,
        confidenceScore: clamp(asNumber(item?.confidenceScore, marketSgd && retailSgd ? 88 : 75)),
        reprintRisk,
        supplyBreadth: asNumber(item?.supplyBreadth, 0),
      }));
      const row = {
        id: hashString(`ingest|${item?.id || item?.url || text}|${retailSgd}|${marketSgd}`),
        observedAt: item?.publishedAt || nowIso(), name, games,
        sourceId: safeString(item?.sourceId || "social-ingest", 80),
        sourceName: safeString(item?.sourceName || item?.platform || "Social ingest", 100),
        sourceKind: "social", signalType: reprintRisk > urgency ? "SUPPLY" : "DROP", supplyRisk: reprintRisk,
        location: extractLocationHint(text, item?.location || "Singapore"), timingHint: item?.timingHint || extractTimingHint(text),
        url: item?.url || null, retailSgd, marketSgd, market: market ? { ...market, sales30d, totalListings } : null, scoring,
        reason: ["social/drop signal", scoring.netMarginPct !== null ? `${scoring.netMarginPct}% est. net margin` : null, urgency ? `urgency ${urgency}/100` : null, reprintRisk ? `supply risk ${reprintRisk}/100` : null].filter(Boolean),
      };
      observations.push(row);
      await this.maybeAlert(row, snapshot, true);
    }
    snapshot.opportunities = rankRows([...observations, ...(snapshot.opportunities || [])])
      .filter((x, i, rows2) => rows2.findIndex((y) => y.id === x.id) === i)
      .slice(0, MAX_OPPORTUNITIES);
    this.log(snapshot.meta, "social.ingest", { received: rows.length, observations: observations.length });
    await this.persist({ meta: snapshot.meta, opportunities: snapshot.opportunities, alerts: snapshot.alerts, marketCache: snapshot.marketCache });
    return { ok: true, received: rows.length, observations: observations.length };
  }

  async run(trigger = "cron") {
    const snapshot = await this.load();
    const { meta, sourceStates } = snapshot;
    meta.lastCheckAt = nowIso();
    this.log(meta, "monitor.check.start", { trigger });
    const sources = loadSources(this.env);
    let checked = 0;
    let successes = 0;
    const newOpportunities = [];

    for (const source of sources) {
      const state = sourceStates[source.id] || {};
      if (state.nextDueAt && Date.now() < Date.parse(state.nextDueAt)) continue;
      checked += 1;
      state.lastCheckAt = nowIso();
      try {
        const result = await this.checkWebsiteSource(source, state, snapshot);
        state.lastSuccessAt = nowIso();
        state.consecutiveFailures = 0;
        state.lastError = null;
        state.fingerprint = result.fingerprint;
        state.scoringConfigStamp = result.scoringConfigStamp;
        if (result.rescore && result.rescoreComplete) state.lastScoredAt = nowIso();
        state.observations = Number(state.observations || 0) + result.observations.length;
        state.nextDueAt = new Date(Date.now() + source.intervalSeconds * 1000).toISOString();
        successes += 1;
        newOpportunities.push(...result.observations);
        this.log(meta, "source.fetch.ok", {
          sourceId: source.id, kind: source.kind, changed: result.changed, rescore: result.rescore,
          products: result.products, games: result.games, urgency: result.urgency, reprintRisk: result.reprintRisk,
        });
      } catch (error) {
        state.consecutiveFailures = Number(state.consecutiveFailures || 0) + 1;
        state.lastError = safeString(error.message);
        const backoff = Math.min(6 * 3600, DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS * 2 ** Math.min(state.consecutiveFailures - 1, 4));
        state.nextDueAt = new Date(Date.now() + backoff * 1000).toISOString();
        this.log(meta, "source.fetch.error", { sourceId: source.id, failures: state.consecutiveFailures, message: state.lastError, backoffSeconds: backoff });
      }
      sourceStates[source.id] = state;
    }

    for (const account of loadXAccounts(this.env)) {
      const key = `x:${account.username}`;
      const state = sourceStates[key] || {};
      const interval = Math.max(60, Number(account.intervalSeconds || 180));
      if (state.nextDueAt && Date.now() < Date.parse(state.nextDueAt)) continue;
      checked += 1;
      state.lastCheckAt = nowIso();
      try {
        const result = await this.checkXAccount(account, state, snapshot);
        state.lastSuccessAt = nowIso(); state.consecutiveFailures = 0; state.lastError = null;
        state.lastPostId = result.lastPostId; state.observations = Number(state.observations || 0) + result.observations.length;
        state.nextDueAt = new Date(Date.now() + interval * 1000).toISOString();
        successes += 1; newOpportunities.push(...result.observations);
        this.log(meta, "source.x.ok", { sourceId: key, posts: result.posts, observations: result.observations.length });
      } catch (error) {
        state.consecutiveFailures = Number(state.consecutiveFailures || 0) + 1;
        state.lastError = safeString(error.message);
        const backoff = Math.min(6 * 3600, DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS * 2 ** Math.min(state.consecutiveFailures - 1, 4));
        state.nextDueAt = new Date(Date.now() + backoff * 1000).toISOString();
        this.log(meta, "source.x.error", { sourceId: key, message: state.lastError, backoffSeconds: backoff });
      }
      sourceStates[key] = state;
    }

    meta.consecutiveFailures = checked && !successes ? Number(meta.consecutiveFailures || 0) + 1 : 0;
    if (successes) meta.lastSuccessAt = nowIso();
    meta.lastRun = {
      trigger, checked, successes, newOpportunities: newOpportunities.length,
      marketLookups: snapshot.marketLookupsThisRun, marketBudgetExhausted: snapshot.marketBudgetExhausted,
    };

    snapshot.opportunities = rankRows([...newOpportunities, ...(snapshot.opportunities || [])])
      .filter((x, i, rows) => rows.findIndex((y) => y.id === x.id) === i)
      .slice(0, MAX_OPPORTUNITIES);
    this.log(meta, "monitor.check.complete", meta.lastRun);
    await this.persist({ meta, sourceStates, opportunities: snapshot.opportunities, alerts: snapshot.alerts, marketCache: snapshot.marketCache });
    return meta.lastRun;
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/run") return json(await this.run("manual"));
    if (request.method === "POST" && url.pathname === "/ingest") return json(await this.ingestSocial(await request.json()));
    if (request.method === "GET" && url.pathname === "/healthz") {
      const data = await this.load();
      const sources = loadSources(this.env);
      const xAccounts = loadXAccounts(this.env);
      const healthRows = [
        ...sources.map((s) => sourceHealth(s, data.sourceStates[s.id])),
        ...xAccounts.map((a) => sourceHealth({ id: `x:${a.username}`, name: a.name || `@${a.username}`, kind: "social" }, data.sourceStates[`x:${a.username}`])),
      ];
      const stale = !data.meta.lastSuccessAt || Date.now() - Date.parse(data.meta.lastSuccessAt) > 2 * 3600 * 1000;
      const degraded = Number(data.meta.consecutiveFailures || 0) > 0 || stale;
      return json({
        status: degraded ? "degraded" : "ok",
        lastCheckAt: data.meta.lastCheckAt || null,
        lastSuccessAt: data.meta.lastSuccessAt || null,
        lastRun: data.meta.lastRun || null,
        sources: {
          total: healthRows.length,
          ok: healthRows.filter((x) => x.status === "ok").length,
          degraded: healthRows.filter((x) => x.status === "degraded").length,
          unknown: healthRows.filter((x) => x.status === "unknown").length,
        },
        topOpportunity: data.opportunities?.[0] || null,
      });
    }
    if (request.method === "GET" && url.pathname === "/debug") {
      const data = await this.load();
      const sources = loadSources(this.env);
      const x = loadXAccounts(this.env).map((a) => ({ id: `x:${a.username}`, name: a.name || `@${a.username}`, kind: "social" }));
      const cfg = scoringConfig(this.env);
      return json({
        health: {
          lastCheckAt: data.meta.lastCheckAt || null,
          lastSuccessAt: data.meta.lastSuccessAt || null,
          consecutiveFailures: data.meta.consecutiveFailures || 0,
          lastRun: data.meta.lastRun || null,
        },
        config: {
          websiteSources: sources.length,
          xAccounts: x.length,
          tcgApiEnabled: Boolean(this.env.TCG_API_KEY),
          tcgHistoryEnabled: asBool(this.env.TCG_API_HISTORY_ENABLED, false),
          priceChartingEnabled: Boolean(this.env.PRICECHARTING_TOKEN),
          socialIngestEnabled: Boolean(this.env.INGEST_TOKEN || this.env.DEBUG_TOKEN),
          minNetMarginPct: cfg.minNet,
          minDemandScore: cfg.minDemand,
          minBuyScore: cfg.minBuy,
          minWatchScore: cfg.minWatch,
          usdSgdRate: cfg.usdSgd,
          marketCacheSeconds: asInt(this.env.MARKET_CACHE_SECONDS, DEFAULT_MARKET_CACHE_SECONDS, 900, 7 * 86400),
          marketNegativeCacheSeconds: asInt(this.env.MARKET_NEGATIVE_CACHE_SECONDS, DEFAULT_MARKET_NEGATIVE_CACHE_SECONDS, 60, 21600),
          maxMarketLookupsPerRun: asInt(this.env.MAX_MARKET_LOOKUPS_PER_RUN, DEFAULT_MAX_MARKET_LOOKUPS_PER_RUN, 1, 200),
          marketCacheEntries: Object.keys(data.marketCache || {}).length,
          persistence: "Durable Object SQLite-backed storage",
          d1Enabled: false,
        },
        sources: [...sources, ...x].map((s) => sourceHealth(s, data.sourceStates[s.id])),
        opportunities: rankRows(data.opportunities || []),
        recentEvents: data.meta.recentEvents || [],
      });
    }
    return json({ error: "not_found" }, 404);
  }
}

function stub(env) {
  const id = env.COLLECTIBLES_MONITOR.idFromName("sg-collectibles-market-intel");
  return env.COLLECTIBLES_MONITOR.get(id);
}
function authorized(request, env) { return Boolean(env.DEBUG_TOKEN) && constantTimeEqual(bearerToken(request), env.DEBUG_TOKEN); }
function ingestAuthorized(request, env) {
  const token = env.INGEST_TOKEN || env.DEBUG_TOKEN;
  return Boolean(token) && constantTimeEqual(bearerToken(request), token);
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(stub(env).fetch("https://internal/run", { method: "POST" }));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/") {
      return json({
        service: "sg-collectibles-market-intel",
        health: "/healthz",
        debug: "/debug (Bearer token)",
        manualRun: "/run (POST, Bearer token)",
        socialIngest: "/ingest (POST, Bearer token)",
      });
    }
    if (request.method === "GET" && url.pathname === "/healthz") return stub(env).fetch("https://internal/healthz");
    if (request.method === "POST" && url.pathname === "/ingest") {
      if (!ingestAuthorized(request, env)) return json({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      return stub(env).fetch("https://internal/ingest", { method: "POST", headers: { "content-type": "application/json" }, body: await request.text() });
    }
    if (["/debug", "/run"].includes(url.pathname)) {
      if (!authorized(request, env)) return json({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      return stub(env).fetch(`https://internal${url.pathname}`, { method: request.method });
    }
    return json({ error: "not_found" }, 404);
  },
};
