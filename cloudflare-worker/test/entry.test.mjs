import test from "node:test";
import assert from "node:assert/strict";
import { LazadaMonitor, blockBackoffSeconds, isActiveSgt, nextActiveStart } from "../src/entry.js";

test("active window starts at 08:00 SGT", () => {
  assert.equal(isActiveSgt(Date.parse("2026-09-05T00:00:00.000Z")), true);
  assert.equal(isActiveSgt(Date.parse("2026-09-04T23:59:59.999Z")), false);
});

test("active window ends at midnight SGT", () => {
  assert.equal(isActiveSgt(Date.parse("2026-09-05T15:59:59.999Z")), true);
  assert.equal(isActiveSgt(Date.parse("2026-09-05T16:00:00.000Z")), false);
});

test("overnight sleep wakes at the next 08:00 SGT", () => {
  assert.equal(
    new Date(nextActiveStart(Date.parse("2026-09-05T16:00:00.000Z"))).toISOString(),
    "2026-09-06T00:00:00.000Z",
  );
  assert.equal(
    new Date(nextActiveStart(Date.parse("2026-09-05T23:30:00.000Z"))).toISOString(),
    "2026-09-06T00:00:00.000Z",
  );
});

test("block backoff grows through eight hours and caps", () => {
  assert.equal(blockBackoffSeconds(1, 900), 900);
  assert.equal(blockBackoffSeconds(2, 900), 1800);
  assert.equal(blockBackoffSeconds(3, 900), 3600);
  assert.equal(blockBackoffSeconds(4, 900), 7200);
  assert.equal(blockBackoffSeconds(5, 900), 14400);
  assert.equal(blockBackoffSeconds(6, 900), 28800);
  assert.equal(blockBackoffSeconds(10, 900), 28800);
});

test("overnight backoff keeps an alarm scheduled for 08:00 SGT", async () => {
  const originalDateNow = Date.now;
  const alarms = [];

  try {
    Date.now = () => Date.parse("2026-09-09T09:42:10.345Z"); // 17:42 SGT
    const state = {
      storage: {
        setAlarm: async (at) => alarms.push(at),
        deleteAlarm: async () => assert.fail("overnight scheduling must not delete the only alarm"),
      },
    };
    const monitor = new LazadaMonitor(state, {});
    const meta = { recentEvents: [] };

    await monitor.schedule(meta, 8 * 60 * 60 * 1000);

    const expectedWakeAt = Date.parse("2026-09-10T00:00:00.000Z"); // 08:00 SGT
    assert.deepEqual(alarms, [expectedWakeAt]);
    assert.equal(meta.nextAlarmAt, "2026-09-10T00:00:00.000Z");
    assert.equal(meta.nextAllowedCheckAt, expectedWakeAt);
    assert.equal(meta.sleepingUntil, meta.nextAlarmAt);
  } finally {
    Date.now = originalDateNow;
  }
});

test("an alarm firing outside the active window reschedules itself for 08:00 SGT", async () => {
  const originalDateNow = Date.now;
  const alarms = [];
  const persisted = [];

  try {
    Date.now = () => Date.parse("2026-09-09T16:30:00.000Z"); // 00:30 SGT on Sep 10
    const state = {
      storage: {
        setAlarm: async (at) => alarms.push(at),
        deleteAlarm: async () => assert.fail("sleep handling must leave a wake-up alarm"),
        put: async (value) => persisted.push(value),
      },
    };
    const monitor = new LazadaMonitor(state, {});
    const inventory = {};
    const meta = { recentEvents: [] };

    const result = await monitor.runCheck("alarm", inventory, meta);

    const expectedWakeAt = Date.parse("2026-09-10T00:00:00.000Z"); // 08:00 SGT
    assert.equal(result.skipped, true);
    assert.equal(result.reason, "outside_active_window");
    assert.deepEqual(alarms, [expectedWakeAt]);
    assert.equal(meta.nextAlarmAt, "2026-09-10T00:00:00.000Z");
    assert.equal(meta.sleepingUntil, meta.nextAlarmAt);
    assert.equal(persisted.length, 1);
  } finally {
    Date.now = originalDateNow;
  }
});

test("manual Browser Run check works outside the active window and resets old fetch block state", async () => {
  const originalDateNow = Date.now;
  const originalFetch = globalThis.fetch;
  const alarms = [];
  const stored = {
    inventory: {},
    meta: {
      initialized: false,
      recentEvents: [],
      consecutiveFailures: 20,
      blockStreak: 43,
      recoveryMode: true,
      recoverySuccesses: 0,
      nextAllowedCheckAt: 0,
    },
  };
  let browserCalls = 0;

  try {
    Date.now = () => Date.parse("2026-09-11T22:30:00.000Z"); // 06:30 SGT
    globalThis.fetch = async () => assert.fail("direct Worker fetch must not be used for Lazada when Browser Run is bound");

    const state = {
      storage: {
        get: async (key) => stored[key],
        put: async (value) => Object.assign(stored, value),
        setAlarm: async (at) => alarms.push(at),
      },
    };
    const env = {
      LAZADA_URL: "https://www.lazada.sg/shop/example",
      CHECK_INTERVAL_SECONDS: "900",
      RECOVERY_INTERVAL_SECONDS: "300",
      RECOVERY_SUCCESS_TARGET: "6",
      BLOCK_BACKOFF_SECONDS: "1800",
      DEBUG_NOTIFY_SUCCESS: "false",
      BROWSER: {
        quickAction: async (action, options) => {
          browserCalls += 1;
          assert.equal(action, "content");
          assert.equal(options.url, env.LAZADA_URL);
          return new Response(JSON.stringify({
            success: true,
            result: JSON.stringify({
              data: {
                items: [
                  {
                    name: "Pokemon TCG Booster Box",
                    itemUrl: "https://www.lazada.sg/products/test.html",
                    inStock: true,
                  },
                ],
              },
            }),
          }), { status: 200, headers: { "content-type": "application/json" } });
        },
      },
    };

    const monitor = new LazadaMonitor(state, env);
    const result = await monitor.runCheck("manual");

    assert.equal(result.ok, true);
    assert.equal(result.skipped, undefined);
    assert.equal(browserCalls, 1);
    assert.equal(stored.meta.sourceEngine, "cloudflare-browser-run");
    assert.equal(stored.meta.consecutiveFailures, 0);
    assert.equal(stored.meta.blockStreak, 0);
    assert.equal(stored.meta.recoveryMode, false);
    assert.equal(stored.meta.lastSource.engine, "cloudflare-browser-run");
    assert.equal(Object.keys(stored.inventory).length, 1);
    assert.equal(alarms.length, 1);
  } finally {
    Date.now = originalDateNow;
    globalThis.fetch = originalFetch;
  }
});
