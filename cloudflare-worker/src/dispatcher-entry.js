import ghaWorker, { LazadaMonitor as ExternalSnapshotMonitor } from "./gha-entry.js";

const DEFAULT_GITHUB_REPOSITORY = "kingyx3/alert";
const DEFAULT_GITHUB_WORKFLOW = "lazada-playwright-probe.yml";
const DEFAULT_GITHUB_REF = "main";
const DISPATCH_INTERVAL_MS = 10 * 1000;
const DISPATCHES_PER_CRON = 60 * 1000 / DISPATCH_INTERVAL_MS;
const DISPATCH_CLAIMS_STORAGE_KEY = "githubDispatchClaims";
const DISPATCH_CLAIM_TTL_MS = 5 * 60 * 1000;
const SGT_OFFSET_MS = 8 * 60 * 60 * 1000;
const ACTIVE_START_HOUR_SGT = 8;
const ACTIVE_END_HOUR_SGT = 20;

function isDispatchWindowSgt(timestamp = Date.now()) {
  const hour = new Date(Number(timestamp) + SGT_OFFSET_MS).getUTCHours();
  return hour >= ACTIVE_START_HOUR_SGT && hour < ACTIVE_END_HOUR_SGT;
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

function asBool(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "boolean") return value;
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "n", "off"].includes(normalized)) return false;
  return fallback;
}

function productKey(product) {
  for (const field of ["skuId", "sku", "url", "name"]) {
    const value = product?.[field];
    if (value !== null && value !== undefined && value !== "") return `${field}:${value}`;
  }
  return null;
}

function availableTcgProducts(payload, env) {
  const wantedKeywords = keywords(env);
  return (Array.isArray(payload?.products) ? payload.products : [])
    .filter((product) => product && typeof product === "object" && product.inStock === true)
    .filter((product) => {
      const name = String(product.name || "").trim();
      if (!name || !productKey(product)) return false;
      const haystack = normalizeText(name);
      return wantedKeywords.some((keyword) => haystack.includes(keyword));
    });
}

function alertBatchIdFor(batchId) {
  return String(batchId || "").replace(/:source-\d+$/, "");
}

function cloudflareBatchSequence(batchId) {
  const match = String(batchId || "").match(/^cf-(\d+)(?::source-\d+)?$/);
  if (!match) return null;
  const sequence = Number(match[1]);
  return Number.isSafeInteger(sequence) ? sequence : null;
}

function snapshotIsSuperseded(batchId, checkedAtMs, meta) {
  const acceptedBatchId = String(meta?.lastIngestBatchId || "");
  if (!acceptedBatchId || acceptedBatchId === batchId) return false;

  const incomingSequence = cloudflareBatchSequence(batchId);
  const acceptedSequence = cloudflareBatchSequence(acceptedBatchId);
  if (incomingSequence !== null && acceptedSequence !== null) {
    // Source-1, source-2, and the final complete snapshot of the same cf-N root
    // are peers. Only a strictly older Cloudflare dispatch generation is stale.
    return incomingSequence < acceptedSequence;
  }

  const lastSuccessMs = meta?.lastSuccessAt ? Date.parse(meta.lastSuccessAt) : 0;
  return Number.isFinite(lastSuccessMs) && Number.isFinite(checkedAtMs) && lastSuccessMs >= checkedAtMs;
}

function alertedSkuKeys(meta, alertBatchId) {
  if (!alertBatchId || meta?.lastAlertBatchId !== alertBatchId) return new Set();
  return new Set(Array.isArray(meta?.lastAlertSkuKeys) ? meta.lastAlertSkuKeys.map(String) : []);
}

function formatPrice(product) {
  if (product?.priceShow) return String(product.priceShow);
  const price = Number(product?.price);
  if (Number.isFinite(price)) return `$${price.toFixed(2)}`;
  return "Price unavailable";
}

