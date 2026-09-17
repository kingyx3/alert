import test from "node:test";
import assert from "node:assert/strict";

import { LazadaMonitor } from "../src/dispatcher-entry.js";

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
    name: "Pokémon TCG Test Product",
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

test("duplicate Cloudflare deliveries claim a 10-second dispatch key only once", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {});

  const first = await monitor.claimGithubDispatch("cf-59654269");
  const duplicate = await monitor.claimGithubDispatch("cf-59654269");
  const nextSlot = await monitor.claimGithubDispatch("cf-59654270");

  assert.deepEqual(first, { ok: true, claimed: true, dispatchKey: "cf-59654269" });
  assert.deepEqual(duplicate, { ok: true, claimed: false, dispatchKey: "cf-59654269" });
  assert.deepEqual(nextSlot, { ok: true, claimed: true, dispatchKey: "cf-59654270" });
});

test("concurrent claims for the same dispatch key serialize to one winner", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {});

  const results = await Promise.all([
    monitor.claimGithubDispatch("cf-70000000"),
    monitor.claimGithubDispatch("cf-70000000"),
    monitor.claimGithubDispatch("cf-70000000"),
  ]);

  assert.equal(results.filter((result) => result.claimed).length, 1);
  assert.equal(results.filter((result) => !result.claimed).length, 2);
});

test("stock alerts repeat on the next 10-second batch but not across sources in the same batch", async () => {
  const state = makeState();
  const monitor = new LazadaMonitor(state, {
    EXTERNAL_SNAPSHOT_MODE: "true",
    TCG_KEYWORDS: "pokemon,pokémon,tcg,trading card",
    MISSING_CONFIRMATIONS: "2",
    ALERT_ON_FIRST_RUN: "true",
    TELEGRAM_BOT_TOKEN: "test-bot-token",
    TELEGRAM_CHANNEL_ID: "test-channel",
  });

  const originalFetch = globalThis.fetch;
  let telegramCalls = 0;
  globalThis.fetch = async (url) => {
    const target = String(url);
    if (!target.startsWith("https://api.telegram.org/")) {
      throw new Error(`Unexpected fetch: ${target}`);
    }
    telegramCalls += 1;
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const baselineAt = new Date(Date.now() - 5000).toISOString();
    await monitor.ingestSnapshot({
      batchId: "baseline",
      runnerSlot: "1",
      checkedAt: baselineAt,
      products: [product({ inStock: false })],
      complete: true,
    });
    assert.equal(telegramCalls, 0);

    const firstStockAt = new Date(Date.now() - 3000).toISOString();
    const first = await monitor.ingestSnapshot({
      batchId: "cf-100:source-1",
      runnerSlot: "1",
      checkedAt: firstStockAt,
      products: [product({ inStock: true })],
      complete: false,
    });
    assert.equal(first.ok, true);
    assert.equal(telegramCalls, 1, "stock transition should alert immediately");

    const sameBatchAt = new Date(Date.now() - 2000).toISOString();
    const sameBatch = await monitor.ingestSnapshot({
      batchId: "cf-100:source-2",
      runnerSlot: "2",
      checkedAt: sameBatchAt,
      products: [product({ inStock: true })],
      complete: false,
    });
    assert.equal(sameBatch.ok, true);
    assert.equal(telegramCalls, 1, "second source in the same root batch must not duplicate the alert");

    const nextBatchAt = new Date(Date.now() - 1000).toISOString();
    const stillInStock = await monitor.ingestSnapshot({
      batchId: "cf-101:source-1",
      runnerSlot: "1",
      checkedAt: nextBatchAt,
      products: [product({ inStock: true })],
      complete: false,
    });
    assert.equal(stillInStock.ok, true);
    assert.equal(telegramCalls, 2, "next 10-second root batch should alert again while stock remains");
    assert.equal(state.values.get("meta").lastAlertBatchId, "cf-101");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
