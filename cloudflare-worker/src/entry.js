import worker, { LazadaMonitor as BaseLazadaMonitor } from "./index.js";

const SGT_OFFSET_MS = 8 * 60 * 60 * 1000;
const ACTIVE_START_HOUR_SGT = 8;
const DEFAULT_HEALTHY_INTERVAL_SECONDS = 30;
const DEFAULT_RECOVERY_INTERVAL_SECONDS = 60;
const DEFAULT_RECOVERY_SUCCESS_TARGET = 20;
const DEFAULT_BLOCK_BACKOFF_SECONDS = 15 * 60;
const MAX_BLOCK_BACKOFF_SECONDS = 8 * 60 * 60;
const SOURCE_ENGINE_BROWSER_RUN = "cloudflare-browser-run";
const SOURCE_ENGINE_WORKER_FETCH = "worker-fetch";
const BROWSER_RUN_TIMEOUT_MS = 30 * 1000;

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

function sgtDate(timestamp = Date.now()) {
  return new Date(timestamp + SGT_OFFSET_MS);
}

export function isActiveSgt(timestamp = Date.now()) {
  return sgtDate(timestamp).getUTCHours() >= ACTIVE_START_HOUR_SGT;
}

export function nextActiveStart(timestamp = Date.now()) {
  const local = sgtDate(timestamp);
  const year = local.getUTCFullYear();
  const month = local.getUTCMonth();
  const day = local.getUTCDate();
  const localHour = local.getUTCHours();
  const startDay = localHour < ACTIVE_START_HOUR_SGT ? day : day + 1;
  const localStart = Date.UTC(year, month, startDay, ACTIVE_START_HOUR_SGT, 0, 0, 0);
  return localStart - SGT_OFFSET_MS;
}

export function blockBackoffSeconds(blockStreak, baseSeconds = DEFAULT_BLOCK_BACKOFF_SECONDS) {
  const streak = Math.max(1, Number.parseInt(String(blockStreak ?? 1), 10) || 1);
  const base = Math.min(
    MAX_BLOCK_BACKOFF_SECONDS,
    Math.max(5 * 60, Number(baseSeconds) || DEFAULT_BLOCK_BACKOFF_SECONDS),
  );
  return Math.min(MAX_BLOCK_BACKOFF_SECONDS, base * 2 ** Math.min(streak - 1, 5));
}

function monitorHealth(meta) {
  const now = Date.now();
  const sleeping = !isActiveSgt(now);
  const lastSuccessMs = meta.lastSuccessAt ? Date.parse(meta.lastSuccessAt) : 0;
  const degraded =
    Number(meta.consecutiveFailures || 0) > 0 ||
    (!sleeping && (!lastSuccessMs || now - lastSuccessMs > 10 * 60 * 1000));

  return {
    status: degraded ? "degraded" : "ok",
    mode: sleeping ? "sleeping" : "active",
    activeWindowSgt: "08:00-24:00",
    sourceEngine: meta.sourceEngine || null,
    lastCheckAt: meta.lastCheckAt || null,
    lastSuccessAt: meta.lastSuccessAt || null,
    lastAlertAt: meta.lastAlertAt || null,
    lastErrorAt: meta.lastError?.at || null,
    lastErrorType: meta.lastError?.type || null,
    lastErrorMessage: meta.lastError?.message || null,
    lastBlockMarker: meta.lastError?.details?.blockMarker || null,
    consecutiveFailures: meta.consecutiveFailures || 0,
    blockStreak: meta.blockStreak || 0,
    recoveryMode: Boolean(meta.recoveryMode),
    recoverySuccesses: meta.recoverySuccesses || 0,
    nextAlarmAt: meta.nextAlarmAt || null,
    sleepingUntil: sleeping ? meta.sleepingUntil || new Date(nextActiveStart(now)).toISOString() : null,
  };
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

async function sendDebugSuccessTelegram(env, message) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) {
    throw new Error("TELEGRAM_BOT_TOKEN/TELEGRAM_CHANNEL_ID Worker secrets are not configured");
  }

  const endpoint = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      chat_id: env.TELEGRAM_CHANNEL_ID,
      text: message,
      disable_web_page_preview: true,
    }),
  });
  const responseText = await response.text();
  if (!response.ok) {
    throw new Error(`Telegram debug send failed HTTP ${response.status}: ${responseText.slice(0, 250)}`);
  }
}

