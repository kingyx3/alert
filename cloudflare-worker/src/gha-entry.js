import worker, {
  LazadaMonitor as BrowserRunMonitor,
  isActiveSgt,
  nextActiveStart,
} from "./entry.js";

const SOURCE_ENGINE_GHA = "github-actions-playwright";
const DEFAULT_EXTERNAL_STALE_SECONDS = 20 * 60;
const MAX_SNAPSHOT_AGE_MS = 2 * 60 * 60 * 1000;
const MAX_PRODUCTS = 250;

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
    .map((value) => normalizeText(value.trim()))
    .filter(Boolean);
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

function authorized(request, env) {
  return Boolean(env.DEBUG_TOKEN) && constantTimeEqual(bearerToken(request), env.DEBUG_TOKEN);
}

function monitorStub(env) {
  const id = env.MONITOR.idFromName("lazada-pokemon-tcg");
  return env.MONITOR.get(id);
}

function productKey(product) {
  for (const field of ["skuId", "sku", "url", "name"]) {
    const value = product[field];
    if (value !== null && value !== undefined && value !== "") return `${field}:${value}`;
  }
  return null;
}

function normalizeProduct(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const name = String(raw.name || "").trim();
  const inStock = typeof raw.inStock === "boolean" ? raw.inStock : null;
  let price = raw.price ?? null;
  if (price !== null && price !== "") {
    const parsed = Number(price);
    price = Number.isFinite(parsed) ? parsed : null;
  } else {
    price = null;
  }

  const product = {
    name,
    price,
    priceShow: String(raw.priceShow || ""),
    inStock,
    sold: String(raw.sold || ""),
    url: raw.url ? String(raw.url) : null,
    image: raw.image ? String(raw.image) : null,
    skuId: raw.skuId ? String(raw.skuId) : null,
    sku: raw.sku ? String(raw.sku) : null,
    sellerName: raw.sellerName ? String(raw.sellerName) : null,
    sellerId: raw.sellerId ? String(raw.sellerId) : null,
  };

  return name && productKey(product) ? product : null;
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
    "🚨 Lazada Pokémon TCG restock",
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
      body: JSON.stringify({
        chat_id: env.TELEGRAM_CHANNEL_ID,
        text,
        disable_web_page_preview: true,
      }),
    });
    const responseText = await response.text();
    if (!response.ok) {
      throw new Error(`Telegram send failed HTTP ${response.status}: ${responseText.slice(0, 250)}`);
    }
  }

  return { chunks: chunks.length };
}

function externalHealth(meta, staleMs) {
  const now = Date.now();
  const sleeping = !isActiveSgt(now);
  const lastSuccessMs = meta.lastSuccessAt ? Date.parse(meta.lastSuccessAt) : 0;
  const stale = !lastSuccessMs || now - lastSuccessMs > staleMs;
  const degraded = !sleeping && stale;

  return {
    status: degraded ? "degraded" : "ok",
    mode: sleeping ? "sleeping" : "active",
    activeWindowSgt: "08:00-24:00",
    sourceEngine: SOURCE_ENGINE_GHA,
    externalSnapshotMode: true,
    healthStaleAfterSeconds: Math.round(staleMs / 1000),
    lastCheckAt: meta.lastCheckAt || null,
    lastSuccessAt: meta.lastSuccessAt || null,
    lastAlertAt: meta.lastAlertAt || null,
    lastAcceptedBatchId: meta.lastIngestBatchId || null,
    lastAcceptedRunnerSlot: meta.lastIngestRunnerSlot || null,
    lastErrorAt: meta.lastError?.at || null,
    lastErrorType: meta.lastError?.type || null,
    lastErrorMessage: meta.lastError?.message || null,
    consecutiveFailures: 0,
    blockStreak: 0,
    recoveryMode: false,
    recoverySuccesses: 0,
    nextAlarmAt: null,
    sleepingUntil: sleeping ? new Date(nextActiveStart(now)).toISOString() : null,
  };
}

export class LazadaMonitor extends BrowserRunMonitor {
  externalSnapshotMode() {
    return asBool(this.env.EXTERNAL_SNAPSHOT_MODE, false);
  }

  externalStaleMs() {
    return asInt(
      this.env.EXTERNAL_HEALTH_STALE_SECONDS,
      DEFAULT_EXTERNAL_STALE_SECONDS,
      5 * 60,
      2 * 60 * 60,
    ) * 1000;
  }