async function sendPersistentStockTelegram(env, products, checkedAt) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) {
    throw new Error("TELEGRAM_BOT_TOKEN/TELEGRAM_CHANNEL_ID Worker secrets are not configured");
  }

  const lines = [
    "🚨 Lazada Pokémon TCG in stock",
    `${products.length} SKU${products.length === 1 ? "" : "s"} currently available`,
    `Checked: ${checkedAt}`,
    "",
  ];

  for (const [index, product] of products.entries()) {
    lines.push(`${index + 1}. ${String(product.name || "").trim()}`);
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
}

export class LazadaMonitor extends ExternalSnapshotMonitor {
  async ingestSnapshot(payload) {
    const previousIngest = this._ingestTail || Promise.resolve();
    let releaseIngest;
    this._ingestTail = new Promise((resolve) => {
      releaseIngest = resolve;
    });

    await previousIngest;
    try {
      const batchId = String(payload?.batchId || "").trim();
      const alertBatchId = alertBatchIdFor(batchId);
      const checkedAt = String(payload?.checkedAt || "").trim();
      const checkedAtMs = Date.parse(checkedAt);
      let loaded = null;

      if (batchId && Number.isFinite(checkedAtMs)) {
        loaded = await this.loadState();
        if (snapshotIsSuperseded(batchId, checkedAtMs, loaded.meta)) {
          this.log(loaded.meta, "external.snapshot.superseded", {
            batchId,
            alertBatchId,
            checkedAt,
            batchSequence: cloudflareBatchSequence(batchId),
            acceptedBatchId: loaded.meta.lastIngestBatchId,
            acceptedBatchSequence: cloudflareBatchSequence(loaded.meta.lastIngestBatchId),
            lastSuccessAt: loaded.meta.lastSuccessAt,
          });
          return {
            ok: true,
            duplicate: false,
            superseded: true,
            acceptedBatchId: loaded.meta.lastIngestBatchId,
            lastSuccessAt: loaded.meta.lastSuccessAt,
          };
        }
      }

      if (!loaded) loaded = await this.loadState();
      const availableProducts = availableTcgProducts(payload, this.env);
      const initialized = Boolean(loaded.meta.initialized);
      const alreadyAlerted = alertedSkuKeys(loaded.meta, alertBatchId);
      const alertsAllowed = !asBool(this.env.ALERT_WINDOW_ENFORCED, false) || isDispatchWindowSgt(Date.now());
      const transitionProducts = availableProducts.filter((product) => {
        const key = productKey(product);
        const previous = key ? loaded.inventory[key] : null;
        return !previous || previous.available !== true;
      });
      const persistentProducts = initialized
        ? availableProducts.filter((product) => {
            const key = productKey(product);
            const previous = key ? loaded.inventory[key] : null;
            return previous?.available === true && key && !alreadyAlerted.has(key);
          })
        : [];

      if (alertBatchId && persistentProducts.length > 0 && alertsAllowed) {
        try {
          await sendPersistentStockTelegram(this.env, persistentProducts, checkedAt);
        } catch (error) {
          this.log(loaded.meta, "external.snapshot.telegram_error", {
            batchId,
            alertBatchId,
            persistentStock: true,
            message: String(error?.message || error),
          });
          return { ok: false, status: 502, error: "telegram_send_failed" };
        }

        const keys = new Set(alreadyAlerted);
        for (const product of persistentProducts) {
          const key = productKey(product);
          if (key) keys.add(key);
        }
        loaded.meta.lastAlertBatchId = alertBatchId;
        loaded.meta.lastAlertSkuKeys = [...keys];
        loaded.meta.lastAlertAt = checkedAt;
        this.log(loaded.meta, "external.snapshot.stock_still_available_alert", {
          batchId,
          alertBatchId,
          products: persistentProducts.length,
          skuKeys: [...keys],
        });
        await this.persist(loaded.inventory, loaded.meta);
      }

      const result = await super.ingestSnapshot(payload);

      const transitionAlertProducts =
        !initialized && asBool(this.env.ALERT_ON_FIRST_RUN, false)
          ? availableProducts.filter((product) => {
              const key = productKey(product);
              return key && !alreadyAlerted.has(key);
            })
          : transitionProducts.filter((product) => {
              const key = productKey(product);
              return key && !alreadyAlerted.has(key);
            });

      if (
        result?.ok === true &&
        !result?.duplicate &&
        !result?.superseded &&
        alertBatchId &&
        alertsAllowed &&
        transitionAlertProducts.length > 0
      ) {
        const fresh = await this.loadState();
        const keys = alertedSkuKeys(fresh.meta, alertBatchId);
        for (const product of transitionAlertProducts) {
          const key = productKey(product);
          if (key) keys.add(key);
        }
        fresh.meta.lastAlertBatchId = alertBatchId;
        fresh.meta.lastAlertSkuKeys = [...keys];
        await this.persist(fresh.inventory, fresh.meta);
      }

      return result;
    } finally {
      releaseIngest();
    }
  }

