import test from "node:test";
import assert from "node:assert/strict";
import { loadSocialSources } from "../src/social/index.js";
import { loadXAccounts, xAdapter } from "../src/social/x.js";

test("disabled X adapter does not appear as a healthy polling source", () => {
  const env = { X_ACCOUNTS_JSON: JSON.stringify([{ username: "PokemonTCG" }]) };
  assert.deepEqual(loadSocialSources(env), []);
});

test("configured X adapter loads normalized account handles", () => {
  const env = {
    X_BEARER_TOKEN: "test-token",
    X_ACCOUNTS_JSON: JSON.stringify([
      { username: "  @PokemonTCG  ", name: "Pokemon" },
      { username: "   " },
    ]),
  };
  const accounts = loadXAccounts(env);
  assert.equal(accounts.length, 1);
  assert.equal(accounts[0].username, "PokemonTCG");

  const sources = loadSocialSources(env);
  assert.equal(sources.length, 1);
  assert.equal(sources[0].id, "x:PokemonTCG");
});

test("X cursor advances by numeric post id and never moves backwards", () => {
  assert.equal(xAdapter.nextCursor([{ id: "9" }, { id: "10" }]), "10");
  assert.equal(xAdapter.nextCursor([{ id: "10" }], "11"), "11");
});

test("X catch-up polls request up to 100 posts after a cursor exists", async () => {
  const originalFetch = globalThis.fetch;
  const urls = [];
  globalThis.fetch = async (url) => {
    urls.push(String(url));
    if (String(url).includes("/users/by/username/")) {
      return { ok: true, json: async () => ({ data: { id: "123" } }) };
    }
    return { ok: true, json: async () => ({ data: [] }) };
  };

  try {
    await xAdapter.fetchPosts({ X_BEARER_TOKEN: "test-token" }, { username: "PokemonTCG" }, "456");
  } finally {
    globalThis.fetch = originalFetch;
  }

  const timeline = new URL(urls[1]);
  assert.equal(timeline.searchParams.get("max_results"), "100");
  assert.equal(timeline.searchParams.get("since_id"), "456");
});
