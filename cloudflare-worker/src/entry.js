import worker, { LazadaMonitor as BaseLazadaMonitor } from "./index.js";

const SGT_OFFSET_MS = 8 * 60 * 60 * 1000;
const ACTIVE_START_HOUR_SGT = 8;
const DEFAULT_HEALTHY_INTERVAL_SECONDS = 30;
const DEFAULT_RECOVERY_INTERVAL_SECONDS = 60;
const DEFAULT_RECOVERY_SUCCESS_TARGET = 20;
const DEFAULT_BLOCK_BACKOFF_SECONDS = 15 * 60;
const MAX_BLOCK_BACKOFF_SECONDS = 8 * 60 * 60;

function asInt(value, fallback, min = 1, max = Number.MAX_SAFE_INTEGER) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
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
    lastCheckAt: meta.lastCheckAt || null,
    lastSuccessAt: meta.lastSuccessAt || null,
    lastAlertAt: meta.lastAlertAt || null,
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

// Conservative adaptive polling: 30s normally. A Lazada block/challenge backs off
// 15m -> 30m -> 1h -> 2h -> 4h -> 8h, then remains capped at 8h.
// After access recovers, poll at 60s for 20 clean checks, then return to the
// 30-second healthy cadence. Checks only run 08:00-24:00 SGT.
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

  async runCheck(trigger, inventoryArg = null, metaArg = null) {
    if (!isActiveSgt()) {
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

    const result = await super.runCheck(trigger, loaded.inventory, loaded.meta);

    if (result?.blocked) {
      const { inventory, meta } = await this.loadState();
      meta.blockStreak = this._pendingBlockStreak;
      meta.recoveryMode = true;
      meta.recoverySuccesses = 0;
      const delaySeconds = blockBackoffSeconds(meta.blockStreak, this.blockBackoffBaseSeconds());
      this.log(meta, "monitor.block_backoff", {
        trigger,
        blockStreak: meta.blockStreak,
        delaySeconds,
        nextAlarmAt: meta.nextAlarmAt || null,
      });
      await this.persist(inventory, meta);
      return result;
    }

    if (result?.ok) {
      const { inventory, meta } = await this.loadState();
      if (meta.recoveryMode) {
        meta.recoverySuccesses = Number(meta.recoverySuccesses || 0) + 1;
        const target = this.recoverySuccessTarget();

        if (meta.recoverySuccesses >= target) {
          meta.recoveryMode = false;
          meta.recoverySuccesses = 0;
          meta.blockStreak = 0;
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
        checkIntervalSeconds: this.healthyIntervalMs() / 1000,
        recoveryIntervalSeconds: this.recoveryIntervalMs() / 1000,
        recoverySuccessTarget: this.recoverySuccessTarget(),
        blockBackoffSeconds: baseBackoff,
        blockBackoffMaxSeconds: MAX_BLOCK_BACKOFF_SECONDS,
        blockBackoffSequenceSeconds: [1, 2, 3, 4, 5, 6].map((streak) => blockBackoffSeconds(streak, baseBackoff)),
        activeWindowSgt: "08:00-24:00",
        backgroundChecksOutsideWindow: false,
      };
      return jsonResponse(payload, response.status);
    }

    return super.fetch(request);
  }
}

export default worker;