  sourceEngine() {
    return this.externalSnapshotMode() ? SOURCE_ENGINE_GHA : super.sourceEngine();
  }

  async ensureRunning() {
    if (!this.externalSnapshotMode()) return super.ensureRunning();
    const { inventory, meta } = await this.loadState();
    await this.state.storage.deleteAlarm();
    meta.sourceEngine = SOURCE_ENGINE_GHA;
    meta.nextAlarmAt = null;
    meta.nextAllowedCheckAt = 0;
    meta.sleepingUntil = null;
    this.log(meta, "external.watchdog", {
      sourceEngine: SOURCE_ENGINE_GHA,
      lastSuccessAt: meta.lastSuccessAt || null,
      lastIngestBatchId: meta.lastIngestBatchId || null,
    });
    await this.persist(inventory, meta);
  }

  async alarm() {
    if (!this.externalSnapshotMode()) return super.alarm();
    await this.state.storage.deleteAlarm();
    const { inventory, meta } = await this.loadState();
    meta.nextAlarmAt = null;
    meta.nextAllowedCheckAt = 0;
    this.log(meta, "external.stale_alarm.cleared", { sourceEngine: SOURCE_ENGINE_GHA });
    await this.persist(inventory, meta);
  }

  async runCheck(trigger, inventoryArg = null, metaArg = null) {
    if (!this.externalSnapshotMode()) return super.runCheck(trigger, inventoryArg, metaArg);
    const loaded = inventoryArg && metaArg
      ? { inventory: inventoryArg, meta: metaArg }
      : await this.loadState();
    await this.state.storage.deleteAlarm();
    loaded.meta.sourceEngine = SOURCE_ENGINE_GHA;
    loaded.meta.nextAlarmAt = null;
    loaded.meta.nextAllowedCheckAt = 0;
    loaded.meta.sleepingUntil = null;
    this.log(loaded.meta, "external.source_check.skipped", {
      trigger,
      reason: "external_snapshot_mode",
    });
    await this.persist(loaded.inventory, loaded.meta);
    return { ok: true, skipped: true, reason: "external_snapshot_mode" };
  }

