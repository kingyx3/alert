const DEFAULT_CHECK_INTERVAL_SECONDS = 30;
const DEFAULT_BLOCK_BACKOFF_SECONDS = 300;
const DEFAULT_ERROR_BACKOFF_SECONDS = 60;
const DEFAULT_MISSING_CONFIRMATIONS = 2;
const MAX_EVENTS = 50;
const MAX_DEBUG_INVENTORY = 150;

const BLOCK_MARKERS = [
  "captcha",
  "security check",
  "verify you are human",
  "access denied",
  "unusual traffic",
  "robot check",
  "are you a robot",
];

class SourceBlockedError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "SourceBlockedError";
    this.details = details;
  }
}

class SourceParseError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "SourceParseError";
    this.details = details;
  }
}

function nowIso() {
  return new Date().toISOString();
}

function asInt(value, fallback, min = 1, max = Number.MAX_SAFE_INTEGER) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function asBool(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "boolean") return value;
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "n", "off"].includes(normalized)) return false;
  return fallback;
}

function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function keywords(env) {
  return String(env.TCG_KEYWORDS || "pokemon,pokémon,tcg,trading card")
    .split(",")
    .map((x) => normalizeText(x.trim()))
    .filter(Boolean);
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return `${url.protocol}//${url.host}${url.pathname}`;
  } catch {
    return "invalid-url";
  }
}

function jsonResponse(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

function bearerToken(request) {
  const header = request.headers.get("authorization") || "";
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match ? match[1] : "";
}

function constantTimeEqual(a, b) {
  const left = String(a || "");
  const right = String(b || "");
  if (!left || !right || left.length !== right.length) return false;
  let result = 0;
  for (let i = 0; i < left.length; i += 1) {
    result |= left.charCodeAt(i) ^ right.charCodeAt(i);
  }
  return result === 0;
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
  if (Object.prototype.hasOwnProperty.call(item, "inStock")) {
    return parseBooleanSignal(item.inStock);
  }

  if (Object.prototype.hasOwnProperty.call(item, "soldOut")) {
    const soldOut = parseBooleanSignal(item.soldOut);
    return soldOut === null ? null : !soldOut;
  }

  for (const key of ["stock", "stockCount", "quantity", "availableStock"]) {
    if (Object.prototype.hasOwnProperty.call(item, key)) {
      const n = Number(item[key]);
      if (Number.isFinite(n)) return n > 0;
    }
  }

  const availability = normalizeText(item.availability || item.stockStatus || item.status);
  if (availability) {
    if (["out of stock", "sold out", "unavailable"].some((x) => availability.includes(x))) return false;
    if (["in stock", "available"].some((x) => availability.includes(x))) return true;
  }

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
    name: item.name || item.title || item.productName || "",
    price,
    priceShow: item.priceShow || item.originalPriceShow || item.salePriceShow || "",
    inStock: inferInStock(item),
    sold: item.itemSoldCntShow || item.itemSoldCnt || item.sold || "",
    url: itemUrl || null,
    image: item.image || item.imageUrl || null,
    skuId: item.skuId || item.itemId || item.productId || null,
    sku: item.sku || item.skuCode || null,
    sellerName: item.sellerName || null,
    sellerId: item.sellerId || null,
  };
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
      const dictItems = value.filter((x) => x && typeof x === "object" && !Array.isArray(x));
      if (dictItems.length) yield dictItems;
    }
    yield* candidateItemLists(value, depth + 1);
  }
}

function extractProducts(payload) {
  let best = [];
  for (const items of candidateItemLists(payload)) {
    const normalized = items
      .map(normalizeProduct)
      .filter((p) => p.name && (p.url || p.skuId || p.sku));
    if (normalized.length > best.length) best = normalized;
  }
  return best;
}

function isTcgProduct(product, env) {
  const haystack = normalizeText(product.name);
  return keywords(env).some((keyword) => haystack.includes(keyword));
}

