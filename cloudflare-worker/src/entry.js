import worker, { LazadaMonitor as BaseLazadaMonitor } from "./index.js";

const SGT_OFFSET_MS = 8 * 60 * 60 * 1000;
const ACTIVE_START_HOUR_SGT = 8;

function sgtDate(timestamp = Date.now()) {
  return new Date(timestamp + SGT_OFFSET_MS);
}

function isActiveSgt(timestamp = Date.now()) {
  // Active every day from 08:00:00 SGT through 23:59:59 SGT.
  return sgtDate(timestamp).getUTCHours() >= ACTIVE_START_HOUR_SGT;
}

function nextActiveStart(timestamp = Date.now()) {
  const local = sgtDate(timestamp);
  const year = local.getUTCFullYear();
  const month = local.getUTCMonth();
  const day = local.getUTCDate();
  const localHour = local.getUTCHours();
  const startDay = localHour < ACTIVE_START_HOUR_SGT ? day : day + 1;
  const localStart = Date.UTC(year, month, startDay, ACTIVE_START_HOUR_SGT, 0, 0, 0);
  return localStart - SGT_OFFSET_MS;
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
    lastCheckAt: meta.lastCheckAt || null,
    lastSuccessAt: meta.lastSuccessAt || null,
    lastAlertAt: meta.lastAlertAt || null,
    consecutiveFailures: meta.consecutiveFailures || 0,
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

// Deployment entrypoint for the aggressive healthy-path polling cadence.
// The Durable Object checks every 5 seconds only during 08:00-24:00 SGT.
// Outside that window it has no alarm scheduled; the active-hours Cron Trigger
// wakes it again after 08:00 SGT. Existing source-block/error backoff remains.
export class LazadaMonitor extends BaseLazadaMonitor {
  intervalMs() {
    const parsed = Number.parseInt(String(this.env.CHECK_INTERVAL_SECONDS ?? ""), 10);
    const seconds = Number.isFinite(parsed)
      ? Math.min(3600, Math.max(5, parsed))
      : 5;
    return seconds * 1000;
  }

  async schedule(meta, delayMs) {
    const requestedAt = Date.now() + delayMs;
    if (isActiveSgt(requestedAt)) {
      meta.sleepingUntil = null;
      return super.schedule(meta, delayMs);
    }

    const wakeAt = nextActiveStart(requestedAt);
    await this.state.storage.deleteAlarm();
    meta.nextAlarmAt = null;
    meta.nextAllowedCheckAt = wakeAt;
    meta.sleepingUntil = new Date(wakeAt).toISOString();
    this.log(meta, "monitor.sleep.scheduled", {
      requestedAt: new Date(requestedAt).toISOString(),
      sleepingUntil: meta.sleepingUntil,
      activeWindowSgt: "08:00-24:00",
    });
  }

  async runCheck(trigger, inventoryArg = null, metaArg = null) {
    if (isActiveSgt()) {
      return super.runCheck(trigger, inventoryArg, metaArg);
    }

    const loaded = inventoryArg && metaArg
      ? { inventory: inventoryArg, meta: metaArg }
      : await this.loadState();
    const wakeAt = nextActiveStart();
    await this.state.storage.deleteAlarm();
    loaded.meta.nextAlarmAt = null;
    loaded.meta.nextAllowedCheckAt = wakeAt;
    loaded.meta.sleepingUntil = new Date(wakeAt).toISOString();
    this.log(loaded.meta, "monitor.sleeping", {
      trigger,
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
      payload.health = monitorHealth(meta);
      payload.config = {
        ...(payload.config || {}),
        activeWindowSgt: "08:00-24:00",
        backgroundChecksOutsideWindow: false,
      };
      return jsonResponse(payload, response.status);
    }

    return super.fetch(request);
  }
}

export default worker;
