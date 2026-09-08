export function clamp(value, min = 0, max = 100) {
  const n = Number(value);
  if (!Number.isFinite(n)) return min;
  return Math.min(max, Math.max(min, n));
}

export function grossMarginPct(retailSgd, marketSgd) {
  const retail = Number(retailSgd);
  const market = Number(marketSgd);
  if (!(retail > 0) || !(market > 0)) return null;
  return ((market - retail) / retail) * 100;
}

export function netMarginPct({ retailSgd, expectedSaleSgd, platformFeePct = 4, shippingSgd = 4.5, riskBufferPct = 5 }) {
  const retail = Number(retailSgd);
  const sale = Number(expectedSaleSgd);
  if (!(retail > 0) || !(sale > 0)) return null;
  const fee = sale * (Number(platformFeePct) || 0) / 100;
  const risk = sale * (Number(riskBufferPct) || 0) / 100;
  const profit = sale - retail - fee - (Number(shippingSgd) || 0) - risk;
  return (profit / retail) * 100;
}

function salesVelocityScore(sales30d) {
  const sales = Number(sales30d);
  if (!Number.isFinite(sales) || sales < 0) return null;
  // 0 sales = 0; ~5 = 35; ~15 = 60; ~40 = 80; 100+ = ~100.
  return clamp(100 * (1 - Math.exp(-sales / 28)));
}

function listingScarcityScore(totalListings) {
  const listings = Number(totalListings);
  if (!Number.isFinite(listings) || listings < 0) return null;
  if (listings <= 3) return 95;
  if (listings <= 10) return 85;
  if (listings <= 25) return 70;
  if (listings <= 75) return 55;
  if (listings <= 200) return 40;
  return 25;
}

export function demandScore({
  sales30d = null,
  priceChange7d = null,
  priceChange30d = null,
  totalListings = null,
  socialHeat = 0,
  retailerSelloutHeat = 0,
  carousellInterest = null,
} = {}) {
  const components = [];
  const sales = salesVelocityScore(sales30d);
  if (sales !== null) components.push([sales, 0.42]);

  const p7 = Number(priceChange7d);
  if (Number.isFinite(p7)) components.push([clamp(50 + p7 * 2.2), 0.12]);

  const p30 = Number(priceChange30d);
  if (Number.isFinite(p30)) components.push([clamp(50 + p30 * 1.2), 0.08]);

  const scarcity = listingScarcityScore(totalListings);
  if (scarcity !== null) components.push([scarcity, 0.12]);

  components.push([clamp(socialHeat), 0.12]);
  components.push([clamp(retailerSelloutHeat), 0.08]);

  const carou = Number(carousellInterest);
  if (Number.isFinite(carou)) components.push([clamp(carou), 0.14]);

  const weight = components.reduce((sum, [, w]) => sum + w, 0);
  if (!weight) return 0;
  return clamp(components.reduce((sum, [v, w]) => sum + v * w, 0) / weight);
}

export function deadInventoryRisk({
  sales30d = null,
  priceChange7d = null,
  priceChange30d = null,
  supplyBreadth = 0,
  reprintRisk = 0,
  socialHeat = 0,
} = {}) {
  let risk = 30;
  const sales = Number(sales30d);
  if (Number.isFinite(sales)) {
    if (sales <= 2) risk += 35;
    else if (sales <= 7) risk += 20;
    else if (sales >= 30) risk -= 20;
  }
  const p7 = Number(priceChange7d);
  if (Number.isFinite(p7)) risk += p7 < -10 ? 20 : p7 > 10 ? -8 : 0;
  const p30 = Number(priceChange30d);
  if (Number.isFinite(p30)) risk += p30 < -15 ? 15 : p30 > 15 ? -8 : 0;
  risk += clamp(supplyBreadth, 0, 10) * 3;
  risk += clamp(reprintRisk) * 0.28;
  risk -= clamp(socialHeat) * 0.12;
  return clamp(risk);
}

export function opportunityScore(input = {}) {
  const gross = grossMarginPct(input.retailSgd, input.marketSgd);
  const net = netMarginPct({
    retailSgd: input.retailSgd,
    expectedSaleSgd: input.marketSgd,
    platformFeePct: input.platformFeePct,
    shippingSgd: input.shippingSgd,
    riskBufferPct: input.riskBufferPct,
  });

  const demand = demandScore(input);
  const scarcity = listingScarcityScore(input.totalListings) ?? clamp(input.scarcityScore ?? 45);
  const urgency = clamp(input.urgencyScore ?? 0);
  const confidence = clamp(input.confidenceScore ?? 50);
  const risk = deadInventoryRisk(input);

  const marginComponent = net === null ? 0 : clamp((net + 10) * 1.6);
  let score =
    marginComponent * 0.35 +
    demand * 0.30 +
    scarcity * 0.13 +
    urgency * 0.10 +
    confidence * 0.12 -
    risk * 0.18;

  score = clamp(score);

  const minNet = Number(input.minNetMarginPct ?? 22);
  const minDemand = Number(input.minDemandScore ?? 62);
  const minBuyScore = Number(input.minBuyScore ?? 76);
  const minWatchScore = Number(input.minWatchScore ?? 58);

  let action = "PASS";
  if (net !== null && net >= minNet && demand >= minDemand && score >= minBuyScore && risk <= 60) {
    action = "BUY";
  } else if (score >= minWatchScore && (net === null || net >= 8)) {
    action = "WATCH";
  }

  return {
    score: Math.round(score),
    action,
    grossMarginPct: gross === null ? null : Math.round(gross * 10) / 10,
    netMarginPct: net === null ? null : Math.round(net * 10) / 10,
    demandScore: Math.round(demand),
    scarcityScore: Math.round(scarcity),
    urgencyScore: Math.round(urgency),
    confidenceScore: Math.round(confidence),
    deadInventoryRisk: Math.round(risk),
  };
}
