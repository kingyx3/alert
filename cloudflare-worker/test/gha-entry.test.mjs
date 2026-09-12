import test from "node:test";
import assert from "node:assert/strict";

import { LazadaMonitor, dispatchGithubWorkflow } from "../src/dispatcher-entry.js";

function makeState() {
  const values = new Map();
  return {
    storage: {
      async get(key) {
        return values.get(key);
      },
      async put(entries) {
        for (const [key, value] of Object.entries(entries)) values.set(key, value);
      },
      async deleteAlarm() {},
      async setAlarm() {},
      async getAlarm() {
        return null;
      },
    },
    values,
  };
}

function product(overrides = {}) {
  return {
    name: "Pokémon Trading Card Game Test Product",
    price: 10,
    priceShow: "$10.00",
    inStock: false,
    sold: "",
    url: "https://www.lazada.sg/products/test.html",
    image: null,
    skuId: "1001",
    sku: "TEST_SKU",
    sellerName: "Pokémon Store Online Singapore",
    sellerId: "1628720011",
    ...overrides,
  };
}

test("external snapshots are accepted once per GHA batch", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {
    EXTERNAL_SNAPSHOT_MODE: "true",
    TCG_KEYWORDS: "pokemon,pokémon,tcg,trading card",
    MISSING_CONFIRMATIONS: "2",
    ALERT_ON_FIRST_RUN: "false",
  });

  const checkedAt = new Date().toISOString();
  const first = await monitor.ingestSnapshot({
    batchId: "run-1",
    runnerSlot: "1",
    checkedAt,
    httpStatus: 200,
    finalUrl: "https://www.lazada.sg/pokemon-store-online-singapore/",
    products: [
      product(),
      product({
        name: "Pokémon TCG Second Product",
        skuId: "1002",
        sku: "TEST_SKU_2",
        url: "https://www.lazada.sg/products/test-2.html",
      }),
    ],
  });

  assert.equal(first.ok, true);
  assert.equal(first.duplicate, false);
  assert.equal(first.products, 2);

  const duplicate = await monitor.ingestSnapshot({
    batchId: "run-1",
    runnerSlot: "2",
    checkedAt: new Date().toISOString(),
    products: [product()],
  });
  assert.equal(duplicate.ok, true);
  assert.equal(duplicate.duplicate, true);

  let inventory = state.values.get("inventory");
  assert.equal(Object.keys(inventory).length, 2);
  assert.equal(inventory["skuId:1002"].missingStreak, 0);

  const secondBatch = await monitor.ingestSnapshot({
    batchId: "run-2",
    runnerSlot: "3",
    checkedAt: new Date(Date.now() + 10).toISOString(),
    products: [product()],
  });
  assert.equal(secondBatch.ok, true);
  assert.equal(secondBatch.duplicate, false);

  inventory = state.values.get("inventory");
  assert.equal(inventory["skuId:1002"].missingStreak, 1);

  const meta = state.values.get("meta");
  assert.equal(meta.sourceEngine, "github-actions-playwright");
  assert.equal(meta.lastIngestBatchId, "run-2");
  assert.equal(meta.consecutiveFailures, 0);
  assert.equal(meta.blockStreak, 0);
  assert.equal(meta.recoveryMode, false);
});

test("older overlapping minute snapshots cannot roll inventory backward", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {
    EXTERNAL_SNAPSHOT_MODE: "true",
    TCG_KEYWORDS: "pokemon,pokémon,tcg,trading card",
    MISSING_CONFIRMATIONS: "2",
    ALERT_ON_FIRST_RUN: "false",
  });

  const newerCheckedAt = new Date(Date.now() - 1000).toISOString();
  const olderCheckedAt = new Date(Date.now() - 61000).toISOString();

  const newer = await monitor.ingestSnapshot({
    batchId: "cf-200",
    runnerSlot: "1",
    checkedAt: newerCheckedAt,
    products: [product({ inStock: false })],
  });
  assert.equal(newer.ok, true);
  assert.equal(newer.superseded, undefined);

  const older = await monitor.ingestSnapshot({
    batchId: "cf-199",
    runnerSlot: "1",
    checkedAt: olderCheckedAt,
    products: [product({ inStock: true })],
  });
  assert.equal(older.ok, true);
  assert.equal(older.superseded, true);
  assert.equal(older.acceptedBatchId, "cf-200");

  const inventory = state.values.get("inventory");
  assert.equal(inventory["skuId:1001"].available, false);
  const meta = state.values.get("meta");
  assert.equal(meta.lastIngestBatchId, "cf-200");
  assert.equal(meta.lastSuccessAt, newerCheckedAt);
});