function normalizedRequestUrl(input) {
  try {
    if (typeof input === "string") return new URL(input).toString();
    if (input instanceof URL) return input.toString();
    if (input instanceof Request) return new URL(input.url).toString();
  } catch {
    return "";
  }
  return "";
}

async function browserRunSourceResponse(env) {
  try {
    const response = await env.BROWSER.quickAction("content", {
      url: env.LAZADA_URL,
      cacheTTL: 0,
      gotoOptions: {
        waitUntil: "networkidle2",
        timeout: BROWSER_RUN_TIMEOUT_MS,
      },
    });

    const raw = await response.text();
    if (!response.ok) {
      return new Response(`Browser Run HTTP ${response.status}: ${raw.slice(0, 500)}`, {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    let envelope;
    try {
      envelope = JSON.parse(raw);
    } catch {
      return new Response(`Browser Run returned invalid JSON: ${raw.slice(0, 500)}`, {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    if (!envelope?.success || typeof envelope.result !== "string") {
      return new Response(`Browser Run returned no HTML: ${raw.slice(0, 500)}`, {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    return new Response(envelope.result, {
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "x-alert-source-engine": SOURCE_ENGINE_BROWSER_RUN,
      },
    });
  } catch (error) {
    return new Response(`Browser Run exception: ${String(error?.message || error).slice(0, 500)}`, {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
}

// Conservative adaptive polling. Browser Run is used for the Lazada navigation
// when the BROWSER binding exists; all other fetches (including Telegram) still
// use the normal Workers fetch implementation. Checks run 08:00-24:00 SGT,
// while authenticated manual checks are allowed outside that window for testing.
export class LazadaMonitor extends BaseLazadaMonitor {
  healthyIntervalMs() {
    return asInt(this.env.CHECK_INTERVAL_SECONDS, DEFAULT_HEALTHY_INTERVAL_SECONDS, 15, 3600) * 1000;
  }

  recoveryIntervalMs() {
    return asInt(this.env.RECOVERY_INTERVAL_SECONDS, DEFAULT_RECOVERY_INTERVAL_SECONDS, 30, 3600) * 1000;
  }

  recoverySuccessTarget() {
    return asInt(this.env.RECOVERY_SUCCESS_TARGET, DEFAULT_RECOVERY_SUCCESS_TARGET, 1, 1000);
  }

  blockBackoffBaseSeconds() {
    return asInt(
      this.env.BLOCK_BACKOFF_SECONDS,
      DEFAULT_BLOCK_BACKOFF_SECONDS,
      5 * 60,
      MAX_BLOCK_BACKOFF_SECONDS,
    );
  }

  debugSuccessNotificationsEnabled() {
    return asBool(this.env.DEBUG_NOTIFY_SUCCESS, false);
  }

  browserRunEnabled() {
    return Boolean(this.env.BROWSER?.quickAction && this.env.LAZADA_URL);
  }

  sourceEngine() {
    return this.browserRunEnabled() ? SOURCE_ENGINE_BROWSER_RUN : SOURCE_ENGINE_WORKER_FETCH;
  }

  intervalMs() {
    return this._currentRecoveryMode ? this.recoveryIntervalMs() : this.healthyIntervalMs();
  }

  blockBackoffMs() {
    return blockBackoffSeconds(
      this._pendingBlockStreak || 1,
      this.blockBackoffBaseSeconds(),
    ) * 1000;
  }

  async schedule(meta, delayMs) {
    const requestedAt = Date.now() + delayMs;
    if (isActiveSgt(requestedAt)) {
      meta.sleepingUntil = null;
      return super.schedule(meta, delayMs);
    }

    const wakeAt = nextActiveStart(requestedAt);
    await this.state.storage.setAlarm(wakeAt);
    meta.nextAlarmAt = new Date(wakeAt).toISOString();
    meta.nextAllowedCheckAt = wakeAt;
    meta.sleepingUntil = meta.nextAlarmAt;
    this.log(meta, "monitor.sleep.scheduled", {
      requestedAt: new Date(requestedAt).toISOString(),
      nextAlarmAt: meta.nextAlarmAt,
      sleepingUntil: meta.sleepingUntil,
      activeWindowSgt: "08:00-24:00",
    });
  }

  async runCheckWithSourceEngine(trigger, loaded) {
    const sourceEngine = this.sourceEngine();
    const sourceUrl = normalizedRequestUrl(this.env.LAZADA_URL || "");

    // A historical block streak from direct Worker fetches should not force a
    // brand-new Browser Run transport straight into the 8-hour backoff cap.
    if (sourceEngine === SOURCE_ENGINE_BROWSER_RUN && loaded.meta.sourceEngine !== sourceEngine) {
      this.log(loaded.meta, "monitor.source_engine.changed", {
        previous: loaded.meta.sourceEngine || null,
        current: sourceEngine,
        resetBlockState: true,
      });
      loaded.meta.blockStreak = 0;
      loaded.meta.recoveryMode = false;
      loaded.meta.recoverySuccesses = 0;
      loaded.meta.consecutiveFailures = 0;
    }
    loaded.meta.sourceEngine = sourceEngine;

    if (sourceEngine !== SOURCE_ENGINE_BROWSER_RUN) {
      return super.runCheck(trigger, loaded.inventory, loaded.meta);
    }

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input, init = undefined) => {
      const url = normalizedRequestUrl(input);
      const requestMethod = String(
        init?.method || (input instanceof Request ? input.method : "GET"),
      ).toUpperCase();

      if (requestMethod === "GET" && url && url === sourceUrl) {
        return browserRunSourceResponse(this.env);
      }
      return originalFetch(input, init);
    };

    try {
      return await super.runCheck(trigger, loaded.inventory, loaded.meta);
    } finally {
      globalThis.fetch = originalFetch;
    }
  }

  async runCheck(trigger, inventoryArg = null, metaArg = null) {
    if (!isActiveSgt() && trigger !== "manual") {
      const loaded = inventoryArg && metaArg
        ? { inventory: inventoryArg, meta: metaArg }
        : await this.loadState();
      const wakeAt = nextActiveStart();
      await this.state.storage.setAlarm(wakeAt);
      loaded.meta.nextAlarmAt = new Date(wakeAt).toISOString();
      loaded.meta.nextAllowedCheckAt = wakeAt;
      loaded.meta.sleepingUntil = loaded.meta.nextAlarmAt;
      this.log(loaded.meta, "monitor.sleeping", {
        trigger,
        nextAlarmAt: loaded.meta.nextAlarmAt,
        sleepingUntil: loaded.meta.sleepingUntil,
        activeWindowSgt: "08:00-24:00",
      });
      await this.persist(loaded.inventory, loaded.meta);
      return {
        ok: true,
        skipped: true,
        reason: "outside_active_window",
        sleepingUntil: loaded.meta.sleepingUntil,
      };
    }

    const loaded = inventoryArg && metaArg
      ? { inventory: inventoryArg, meta: metaArg }
      : await this.loadState();

    this._currentRecoveryMode = Boolean(loaded.meta.recoveryMode);
    this._pendingBlockStreak = Number(loaded.meta.blockStreak || 0) + 1;

    const result = await this.runCheckWithSourceEngine(trigger, loaded);

    if (result?.blocked) {
      const { inventory, meta } = await this.loadState();
      meta.sourceEngine = this.sourceEngine();
      meta.blockStreak = this._pendingBlockStreak;
      meta.recoveryMode = true;
      meta.recoverySuccesses = 0;
      const delaySeconds = blockBackoffSeconds(meta.blockStreak, this.blockBackoffBaseSeconds());
      this.log(meta, "monitor.block_backoff", {
        trigger,
        sourceEngine: meta.sourceEngine,
        blockStreak: meta.blockStreak,
        delaySeconds,
        nextAlarmAt: meta.nextAlarmAt || null,
      });
      await this.persist(inventory, meta);
      return result;
    }

    if (result?.ok) {
      const { inventory, meta } = await this.loadState();
      meta.sourceEngine = this.sourceEngine();
      if (meta.lastSource && typeof meta.lastSource === "object") {
        meta.lastSource.engine = meta.sourceEngine;
      }
      if (meta.recoveryMode) {
        meta.recoverySuccesses = Number(meta.recoverySuccesses || 0) + 1;
        const target = this.recoverySuccessTarget();

        if (meta.recoverySuccesses >= target) {
          meta.recoveryMode = false;
          meta.recoverySuccesses = 0;
          meta.blockStreak = 0;
          this._currentRecoveryMode = false;
          this.log(meta, "monitor.recovery.complete", {
            trigger,
            healthyIntervalSeconds: this.healthyIntervalMs() / 1000,
          });
          await this.schedule(meta, this.healthyIntervalMs());
        } else {
          this.log(meta, "monitor.recovery.progress", {
            trigger,
            successes: meta.recoverySuccesses,
            target,
            intervalSeconds: this.recoveryIntervalMs() / 1000,
          });
        }
      } else {
        meta.blockStreak = 0;
        meta.recoverySuccesses = 0;
      }

      if (this.debugSuccessNotificationsEnabled()) {
        try {
          const trackedSkus = Object.keys(inventory).length;
          const availableSkus = Object.values(inventory).filter((item) => item?.available === true).length;
          const debugMessage = [
            "✅ Lazada monitor debug: scrape succeeded",
            `Trigger: ${trigger}`,
            `Engine: ${meta.sourceEngine}`,
            `Checked: ${meta.lastSuccessAt || new Date().toISOString()}`,
            `Restocks detected: ${Number(result.restocked || 0)}`,
            `Tracked SKUs: ${trackedSkus}`,
            `Available SKUs: ${availableSkus}`,
            `Mode: ${meta.recoveryMode ? "recovery" : "healthy"}`,
            `Next alarm: ${meta.nextAlarmAt || "not scheduled"}`,
            "DEBUG_NOTIFY_SUCCESS=true",
          ].join("\n");

          await sendDebugSuccessTelegram(this.env, debugMessage);
          this.log(meta, "telegram.debug_success.sent", {
            trigger,
            runId: result.runId || null,
            restockedSkus: Number(result.restocked || 0),
            trackedSkus,
            availableSkus,
          });
        } catch (error) {
          this.log(meta, "telegram.debug_success.error", {
            trigger,
            runId: result.runId || null,
            message: String(error?.message || error),
          });
        }
      }

      await this.persist(inventory, meta);
    }

    return result;
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/healthz") {
      const { meta } = await this.loadState();
      return jsonResponse(monitorHealth(meta));
    }

    if (request.method === "GET" && url.pathname === "/debug") {
      const response = await super.fetch(request);
      const payload = await response.json();
      const { meta } = await this.loadState();
      const baseBackoff = this.blockBackoffBaseSeconds();
      payload.health = monitorHealth(meta);
      payload.config = {
        ...(payload.config || {}),
        sourceEngine: this.sourceEngine(),
        browserRunEnabled: this.browserRunEnabled(),
        browserRunTimeoutMs: BROWSER_RUN_TIMEOUT_MS,
        checkIntervalSeconds: this.healthyIntervalMs() / 1000,
        recoveryIntervalSeconds: this.recoveryIntervalMs() / 1000,
        recoverySuccessTarget: this.recoverySuccessTarget(),
        blockBackoffSeconds: baseBackoff,
        blockBackoffMaxSeconds: MAX_BLOCK_BACKOFF_SECONDS,
        blockBackoffSequenceSeconds: [1, 2, 3, 4, 5, 6].map((streak) => blockBackoffSeconds(streak, baseBackoff)),
        debugNotifySuccess: this.debugSuccessNotificationsEnabled(),
        activeWindowSgt: "08:00-24:00",
        backgroundChecksOutsideWindow: false,
        authenticatedManualChecksOutsideWindow: true,
      };
      return jsonResponse(payload, response.status);
    }

    return super.fetch(request);
  }
}

export default worker;