function productKey(product) {
  for (const field of ["skuId", "sku", "url", "name"]) {
    const value = product[field];
    if (value !== null && value !== undefined && value !== "") return `${field}:${value}`;
  }
  return null;
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
  for (const marker of ['{"mods"', '{"modsData"', '{"data"']) {
    let start = body.indexOf(marker);
    while (start >= 0) {
      const parsed = parseJsonObjectAt(body, start);
      if (parsed && typeof parsed === "object") return parsed;
      start = body.indexOf(marker, start + marker.length);
    }
  }
  return null;
}

function bodyFingerprint(body) {
  let hash = 2166136261;
  const sample = body.slice(0, 200000);
  for (let i = 0; i < sample.length; i += 1) {
    hash ^= sample.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

async function fetchSource(env) {
  if (!env.LAZADA_URL) throw new SourceParseError("LAZADA_URL Worker secret is not configured");

  const response = await fetch(env.LAZADA_URL, {
    method: "GET",
    redirect: "follow",
    headers: {
      "user-agent": "kingyx3-alert/3.0 (+https://github.com/kingyx3/alert)",
      accept: "application/json,text/html;q=0.9,*/*;q=0.8",
      "accept-language": "en-SG,en;q=0.9",
    },
  });

  const body = await response.text();
  const lowerBody = body.toLowerCase();
  const metadata = {
    status: response.status,
    contentType: response.headers.get("content-type") || "",
    bytes: body.length,
    finalUrl: safeUrl(response.url || env.LAZADA_URL),
    fingerprint: bodyFingerprint(body),
  };

  if ([403, 429].includes(response.status) || BLOCK_MARKERS.some((marker) => lowerBody.includes(marker))) {
    throw new SourceBlockedError("Source returned a rate-limit or anti-bot challenge; no bypass attempted", metadata);
  }

  if (!response.ok) {
    const error = new Error(`Source returned HTTP ${response.status}`);
    error.details = metadata;
    throw error;
  }

  let payload = null;
  try {
    payload = JSON.parse(body);
  } catch {
    payload = extractEmbeddedJson(body);
  }

  if (!payload || typeof payload !== "object") {
    throw new SourceParseError("Response did not contain a parseable product payload", metadata);
  }

  return { payload, metadata };
}

function formatPrice(product) {
  if (product.priceShow) return product.priceShow;
  if (Number.isFinite(product.price)) return `$${product.price.toFixed(2)}`;
  return "Price unavailable";
}

async function sendTelegram(env, products, checkedAt) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) {
    throw new Error("TELEGRAM_BOT_TOKEN/TELEGRAM_CHANNEL_ID Worker secrets are not configured");
  }

  const lines = [
    `🚨 Lazada Pokémon TCG restock`,
    `${products.length} SKU${products.length === 1 ? "" : "s"} newly available`,
    `Checked: ${checkedAt}`,
    "",
  ];

  for (const [index, product] of products.entries()) {
    lines.push(`${index + 1}. ${product.name}`);
    lines.push(`   ${formatPrice(product)}`);
    if (product.skuId || product.sku) lines.push(`   SKU: ${product.skuId || product.sku}`);
    if (product.url) lines.push(`   ${product.url}`);
    lines.push("");
  }

  const chunks = [];
  let current = "";
  for (const line of lines) {
    const next = `${current}${line}\n`;
    if (next.length > 3900 && current) {
      chunks.push(current.trimEnd());
      current = `${line}\n`;
    } else {
      current = next;
    }
  }
  if (current.trim()) chunks.push(current.trimEnd());

  const endpoint = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  for (const text of chunks) {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHANNEL_ID, text, disable_web_page_preview: true }),
    });
    const responseText = await response.text();
    if (!response.ok) {
      throw new Error(`Telegram send failed HTTP ${response.status}: ${responseText.slice(0, 250)}`);
    }
  }

  return { chunks: chunks.length };
}