  async ingestSnapshot(payload) {
    if (!this.externalSnapshotMode()) {
      return { ok: false, status: 409, error: "external_snapshot_mode_disabled" };
    }

    const batchId = String(payload?.batchId || "").trim();
    const runnerSlot = String(payload?.runnerSlot || "").trim() || null;
    const checkedAt = String(payload?.checkedAt || "").trim();
    const checkedAtMs = Date.parse(checkedAt);
    const rawProducts = Array.isArray(payload?.products) ? payload.products : [];

    if (!batchId || batchId.length > 160) {
      return { ok: false, status: 400, error: "invalid_batch_id" };
    }
    if (!Number.isFinite(checkedAtMs)) {
      return { ok: false, status: 400, error: "invalid_checked_at" };
    }
    const ageMs = Date.now() - checkedAtMs;
    if (ageMs > MAX_SNAPSHOT_AGE_MS || ageMs < -5 * 60 * 1000) {
      return { ok: false, status: 400, error: "snapshot_timestamp_out_of_range" };
    }
    if (!rawProducts.length || rawProducts.length > MAX_PRODUCTS) {
      return { ok: false, status: 400, error: "invalid_product_count" };
    }

    const loaded = await this.loadState();
    if (loaded.meta.lastIngestBatchId === batchId) {
      this.log(loaded.meta, "external.snapshot.duplicate", { batchId, runnerSlot });
      await this.persist(loaded.inventory, loaded.meta);
      return {
        ok: true,
        duplicate: true,
        acceptedBatchId: batchId,
        lastSuccessAt: loaded.meta.lastSuccessAt || null,
      };
    }

    const wantedKeywords = keywords(this.env);
    const products = rawProducts
      .map(normalizeProduct)
      .filter(Boolean)
      .filter((product) => {
        const haystack = normalizeText(product.name);
        return wantedKeywords.some((keyword) => haystack.includes(keyword));
      });

    if (!products.length) {
      return { ok: false, status: 400, error: "no_valid_tcg_products" };
    }

    const inventory = structuredClone(loaded.inventory);
    const meta = structuredClone(loaded.meta);
    const initialized = Boolean(meta.initialized);
    const restocked = [];
    const seenKeys = new Set();
    const missingThreshold = this.missingConfirmations();

    for (const product of products) {
      const key = productKey(product);
      if (!key) continue;
      seenKeys.add(key);
      const previous = inventory[key];

      if (!previous) {
        inventory[key] = {
          available: product.inStock === true,
          missingStreak: 0,
          firstSeenAt: checkedAt,
          lastSeenAt: checkedAt,
          lastChangedAt: checkedAt,
          product,
        };
        if (initialized && product.inStock === true) restocked.push(product);
        continue;
      }

      previous.lastSeenAt = checkedAt;
      previous.missingStreak = 0;
      previous.product = product;
      if (product.inStock === true && previous.available !== true) {
        previous.available = true;
        previous.lastChangedAt = checkedAt;
        if (initialized) restocked.push(product);
      } else if (product.inStock === false && previous.available !== false) {
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

    try {
      if (!initialized) {
        meta.initialized = true;
        if (asBool(this.env.ALERT_ON_FIRST_RUN, false)) {
          const available = products.filter((product) => product.inStock === true);
          if (available.length) {
            await sendTelegram(this.env, available, checkedAt);
            meta.lastAlertAt = checkedAt;
          }
        }
      } else if (restocked.length) {
        await sendTelegram(this.env, restocked, checkedAt);
        meta.lastAlertAt = checkedAt;
      }
    } catch (error) {
      this.log(loaded.meta, "external.snapshot.telegram_error", {
        batchId,
        runnerSlot,
        message: String(error?.message || error),
      });
      await this.persist(loaded.inventory, loaded.meta);
      return { ok: false, status: 502, error: "telegram_send_failed" };
    }

    meta.lastCheckAt = checkedAt;
    meta.lastSuccessAt = checkedAt;
    meta.lastError = null;
    meta.lastSource = {
      engine: SOURCE_ENGINE_GHA,
      batchId,
      runnerSlot,
      httpStatus: Number(payload?.httpStatus) || null,
      finalUrl: payload?.finalUrl ? String(payload.finalUrl).slice(0, 500) : null,
      productCount: products.length,
      acceptedAt: new Date().toISOString(),
    };
    meta.sourceEngine = SOURCE_ENGINE_GHA;
    meta.lastIngestBatchId = batchId;
    meta.lastIngestRunnerSlot = runnerSlot;
    meta.consecutiveFailures = 0;
    meta.blockStreak = 0;
    meta.recoveryMode = false;
    meta.recoverySuccesses = 0;
    meta.nextAlarmAt = null;
    meta.nextAllowedCheckAt = 0;
    meta.sleepingUntil = null;

    this.log(meta, "external.snapshot.accepted", {
      batchId,
      runnerSlot,
      products: products.length,
      trackedSkus: Object.keys(inventory).length,
      availableSkus: Object.values(inventory).filter((item) => item?.available === true).length,
      restockedSkus: restocked.length,
    });
    await this.state.storage.deleteAlarm();
    await this.persist(inventory, meta);

    return {
      ok: true,
      duplicate: false,
      acceptedBatchId: batchId,
      products: products.length,
      restocked: restocked.length,
      lastSuccessAt: checkedAt,
    };
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/snapshot") {
      let payload;
      try {
        payload = await request.json();
      } catch {
        return jsonResponse({ ok: false, error: "invalid_json" }, 400);
      }
      const result = await this.ingestSnapshot(payload);
      return jsonResponse(result, result.status || (result.ok ? 200 : 400));
    }

    if (this.externalSnapshotMode() && request.method === "GET" && url.pathname === "/healthz") {
      const { meta } = await this.loadState();
      return jsonResponse(externalHealth(meta, this.externalStaleMs()));
    }

    if (this.externalSnapshotMode() && request.method === "GET" && url.pathname === "/debug") {
      const response = await super.fetch(request);
      const payload = await response.json();
      const { meta } = await this.loadState();
      payload.health = externalHealth(meta, this.externalStaleMs());
      payload.config = {
        ...(payload.config || {}),
        sourceEngine: SOURCE_ENGINE_GHA,
        externalSnapshotMode: true,
        externalHealthStaleSeconds: this.externalStaleMs() / 1000,
        browserRunEnabled: false,
      };
      return jsonResponse(payload, response.status);
    }

    return super.fetch(request);
  }
}

export default {
  ...worker,
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/snapshot") {
      if (!authorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      }
      const body = await request.text();
      return monitorStub(env).fetch("https://monitor.internal/snapshot", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
      });
    }
    return worker.fetch(request, env, ctx);
  },
};
