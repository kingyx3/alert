import test from "node:test";
import assert from "node:assert/strict";

import { LazadaMonitor } from "../src/gha-entry.js";

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
    checkedAt: new Date().toISOString(),
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