function publicHealth(meta) {
  const now = Date.now();
  const lastSuccessMs = meta.lastSuccessAt ? Date.parse(meta.lastSuccessAt) : 0;
  const degraded = (meta.consecutiveFailures || 0) > 0 || !lastSuccessMs || now - lastSuccessMs > 10 * 60 * 1000;
  return {
    status: degraded ? "degraded" : "ok",
    lastCheckAt: meta.lastCheckAt || null,
    lastSuccessAt: meta.lastSuccessAt || null,
    lastAlertAt: meta.lastAlertAt || null,
    consecutiveFailures: meta.consecutiveFailures || 0,
    nextAlarmAt: meta.nextAlarmAt || null,
  };
}

export class LazadaMonitor {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async loadState() {
    const [inventory, meta] = await Promise.all([
      this.state.storage.get("inventory"),
      this.state.storage.get("meta"),
    ]);
    return {
      inventory: inventory || {},
      meta: meta || {
        initialized: false,
        recentEvents: [],
        consecutiveFailures: 0,
        nextAllowedCheckAt: 0,
      },
    };
  }

  log(meta, event, fields = {}) {
    const entry = { ts: nowIso(), event, ...fields };
    console.log(JSON.stringify(entry));
    meta.recentEvents = [...(meta.recentEvents || []), entry].slice(-MAX_EVENTS);
    return entry;
  }

  intervalMs() {
    return asInt(this.env.CHECK_INTERVAL_SECONDS, DEFAULT_CHECK_INTERVAL_SECONDS, 15, 3600) * 1000;
  }

  blockBackoffMs() {
    return asInt(this.env.BLOCK_BACKOFF_SECONDS, DEFAULT_BLOCK_BACKOFF_SECONDS, 60, 86400) * 1000;
  }

  errorBackoffMs(failures) {
    const base = asInt(this.env.ERROR_BACKOFF_SECONDS, DEFAULT_ERROR_BACKOFF_SECONDS, 30, 3600) * 1000;
    return Math.min(15 * 60 * 1000, base * 2 ** Math.min(Math.max(failures - 1, 0), 4));
  }

  missingConfirmations() {
    return asInt(this.env.MISSING_CONFIRMATIONS, DEFAULT_MISSING_CONFIRMATIONS, 1, 20);
  }

  async schedule(meta, delayMs) {
    const nextAt = Date.now() + delayMs;
    await this.state.storage.setAlarm(nextAt);
    meta.nextAlarmAt = new Date(nextAt).toISOString();
    meta.nextAllowedCheckAt = nextAt;
    this.log(meta, "alarm.scheduled", { delayMs, nextAlarmAt: meta.nextAlarmAt });
  }

  async persist(inventory, meta) {
    await this.state.storage.put({ inventory, meta });
  }

  async ensureRunning() {
    const { inventory, meta } = await this.loadState();
    const now = Date.now();
    const alarm = await this.state.storage.getAlarm();
    const due = now >= Number(meta.nextAllowedCheckAt || 0);

    this.log(meta, "monitor.ensure_running", {
      alarmAt: alarm ? new Date(alarm).toISOString() : null,
      due,
      initialized: Boolean(meta.initialized),
    });

    if (!alarm || due) {
      await this.runCheck("cron", inventory, meta);
      return;
    }

    await this.persist(inventory, meta);
  }

  async alarm() {
    const { inventory, meta } = await this.loadState();
    await this.runCheck("alarm", inventory, meta);
  }

