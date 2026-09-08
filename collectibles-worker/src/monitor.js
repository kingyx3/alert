import { opportunityScore, clamp } from "./scoring.js";
import {
  MAX_EVENTS,
  MAX_OPPORTUNITIES,
  MAX_MARKET_CACHE,
  DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS,
  DEFAULT_ALERT_COOLDOWN_SECONDS,
  DEFAULT_MARKET_CACHE_SECONDS,
  DEFAULT_MARKET_NEGATIVE_CACHE_SECONDS,
  DEFAULT_MAX_MARKET_LOOKUPS_PER_RUN,
  scoringConfig,
  sourceHealth,
} from "./core/config.js";
import { asBool, asInt, asNumber, canonicalName, hashString, json, nowIso, safeString } from "./core/utils.js";
import { MARKET_PROVIDERS, queryMarket } from "./market/index.js";
import { sendTelegram } from "./notifications/telegram.js";
import { loadSnapshot, persistSnapshot } from "./storage/state.js";
import { loadSources } from "./sources/index.js";
import { detectGames, extractLocationHint, extractTimingHint, reprintRiskScore, stripHtml, urgencyScore } from "./sources/detection.js";
import { fetchText, parseProducts } from "./sources/web.js";
import { loadSocialSources } from "./social/index.js";

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

function sourceBackoffSeconds(failures) {
  return Math.min(6 * 3600, DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS * 2 ** Math.min(Math.max(0, failures - 1), 4));
}

export class CollectiblesMonitor {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async load() { return loadSnapshot(this.state); }
  async persist(data) { return persistSnapshot(this.state, data); }

