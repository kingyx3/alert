import test from "node:test";
import assert from "node:assert/strict";
import { isActiveSgt, nextActiveStart } from "../src/entry.js";

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