  async claimGithubDispatch(dispatchKey) {
    const previousClaim = this._dispatchClaimTail || Promise.resolve();
    let releaseClaim;
    this._dispatchClaimTail = new Promise((resolve) => {
      releaseClaim = resolve;
    });

    await previousClaim;
    try {
      const now = Date.now();
      const stored = await this.state.storage.get(DISPATCH_CLAIMS_STORAGE_KEY);
      const claims = stored && typeof stored === "object" && !Array.isArray(stored)
        ? { ...stored }
        : {};

      for (const [key, claimedAt] of Object.entries(claims)) {
        const ageMs = now - Number(claimedAt || 0);
        if (!Number.isFinite(ageMs) || ageMs > DISPATCH_CLAIM_TTL_MS) delete claims[key];
      }

      if (Object.prototype.hasOwnProperty.call(claims, dispatchKey)) {
        return { ok: true, claimed: false, dispatchKey };
      }

      claims[dispatchKey] = now;
      await this.state.storage.put({ [DISPATCH_CLAIMS_STORAGE_KEY]: claims });
      return { ok: true, claimed: true, dispatchKey };
    } finally {
      releaseClaim();
    }
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/dispatch-claim") {
      let payload;
      try {
        payload = await request.json();
      } catch {
        return jsonResponse({ ok: false, error: "invalid_json" }, 400);
      }

      const dispatchKey = String(payload?.dispatchKey || "").trim();
      if (!/^cf-\d+$/.test(dispatchKey)) {
        return jsonResponse({ ok: false, error: "invalid_dispatch_key" }, 400);
      }

      return jsonResponse(await this.claimGithubDispatch(dispatchKey));
    }

    return super.fetch(request);
  }
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function dispatchConfig(env) {
  return {
    configured: Boolean(env.GITHUB_ACTIONS_TOKEN),
    repository: String(env.GITHUB_DISPATCH_REPOSITORY || DEFAULT_GITHUB_REPOSITORY),
    workflow: String(env.GITHUB_DISPATCH_WORKFLOW || DEFAULT_GITHUB_WORKFLOW),
    ref: String(env.GITHUB_DISPATCH_REF || DEFAULT_GITHUB_REF),
  };
}

function dispatchKeyFor(scheduledTime) {
  return `cf-${Math.floor(Number(scheduledTime || Date.now()) / DISPATCH_INTERVAL_MS)}`;
}

function monitorStub(env) {
  const id = env.MONITOR.idFromName("lazada-pokemon-tcg");
  return env.MONITOR.get(id);
}

async function claimGithubDispatchSlot(env, dispatchKey) {
  const response = await monitorStub(env).fetch("https://monitor.internal/dispatch-claim", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ dispatchKey }),
  });
  const result = await response.json();
  if (!response.ok || result?.ok !== true) {
    throw new Error(`GitHub dispatch claim failed HTTP ${response.status}: ${JSON.stringify(result).slice(0, 300)}`);
  }
  return result;
}

