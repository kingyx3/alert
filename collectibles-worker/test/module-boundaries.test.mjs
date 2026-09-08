import test from "node:test";
import assert from "node:assert/strict";
import worker, { CollectiblesMonitor } from "../src/index.js";
import { MARKET_PROVIDERS } from "../src/market/index.js";
import { SOCIAL_ADAPTERS } from "../src/social/index.js";
import { DEFAULT_SOURCES, loadSources } from "../src/sources/index.js";
import { PRODUCT_PARSERS } from "../src/sources/web.js";
import { DEFAULT_USD_SGD } from "../src/core/config.js";

test("entrypoint exports Worker and Durable Object class", () => {
  assert.equal(typeof worker.fetch, "function");
  assert.equal(typeof worker.scheduled, "function");
  assert.equal(typeof CollectiblesMonitor, "function");
});

test("market providers are registered independently", () => {
  assert.ok(MARKET_PROVIDERS.length >= 2);
  assert.ok(MARKET_PROVIDERS.every((provider) => provider.id && typeof provider.supports === "function" && typeof provider.query === "function"));
});

test("social polling is adapter based", () => {
  assert.ok(SOCIAL_ADAPTERS.length >= 1);
  assert.ok(SOCIAL_ADAPTERS.every((adapter) => adapter.id && typeof adapter.loadAccounts === "function" && typeof adapter.fetchPosts === "function"));
});

test("website parsers and source catalog are independently extensible", () => {
  assert.equal(typeof PRODUCT_PARSERS.generic, "function");
  assert.ok(DEFAULT_SOURCES.length >= 16);
  assert.equal(loadSources({}).length, DEFAULT_SOURCES.length);
});

test("USD SGD fallback remains 1.30", () => {
  assert.equal(DEFAULT_USD_SGD, 1.30);
});
