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

function secondProduct(overrides = {}) {
  return product({
    name: "Pokémon TCG Second Product",
    skuId: "1002",
    sku: "TEST_SKU_2",
    url: "https://www.lazada.sg/products/test-2.html",
    ...overrides,
  });
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

test("same-batch alert deduplication is SKU-specific across URL 1 and URL 2", async () => {
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
  const telegramBodies = [];
  globalThis.fetch = async (url, init) => {
    const target = String(url);
    if (!target.startsWith("https://api.telegram.org/")) {
      throw new Error(`Unexpected fetch: ${target}`);
    }
    telegramBodies.push(JSON.parse(init.body));
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
      products: [product({ inStock: false }), secondProduct({ inStock: false })],
      complete: true,
    });
    assert.equal(telegramBodies.length, 0);

    const url1At = new Date(Date.now() - 3000).toISOString();
    const url1 = await monitor.ingestSnapshot({
      batchId: "cf-100:source-1",
      runnerSlot: "1",
      checkedAt: url1At,
      products: [product({ inStock: true })],
      complete: false,
    });
    assert.equal(url1.ok, true);
    assert.equal(telegramBodies.length, 1, "URL 1 should alert SKU 1001");
    assert.match(telegramBodies[0].text, /1001/);

    const url2At = new Date(Date.now() - 2000).toISOString();
    const url2 = await monitor.ingestSnapshot({
      batchId: "cf-100:source-2",
      runnerSlot: "2",
      checkedAt: url2At,
      products: [product({ inStock: true }), secondProduct({ inStock: true })],
      complete: false,
    });
    assert.equal(url2.ok, true);
    assert.equal(telegramBodies.length, 2, "URL 2 must still alert its newly found SKU 1002");
    assert.match(telegramBodies[1].text, /1002/);
    assert.doesNotMatch(telegramBodies[1].text, /SKU: 1001/);

    const sameBatchDuplicate = await monitor.ingestSnapshot({
      batchId: "cf-100:source-2",
      runnerSlot: "3",
      checkedAt: new Date(Date.now() - 1500).toISOString(),
      products: [product({ inStock: true }), secondProduct({ inStock: true })],
      complete: false,
    });
    assert.equal(sameBatchDuplicate.ok, true);
    assert.equal(telegramBodies.length, 2, "same SKUs in the same root batch must remain deduplicated");

    const nextBatchAt = new Date(Date.now() - 1000).toISOString();
    const stillInStock = await monitor.ingestSnapshot({
      batchId: "cf-101:source-1",
      runnerSlot: "1",
      checkedAt: nextBatchAt,
      products: [product({ inStock: true }), secondProduct({ inStock: true })],
      complete: false,
    });
    assert.equal(stillInStock.ok, true);
    assert.equal(telegramBodies.length, 3, "next 10-second batch should alert both still-in-stock SKUs again");
    assert.match(telegramBodies[2].text, /1001/);
    assert.match(telegramBodies[2].text, /1002/);

    const meta = state.values.get("meta");
    assert.equal(meta.lastAlertBatchId, "cf-101");
    assert.deepEqual(new Set(meta.lastAlertSkuKeys), new Set(["skuId:1001", "skuId:1002"]));
  } finally {
    globalThis.fetch = originalFetch;
  }
});
