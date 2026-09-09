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