export async function dispatchGithubWorkflow(env, scheduledTime = Date.now()) {
  const dispatchTime = Number(scheduledTime || Date.now());
  const dispatchKey = dispatchKeyFor(dispatchTime);
  if (!isDispatchWindowSgt(dispatchTime)) {
    return {
      ok: true,
      skipped: true,
      reason: "outside_08_20_sgt_window",
      dispatchKey,
      scheduledAt: new Date(dispatchTime).toISOString(),
    };
  }

  const config = dispatchConfig(env);
  if (!config.configured) {
    return { ok: false, skipped: true, reason: "github_actions_token_missing" };
  }

  const endpoint = `https://api.github.com/repos/${config.repository}/actions/workflows/${encodeURIComponent(config.workflow)}/dispatches`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${env.GITHUB_ACTIONS_TOKEN}`,
      "content-type": "application/json",
      "user-agent": "lazada-tcg-restock-monitor",
      "x-github-api-version": "2022-11-28",
    },
    body: JSON.stringify({
      ref: config.ref,
      inputs: {
        trigger_source: "cloudflare-cron",
        dispatch_key: dispatchKey,
        scheduled_at: new Date(dispatchTime).toISOString(),
      },
    }),
  });

  const responseText = await response.text();
  if (!response.ok) {
    throw new Error(`GitHub workflow dispatch failed HTTP ${response.status}: ${responseText.slice(0, 300)}`);
  }

  return {
    ok: true,
    status: response.status,
    dispatchKey,
    scheduledAt: new Date(dispatchTime).toISOString(),
  };
}

async function dispatchAndLog(env, scheduledTime, slot) {
  const dispatchTime = Number(scheduledTime || Date.now());
  const dispatchKey = dispatchKeyFor(dispatchTime);
  if (!isDispatchWindowSgt(dispatchTime)) {
    const result = {
      ok: true,
      skipped: true,
      reason: "outside_08_20_sgt_window",
      dispatchKey,
      scheduledAt: new Date(dispatchTime).toISOString(),
    };
    console.log(`GitHub workflow ${slot} off-hours skipped`, result);
    return result;
  }

  try {
    const claim = await claimGithubDispatchSlot(env, dispatchKey);
    if (!claim.claimed) {
      const result = {
        ok: true,
        skipped: true,
        reason: "duplicate_dispatch_key",
        dispatchKey,
        scheduledAt: new Date(dispatchTime).toISOString(),
      };
      console.log(`GitHub workflow ${slot} duplicate skipped`, result);
      return result;
    }

    const result = await dispatchGithubWorkflow(env, dispatchTime);
    console.log(`GitHub workflow ${slot} dispatch accepted`, result);
    return result;
  } catch (error) {
    console.error(`GitHub workflow ${slot} dispatch failed`, String(error?.message || error));
    return { ok: false, error: String(error?.message || error) };
  }
}

export default {
  ...ghaWorker,

  async scheduled(controller, env, ctx) {
    const scheduledTime = Number(controller?.scheduledTime || Date.now());
    if (!isDispatchWindowSgt(scheduledTime)) {
      console.log("Cloudflare scheduled event outside 08:00-20:00 SGT; no GitHub workflow will be created.");
      return undefined;
    }

    if (!env.GITHUB_ACTIONS_TOKEN) {
      console.warn("GitHub dispatch token is not configured; relying on the GitHub scheduled fallback.");
      if (typeof ghaWorker.scheduled === "function") {
        return ghaWorker.scheduled(controller, env, ctx);
      }
      return undefined;
    }

    const dispatches = Array.from({ length: DISPATCHES_PER_CRON }, (_, index) => (async () => {
      const delayMs = index * DISPATCH_INTERVAL_MS;
      if (delayMs > 0) await scheduler.wait(delayMs);
      return dispatchAndLog(env, scheduledTime + delayMs, `slot-${index + 1}`);
    })());

    await Promise.all(dispatches);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/schedulerz") {
      const config = dispatchConfig(env);
      return jsonResponse({
        status: config.configured ? "ok" : "fallback",
        scheduler: "cloudflare-cron",
        frequencySeconds: 10,
        activeWindowSgt: "08:00-20:00",
        cronFrequencySeconds: 60,
        dispatchOffsetsSeconds: [0, 10, 20, 30, 40, 50],
        dispatchDeduplication: "durable-object-10-second-key",
        githubDispatchConfigured: config.configured,
        repository: config.repository,
        workflow: config.workflow,
        ref: config.ref,
        fallback: "github-actions-schedule-every-5-minutes",
      });
    }
    return ghaWorker.fetch(request, env, ctx);
  },
};
