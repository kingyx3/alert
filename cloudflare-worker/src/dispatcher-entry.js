import ghaWorker, { LazadaMonitor as ExternalSnapshotMonitor } from "./gha-entry.js";

const DEFAULT_GITHUB_REPOSITORY = "kingyx3/alert";
const DEFAULT_GITHUB_WORKFLOW = "lazada-playwright-probe.yml";
const DEFAULT_GITHUB_REF = "main";
const DISPATCH_INTERVAL_MS = 10 * 1000;
const DISPATCHES_PER_CRON = 60 * 1000 / DISPATCH_INTERVAL_MS;
const DISPATCH_CLAIMS_STORAGE_KEY = "githubDispatchClaims";
const DISPATCH_CLAIM_TTL_MS = 5 * 60 * 1000;

export class LazadaMonitor extends ExternalSnapshotMonitor {
  async ingestSnapshot(payload) {
    // Serialize snapshot decisions inside this Durable Object instance. The first
    // clean runner can send Telegram immediately, while later runners wait only
    // for that ingestion decision instead of racing and duplicating an alert.
    const previousIngest = this._ingestTail || Promise.resolve();
    let releaseIngest;
    this._ingestTail = new Promise((resolve) => {
      releaseIngest = resolve;
    });

    await previousIngest;
    try {
      const batchId = String(payload?.batchId || "").trim();
      const checkedAt = String(payload?.checkedAt || "").trim();
      const checkedAtMs = Date.parse(checkedAt);

      if (batchId && Number.isFinite(checkedAtMs)) {
        const loaded = await this.loadState();
        const lastSuccessMs = loaded.meta.lastSuccessAt ? Date.parse(loaded.meta.lastSuccessAt) : 0;
        if (
          loaded.meta.lastIngestBatchId &&
          loaded.meta.lastIngestBatchId !== batchId &&
          Number.isFinite(lastSuccessMs) &&
          lastSuccessMs >= checkedAtMs
        ) {
          this.log(loaded.meta, "external.snapshot.superseded", {
            batchId,
            checkedAt,
            acceptedBatchId: loaded.meta.lastIngestBatchId,
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

      return await super.ingestSnapshot(payload);
    } finally {
      releaseIngest();
    }
  }

  async claimGithubDispatch(dispatchKey) {
    // Cloudflare may deliver the same cron slot more than once. Serialize claims
    // through the singleton Durable Object and persist recent keys so duplicate
    // scheduled events cannot create duplicate GitHub workflow_dispatch runs.
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
  const config = dispatchConfig(env);
  if (!config.configured) {
    return { ok: false, skipped: true, reason: "github_actions_token_missing" };
  }

  const dispatchKey = dispatchKeyFor(scheduledTime);
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
        scheduled_at: new Date(Number(scheduledTime || Date.now())).toISOString(),
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
    scheduledAt: new Date(Number(scheduledTime || Date.now())).toISOString(),
  };
}

async function dispatchAndLog(env, scheduledTime, slot) {
  const dispatchKey = dispatchKeyFor(scheduledTime);
  try {
    const claim = await claimGithubDispatchSlot(env, dispatchKey);
    if (!claim.claimed) {
      const result = {
        ok: true,
        skipped: true,
        reason: "duplicate_dispatch_key",
        dispatchKey,
        scheduledAt: new Date(Number(scheduledTime || Date.now())).toISOString(),
      };
      console.log(`GitHub workflow ${slot} duplicate skipped`, result);
      return result;
    }

    const result = await dispatchGithubWorkflow(env, scheduledTime);
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
