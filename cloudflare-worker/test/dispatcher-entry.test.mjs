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
    },
    values,
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