test("first clean concurrent runner sends exactly one Telegram restock alert", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {
    EXTERNAL_SNAPSHOT_MODE: "true",
    TCG_KEYWORDS: "pokemon,pokémon,tcg,trading card",
    MISSING_CONFIRMATIONS: "2",
    ALERT_ON_FIRST_RUN: "false",
    TELEGRAM_BOT_TOKEN: "test-bot-token",
    TELEGRAM_CHANNEL_ID: "test-channel",
  });

  const initialCheckedAt = new Date(Date.now() - 5000).toISOString();
  await monitor.ingestSnapshot({
    batchId: "cf-initial",
    runnerSlot: "1",
    checkedAt: initialCheckedAt,
    products: [product({ inStock: false })],
  });

  const originalFetch = globalThis.fetch;
  let telegramCalls = 0;
  let markTelegramStarted;
  let releaseTelegram;
  const telegramStarted = new Promise((resolve) => {
    markTelegramStarted = resolve;
  });
  const telegramRelease = new Promise((resolve) => {
    releaseTelegram = resolve;
  });

  globalThis.fetch = async (url) => {
    const target = String(url);
    if (!target.startsWith("https://api.telegram.org/")) {
      throw new Error(`Unexpected fetch in alert test: ${target}`);
    }
    telegramCalls += 1;
    markTelegramStarted();
    await telegramRelease;
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const checkedAt = new Date(Date.now() - 1000).toISOString();
    const firstRunner = monitor.ingestSnapshot({
      batchId: "cf-restock",
      runnerSlot: "1",
      checkedAt,
      products: [product({ inStock: true })],
    });

    await telegramStarted;

    const secondRunner = monitor.ingestSnapshot({
      batchId: "cf-restock",
      runnerSlot: "2",
      checkedAt,
      products: [product({ inStock: true })],
    });

    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(telegramCalls, 1, "later runners must not race the active Telegram alert");

    releaseTelegram();
    const [first, second] = await Promise.all([firstRunner, secondRunner]);

    assert.equal(first.ok, true);
    assert.equal(first.restocked, 1);
    assert.equal(second.ok, true);
    assert.equal(second.duplicate, true);
    assert.equal(telegramCalls, 1);
    assert.equal(state.values.get("meta").lastAlertAt, checkedAt);
  } finally {
    releaseTelegram();
    globalThis.fetch = originalFetch;
  }
});

test("Cloudflare dispatcher safely skips when no GitHub token is configured", async () => {
  const result = await dispatchGithubWorkflow({}, Date.UTC(2026, 8, 12, 0, 3, 0));
  assert.deepEqual(result, {
    ok: false,
    skipped: true,
    reason: "github_actions_token_missing",
  });
});

test("Cloudflare dispatcher sends workflow_dispatch with a stable minute key", async () => {
  const originalFetch = globalThis.fetch;
  let request = null;
  globalThis.fetch = async (url, init) => {
    request = { url: String(url), init };
    return new Response(null, { status: 204 });
  };

  try {
    const scheduledTime = Date.UTC(2026, 8, 12, 0, 3, 0);
    const result = await dispatchGithubWorkflow({
      GITHUB_ACTIONS_TOKEN: "test-token",
      GITHUB_DISPATCH_REPOSITORY: "kingyx3/alert",
      GITHUB_DISPATCH_WORKFLOW: "lazada-playwright-probe.yml",
      GITHUB_DISPATCH_REF: "main",
    }, scheduledTime);

    assert.equal(result.ok, true);
    assert.equal(result.status, 204);
    assert.equal(result.dispatchKey, `cf-${Math.floor(scheduledTime / 60000)}`);
    assert.equal(
      request.url,
      "https://api.github.com/repos/kingyx3/alert/actions/workflows/lazada-playwright-probe.yml/dispatches",
    );
    assert.equal(request.init.method, "POST");
    assert.equal(request.init.headers.authorization, "Bearer test-token");

    const body = JSON.parse(request.init.body);
    assert.equal(body.ref, "main");
    assert.equal(body.inputs.trigger_source, "cloudflare-cron");
    assert.equal(body.inputs.dispatch_key, result.dispatchKey);
    assert.equal(body.inputs.scheduled_at, new Date(scheduledTime).toISOString());
  } finally {
    globalThis.fetch = originalFetch;
  }
});