  async runCheck(trigger, inventoryArg = null, metaArg = null) {
    const runId = crypto.randomUUID();
    const loaded = inventoryArg && metaArg ? { inventory: inventoryArg, meta: metaArg } : await this.loadState();
    const inventory = loaded.inventory;
    const meta = loaded.meta;
    const inventoryBefore = structuredClone(inventory);
    const initializedBefore = Boolean(meta.initialized);
    const checkedAt = nowIso();

    meta.lastCheckAt = checkedAt;
    this.log(meta, "monitor.check.start", {
      runId,
      trigger,
      source: safeUrl(this.env.LAZADA_URL || ""),
      initialized: Boolean(meta.initialized),
    });

    try {
      const { payload, metadata } = await fetchSource(this.env);
      this.log(meta, "source.fetch.ok", { runId, ...metadata });

      const products = extractProducts(payload);
      if (!products.length) {
        throw new SourceParseError("Parsed source but found no recognizable product collection", metadata);
      }

      const tcgProducts = products.filter((product) => isTcgProduct(product, this.env));
      if (!tcgProducts.length && !asBool(this.env.ALLOW_EMPTY_TCG_SNAPSHOT, false)) {
        throw new SourceParseError("Found products but none matched TCG_KEYWORDS; state preserved", {
          ...metadata,
          products: products.length,
        });
      }

      const current = new Map();
      for (const product of tcgProducts) {
        const key = productKey(product);
        if (key) current.set(key, product);
      }

      const initialized = Boolean(meta.initialized);
      const restocked = [];
      const missingThreshold = this.missingConfirmations();
      const seenKeys = new Set(current.keys());

      for (const [key, product] of current.entries()) {
        const previous = inventory[key];
        const signal = product.inStock;

        if (!previous) {
          inventory[key] = {
            available: signal === true,
            missingStreak: 0,
            firstSeenAt: checkedAt,
            lastSeenAt: checkedAt,
            lastChangedAt: checkedAt,
            product,
          };
          if (initialized && signal === true) restocked.push(product);
          continue;
        }

        previous.lastSeenAt = checkedAt;
        previous.missingStreak = 0;
        previous.product = product;

        if (signal === true && previous.available !== true) {
          previous.available = true;
          previous.lastChangedAt = checkedAt;
          if (initialized) restocked.push(product);
        } else if (signal === false && previous.available !== false) {
          previous.available = false;
          previous.lastChangedAt = checkedAt;
        }
      }

      for (const [key, previous] of Object.entries(inventory)) {
        if (seenKeys.has(key)) continue;
        previous.missingStreak = Number(previous.missingStreak || 0) + 1;
        if (previous.missingStreak >= missingThreshold && previous.available !== false) {
          previous.available = false;
          previous.lastChangedAt = checkedAt;
        }
      }

      this.log(meta, "stock.diff", {
        runId,
        products: products.length,
        tcgProducts: tcgProducts.length,
        trackedSkus: Object.keys(inventory).length,
        availableSkus: Object.values(inventory).filter((item) => item.available === true).length,
        restockedSkus: restocked.length,
        restocked: restocked.map((p) => ({ sku: p.skuId || p.sku || null, name: p.name })),
      });

      if (!initialized) {
        meta.initialized = true;
        this.log(meta, "stock.baseline.created", {
          runId,
          alertOnFirstRun: asBool(this.env.ALERT_ON_FIRST_RUN, false),
        });
        if (asBool(this.env.ALERT_ON_FIRST_RUN, false)) {
          const firstRunAvailable = tcgProducts.filter((p) => p.inStock === true);
          if (firstRunAvailable.length) {
            const telegram = await sendTelegram(this.env, firstRunAvailable, checkedAt);
            meta.lastAlertAt = checkedAt;
            this.log(meta, "telegram.sent", { runId, products: firstRunAvailable.length, ...telegram });
          }
        }
      } else if (restocked.length) {
        const telegram = await sendTelegram(this.env, restocked, checkedAt);
        meta.lastAlertAt = checkedAt;
        this.log(meta, "telegram.sent", { runId, products: restocked.length, ...telegram });
      }

      meta.lastSuccessAt = checkedAt;
      meta.lastError = null;
      meta.lastSource = metadata;
      meta.consecutiveFailures = 0;
      await this.schedule(meta, this.intervalMs());
      await this.persist(inventory, meta);
      this.log(meta, "monitor.check.success", { runId, trigger });
      await this.persist(inventory, meta);
      return { ok: true, restocked: restocked.length, runId };
    } catch (error) {
      meta.consecutiveFailures = Number(meta.consecutiveFailures || 0) + 1;
      const blocked = error instanceof SourceBlockedError;
      const delayMs = blocked ? this.blockBackoffMs() : this.errorBackoffMs(meta.consecutiveFailures);
      const details = error?.details || {};

      meta.lastError = {
        at: checkedAt,
        type: error?.name || "Error",
        message: String(error?.message || error),
        details,
      };
      this.log(meta, blocked ? "source.blocked" : "monitor.check.error", {
        runId,
        trigger,
        failureCount: meta.consecutiveFailures,
        errorType: meta.lastError.type,
        message: meta.lastError.message,
        details,
      });

      // Never advance SKU availability or initialization on a failed check/alert.
      // This makes notification failures retryable on the next successful run.
      meta.initialized = initializedBefore;
      await this.schedule(meta, delayMs);
      await this.persist(inventoryBefore, meta);
      return { ok: false, blocked, runId, error: meta.lastError };
    }
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/ensure-running") {
      await this.ensureRunning();
      return jsonResponse({ ok: true });
    }

