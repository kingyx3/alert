import ghaWorker, { LazadaMonitor as ExternalSnapshotMonitor } from "./gha-entry.js";

const DEFAULT_GITHUB_REPOSITORY = "kingyx3/alert";
const DEFAULT_GITHUB_WORKFLOW = "lazada-playwright-probe.yml";
const DEFAULT_GITHUB_REF = "main";
const DISPATCH_BUCKET_MS = 60 * 1000;

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

export async function dispatchGithubWorkflow(env, scheduledTime = Date.now()) {
  const config = dispatchConfig(env);
  if (!config.configured) {
    return { ok: false, skipped: true, reason: "github_actions_token_missing" };
  }

  const dispatchKey = `cf-${Math.floor(Number(scheduledTime || Date.now()) / DISPATCH_BUCKET_MS)}`;
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

    ctx.waitUntil(
      dispatchGithubWorkflow(env, scheduledTime)
        .then((result) => console.log("GitHub workflow dispatch accepted", result))
        .catch((error) => console.error("GitHub workflow dispatch failed", String(error?.message || error))),
    );
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/schedulerz") {
      const config = dispatchConfig(env);
      return jsonResponse({
        status: config.configured ? "ok" : "fallback",
        scheduler: "cloudflare-cron",
        frequencySeconds: 60,
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
