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
    return incomingSequence < acceptedSequence;
  }

  const lastSuccessMs = meta?.lastSuccessAt ? Date.parse(meta.lastSuccessAt) : 0;
  return Number.isFinite(lastSuccessMs) && Number.isFinite(checkedAtMs) && lastSuccessMs >= checkedAtMs;
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

      if (batchId && Number.isFinite(checkedAtMs)) {
        const loaded = await this.loadState();
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

      // Alert decisions are intentionally delegated to the base snapshot monitor,
      // which only sends Telegram for first-run alerts (when enabled) or genuine
      // unavailable -> available transitions. Do not re-alert merely because an
      // already-available SKU appears in a later dispatch batch.
      return await super.ingestSnapshot(payload);
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