  log(meta, event, fields = {}) {
    const row = { ts: nowIso(), event, ...fields };
    console.log(JSON.stringify(row));
    meta.recentEvents = [...(meta.recentEvents || []), row].slice(-MAX_EVENTS);
  }

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
      this.log(snapshot.meta, "telegram.sent", {
        action: row.scoring?.action,
        signalType: row.signalType || null,
        score: row.scoring?.score,
        name: row.name,
        sourceId: row.sourceId,
      });
    }
  }

  async processRetailProduct(source, product, pageText, snapshot) {
    const name = safeString(product.name, 180);
    if (!name) return null;
    const games = [...new Set([...(source.games || []), ...detectGames(`${name} ${pageText.slice(0, 12000)}`)])];
    if (!games.length || (games.length === 1 && games[0] === "collectibles")) return null;

    let market = null;
    try {
      market = await this.marketLookup(name, games, snapshot);
    } catch (error) {
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
      observedAt: nowIso(),
      name,
      games,
      sourceId: source.id,
      sourceName: source.name,
      sourceKind: source.kind,
      location: extractLocationHint(text, source.location || null),
      timingHint: extractTimingHint(text),
      url: product.url || source.url,
      retailSgd: product.priceSgd || null,
      marketSgd,
      market,
      scoring,
      reason,
    };
    await this.maybeAlert(row, snapshot, false);
    return row;
  }

  async checkWebsiteSource(source, state, snapshot) {
    const result = await fetchText(source.url);
    const fingerprint = hashString(result.body);
    const text = stripHtml(result.body);
    const changed = Boolean(state.fingerprint && state.fingerprint !== fingerprint);
    const products = source.kind === "retailer" ? parseProducts(source, result.body, result.finalUrl) : [];
    const games = detectGames(text);
    const urgency = urgencyScore(text);
    const reprintRisk = reprintRiskScore(text);
    const cfgStamp = hashString(JSON.stringify({
      ...scoringConfig(this.env),
      marketProviders: MARKET_PROVIDERS.map((p) => [p.id, p.supports(this.env, "", source.games || [])]),
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
          id: hashString(`${source.id}|${fingerprint}`),
          observedAt: nowIso(),
          name: `${source.name} signal`,
          games,
          sourceId: source.id,
          sourceName: source.name,
          sourceKind: source.kind,
          signalType: reprintRisk >= urgency ? "SUPPLY" : "DROP",
          supplyRisk: reprintRisk,
          location: extractLocationHint(text, source.location || null),
          timingHint: extractTimingHint(text),
          url: result.finalUrl,
          retailSgd: null,
          marketSgd: null,
          market: null,
          scoring,
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

  async checkSocialSource(source, state, snapshot) {
    const cursor = state.cursor || state.lastPostId || null;
    const posts = await source.adapter.fetchPosts(this.env, source.account, cursor);
    const observations = [];
    const sorted = [...posts].sort((a, b) => String(a.id).localeCompare(String(b.id)));
    for (const post of sorted) {
      const games = detectGames(post.text);
      if (!games.length) continue;
      const urgency = urgencyScore(post.text);
      const reprintRisk = reprintRiskScore(post.text);
      const scoring = opportunityScore(this.scoreInput({
        urgencyScore: urgency,
        socialHeat: clamp(45 + urgency),
        confidenceScore: 82,
        scarcityScore: 55,
        reprintRisk,
      }));
      const row = {
        id: hashString(`${source.adapter.id}|${post.id}`),
        observedAt: post.createdAt,
        name: safeString(post.text, 140),
        games,
        sourceId: source.id,
        sourceName: source.name,
        sourceKind: "social",
        signalType: reprintRisk > urgency ? "SUPPLY" : "DROP",
        supplyRisk: reprintRisk,
        location: extractLocationHint(post.text, post.location || source.location || "Singapore"),
        timingHint: extractTimingHint(post.text),
        url: post.url,
        retailSgd: null,
        marketSgd: null,
        market: null,
        scoring,
        reason: ["social signal", urgency ? `urgency ${urgency}/100` : null, reprintRisk ? `supply risk ${reprintRisk}/100` : null].filter(Boolean),
      };
      observations.push(row);
      await this.maybeAlert(row, snapshot, true);
    }
    return {
      observations,
      cursor: source.adapter.nextCursor(posts, cursor),
      posts: posts.length,
    };
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
      try {
        market = await this.marketLookup(name, games, snapshot);
      } catch (error) {
        this.log(snapshot.meta, "market.lookup.error", { sourceId: item?.sourceId || "social-ingest", name, message: safeString(error.message) });
      }
      const cfg = scoringConfig(this.env);
      const marketSgd = asNumber(item?.marketSgd, null) ?? (market?.marketUsd ? market.marketUsd * cfg.usdSgd : null);
      const retailSgd = asNumber(item?.retailSgd, null);
      const sales30d = asNumber(item?.sales30d, null) ?? market?.sales30d;
      const totalListings = asNumber(item?.totalListings, null) ?? market?.totalListings;
      const scoring = opportunityScore(this.scoreInput({
        retailSgd,
        marketSgd,
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
        observedAt: item?.publishedAt || nowIso(),
        name,
        games,
        sourceId: safeString(item?.sourceId || "social-ingest", 80),
        sourceName: safeString(item?.sourceName || item?.platform || "Social ingest", 100),
        sourceKind: "social",
        signalType: reprintRisk > urgency ? "SUPPLY" : "DROP",
        supplyRisk: reprintRisk,
        location: extractLocationHint(text, item?.location || "Singapore"),
        timingHint: item?.timingHint || extractTimingHint(text),
        url: item?.url || null,
        retailSgd,
        marketSgd,
        market: market ? { ...market, sales30d, totalListings } : null,
        scoring,
        reason: [
          "social/drop signal",
          scoring.netMarginPct !== null ? `${scoring.netMarginPct}% est. net margin` : null,
          urgency ? `urgency ${urgency}/100` : null,
          reprintRisk ? `supply risk ${reprintRisk}/100` : null,
        ].filter(Boolean),
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
    const socialSources = loadSocialSources(this.env);
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
          sourceId: source.id,
          kind: source.kind,
          changed: result.changed,
          rescore: result.rescore,
          products: result.products,
          games: result.games,
          urgency: result.urgency,
          reprintRisk: result.reprintRisk,
        });
      } catch (error) {
        state.consecutiveFailures = Number(state.consecutiveFailures || 0) + 1;
        state.lastError = safeString(error.message);
        const backoff = sourceBackoffSeconds(state.consecutiveFailures);
        state.nextDueAt = new Date(Date.now() + backoff * 1000).toISOString();
        this.log(meta, "source.fetch.error", { sourceId: source.id, failures: state.consecutiveFailures, message: state.lastError, backoffSeconds: backoff });
      }
      sourceStates[source.id] = state;
    }

    for (const source of socialSources) {
      const state = sourceStates[source.id] || {};
      if (state.nextDueAt && Date.now() < Date.parse(state.nextDueAt)) continue;
      checked += 1;
      state.lastCheckAt = nowIso();
      try {
        const result = await this.checkSocialSource(source, state, snapshot);
        state.lastSuccessAt = nowIso();
        state.consecutiveFailures = 0;
        state.lastError = null;
        state.cursor = result.cursor;
        state.observations = Number(state.observations || 0) + result.observations.length;
        state.nextDueAt = new Date(Date.now() + source.intervalSeconds * 1000).toISOString();
        successes += 1;
        newOpportunities.push(...result.observations);
        this.log(meta, "source.social.ok", { sourceId: source.id, adapter: source.adapter.id, posts: result.posts, observations: result.observations.length });
      } catch (error) {
        state.consecutiveFailures = Number(state.consecutiveFailures || 0) + 1;
        state.lastError = safeString(error.message);
        const backoff = sourceBackoffSeconds(state.consecutiveFailures);
        state.nextDueAt = new Date(Date.now() + backoff * 1000).toISOString();
        this.log(meta, "source.social.error", { sourceId: source.id, adapter: source.adapter.id, message: state.lastError, backoffSeconds: backoff });
      }
      sourceStates[source.id] = state;
    }

    meta.consecutiveFailures = checked && !successes ? Number(meta.consecutiveFailures || 0) + 1 : 0;
    if (successes) meta.lastSuccessAt = nowIso();
    meta.lastRun = {
      trigger,
      checked,
      successes,
      newOpportunities: newOpportunities.length,
      marketLookups: snapshot.marketLookupsThisRun,
      marketBudgetExhausted: snapshot.marketBudgetExhausted,
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
      const socialSources = loadSocialSources(this.env);
      const healthRows = [
        ...sources.map((s) => sourceHealth(s, data.sourceStates[s.id])),
        ...socialSources.map((s) => sourceHealth(s, data.sourceStates[s.id])),
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
      const socialSources = loadSocialSources(this.env);
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
          socialSources: socialSources.length,
          socialAdapters: [...new Set(socialSources.map((s) => s.adapter.id))],
          marketProviders: MARKET_PROVIDERS.map((provider) => ({ id: provider.id, configured: provider.supports(this.env, "", []) || Boolean(this.env.TCG_API_KEY && provider.id === "tcgapi.dev") })),
          tcgHistoryEnabled: asBool(this.env.TCG_API_HISTORY_ENABLED, false),
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
          persistence: "Durable Object SQLite-backed storage behind storage/state.js",
          d1Enabled: false,
        },
        sources: [...sources, ...socialSources].map((s) => sourceHealth(s, data.sourceStates[s.id])),
        opportunities: rankRows(data.opportunities || []),
        recentEvents: data.meta.recentEvents || [],
      });
    }

    return json({ error: "not_found" }, 404);
  }
}
