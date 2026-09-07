import test from "node:test";
import assert from "node:assert/strict";
import { demandScore, deadInventoryRisk, grossMarginPct, netMarginPct, opportunityScore } from "../src/scoring.js";
import { buildMarketQuery } from "../src/index.js";
import { detectGames, extractLocationHint, extractTimingHint } from "../src/sources.js";

test("gross and net margins are conservative", () => {
  assert.equal(Math.round(grossMarginPct(100, 150)), 50);
  const net = netMarginPct({ retailSgd: 100, expectedSaleSgd: 150, platformFeePct: 5, shippingSgd: 5, riskBufferPct: 5 });
  assert.equal(Math.round(net), 30);
});

test("strong sales velocity raises demand and lowers dead inventory risk", () => {
  const strong = demandScore({ sales30d: 80, priceChange7d: 12, totalListings: 20, socialHeat: 80 });
  const weak = demandScore({ sales30d: 1, priceChange7d: -8, totalListings: 300, socialHeat: 10 });
  assert.ok(strong > weak + 35);
  assert.ok(deadInventoryRisk({ sales30d: 80, priceChange7d: 10 }) < deadInventoryRisk({ sales30d: 1, priceChange7d: -15 }));
});

test("high margin with weak demand is not automatically a BUY", () => {
  const scored = opportunityScore({
    retailSgd: 50, marketSgd: 100, sales30d: 1, priceChange7d: -10,
    totalListings: 250, socialHeat: 5, urgencyScore: 10, confidenceScore: 90,
  });
  assert.notEqual(scored.action, "BUY");
});

test("strong margin plus strong liquidity can qualify as BUY", () => {
  const scored = opportunityScore({
    retailSgd: 100, marketSgd: 155, platformFeePct: 4, shippingSgd: 3, riskBufferPct: 3,
    sales30d: 100, priceChange7d: 12, priceChange30d: 20, totalListings: 15,
    socialHeat: 85, retailerSelloutHeat: 70, urgencyScore: 70, confidenceScore: 95,
  });
  assert.equal(scored.action, "BUY");
  assert.ok(scored.demandScore >= 70);
});

test("market query maps supported TCGs and leaves non-TCG to fallback adapter", () => {
  assert.equal(buildMarketQuery("Pokemon TCG Booster Box", ["pokemon"]).game, "pokemon");
  assert.equal(buildMarketQuery("OP-17 Booster Box", ["one-piece"]).game, "one-piece");
  assert.equal(buildMarketQuery("Beyblade X UX-21", ["beyblade"]).game, null);
});

test("collectible detection is not restricted to TCGs", () => {
  assert.ok(detectGames("POP MART LABUBU limited drop").includes("pop-mart"));
  assert.ok(detectGames("LEGO exclusive set coming soon").includes("lego"));
  assert.ok(detectGames("Hot Wheels Super Treasure Hunt").includes("hot-wheels"));
});

test("drop messages extract Singapore location and timing hints", () => {
  const text = "OP-17 restock tomorrow 10am at PLQ. Limited quantities.";
  assert.equal(extractLocationHint(text), "PLQ");
  assert.match(extractTimingHint(text), /tomorrow/i);
  assert.match(extractTimingHint(text), /10am/i);
});
