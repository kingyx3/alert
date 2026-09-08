import { asNumber } from "./utils.js";

export const MAX_EVENTS = 120;
export const MAX_OPPORTUNITIES = 100;
export const MAX_MARKET_CACHE = 500;
export const DEFAULT_SOURCE_FAILURE_BACKOFF_SECONDS = 900;
export const DEFAULT_ALERT_COOLDOWN_SECONDS = 6 * 60 * 60;
export const DEFAULT_USD_SGD = 1.30;
export const DEFAULT_MARKET_CACHE_SECONDS = 6 * 60 * 60;
export const DEFAULT_MARKET_NEGATIVE_CACHE_SECONDS = 15 * 60;
export const DEFAULT_MAX_MARKET_LOOKUPS_PER_RUN = 24;

export function scoringConfig(env) {
  return {
    usdSgd: asNumber(env.USD_SGD_RATE, DEFAULT_USD_SGD),
    minNet: asNumber(env.MIN_NET_MARGIN_PCT, 22),
    minDemand: asNumber(env.MIN_DEMAND_SCORE, 62),
    minBuy: asNumber(env.MIN_BUY_SCORE, 76),
    minWatch: asNumber(env.MIN_WATCH_SCORE, 58),
    platformFee: asNumber(env.SELL_PLATFORM_FEE_PCT, 4),
    shipping: asNumber(env.SELL_SHIPPING_SGD, 4.5),
    riskBuffer: asNumber(env.SELL_RISK_BUFFER_PCT, 5),
  };
}

export function sourceHealth(source, state = {}) {
  return {
    id: source.id,
    name: source.name,
    kind: source.kind,
    status: state.consecutiveFailures ? "degraded" : state.lastSuccessAt ? "ok" : "unknown",
    lastCheckAt: state.lastCheckAt || null,
    lastSuccessAt: state.lastSuccessAt || null,
    consecutiveFailures: state.consecutiveFailures || 0,
    nextDueAt: state.nextDueAt || null,
    lastError: state.lastError || null,
    observations: state.observations || 0,
  };
}
