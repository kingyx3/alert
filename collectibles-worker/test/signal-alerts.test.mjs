import test from "node:test";
import assert from "node:assert/strict";
import { extractTimingHint } from "../src/sources/detection.js";
import { buildTelegramMessage, shouldDeliverTelegramAlert } from "../src/notifications/telegram.js";

test("aggregated community PASS signals do not reach Telegram", () => {
  const alert = {
    sourceKind: "community",
    sourceName: "TCGCards.sg Singapore News",
    signalType: "DROP",
    timingHint: "6 SEP 2026 · 4PM",
    url: "https://www.tcgcards.sg/",
    scoring: {
      action: "PASS",
      score: 24,
      demandScore: 30,
      urgencyScore: 88,
      deadInventoryRisk: 54,
    },
  };

  assert.equal(shouldDeliverTelegramAlert(alert), false);
});

test("strong social drops can alert even when aggregate opportunity scores are weak", () => {
  const alert = {
    name: "OP-17 restock tomorrow 10am at PLQ",
    sourceKind: "social",
    sourceName: "Store social feed",
    signalType: "DROP",
    location: "PLQ",
    timingHint: "tomorrow · 10am",
    url: "https://example.com/post",
    supplyRisk: 0,
    scoring: {
      action: "PASS",
      score: 24,
      demandScore: 30,
      urgencyScore: 88,
      deadInventoryRisk: 54,
    },
    reason: ["social signal", "urgency 88/100"],
  };

  assert.equal(shouldDeliverTelegramAlert(alert), true);
  const message = buildTelegramMessage(alert);
  assert.match(message, /SOCIAL DROP/);
  assert.match(message, /Action: CHECK DROP/);
  assert.match(message, /Next step: Open the social post and verify stock, price and timing/i);
  assert.doesNotMatch(message, /Dead inventory risk/i);
});

test("social PASS signals still need a strong direct drop signal", () => {
  const weak = {
    sourceKind: "social",
    sourceName: "Store social feed",
    signalType: "DROP",
    url: "https://example.com/post",
    scoring: { action: "PASS", score: 50, demandScore: 70, urgencyScore: 44 },
  };

  assert.equal(shouldDeliverTelegramAlert(weak), false);
});

test("timing hints stay within one event instead of stitching unrelated page fragments", () => {
  const text = "mon English Release Date Japanese Release Date Lorcana Lor · 1 September 2026 TRADE NIGHT (6 SEP 2026) Ever dreamed of heading to a Pokémon Gym? Join us 4PM to 9PM! 12 August 2026 Changelog";
  const hint = extractTimingHint(text);

  assert.doesNotMatch(hint, /mon English Release Date/i);
  assert.match(hint, /6 SEP 2026/i);
  assert.match(hint, /4PM/i);
});