    if (request.method === "POST" && url.pathname === "/check") {
      const { inventory, meta } = await this.loadState();
      const result = await this.runCheck("manual", inventory, meta);
      return jsonResponse(result, result.ok ? 200 : 502);
    }

    if (request.method === "GET" && url.pathname === "/healthz") {
      const { meta } = await this.loadState();
      return jsonResponse(publicHealth(meta));
    }

    if (request.method === "GET" && url.pathname === "/debug") {
      const { inventory, meta } = await this.loadState();
      const inventoryRows = Object.entries(inventory)
        .slice(0, MAX_DEBUG_INVENTORY)
        .map(([key, record]) => ({
          key,
          available: record.available,
          missingStreak: record.missingStreak || 0,
          firstSeenAt: record.firstSeenAt || null,
          lastSeenAt: record.lastSeenAt || null,
          lastChangedAt: record.lastChangedAt || null,
          sku: record.product?.skuId || record.product?.sku || null,
          name: record.product?.name || null,
          url: record.product?.url || null,
        }));
      return jsonResponse({
        health: publicHealth(meta),
        config: {
          source: safeUrl(this.env.LAZADA_URL || ""),
          checkIntervalSeconds: this.intervalMs() / 1000,
          blockBackoffSeconds: this.blockBackoffMs() / 1000,
          missingConfirmations: this.missingConfirmations(),
          keywords: keywords(this.env),
        },
        meta,
        inventory: inventoryRows,
        inventoryTruncated: Object.keys(inventory).length > MAX_DEBUG_INVENTORY,
      });
    }

    return jsonResponse({ error: "not_found" }, 404);
  }
}

function monitorStub(env) {
  const id = env.MONITOR.idFromName("lazada-pokemon-tcg");
  return env.MONITOR.get(id);
}

function authorized(request, env) {
  return Boolean(env.DEBUG_TOKEN) && constantTimeEqual(bearerToken(request), env.DEBUG_TOKEN);
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(
      monitorStub(env).fetch("https://monitor.internal/ensure-running", { method: "POST" }),
    );
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return jsonResponse({
        service: "lazada-tcg-restock-monitor",
        health: "/healthz",
        debug: "/debug (Bearer token required)",
        manualCheck: "/check (POST, Bearer token required)",
      });
    }

    if (request.method === "GET" && url.pathname === "/healthz") {
      return monitorStub(env).fetch("https://monitor.internal/healthz");
    }

    if (["/debug", "/check"].includes(url.pathname)) {
      if (!authorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      }
      return monitorStub(env).fetch(`https://monitor.internal${url.pathname}`, {
        method: request.method,
      });
    }

    return jsonResponse({ error: "not_found" }, 404);
  },
};
