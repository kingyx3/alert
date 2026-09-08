import { tcgApiProvider } from "./providers/tcgapi.js";
import { priceChartingProvider } from "./providers/pricecharting.js";

export { buildMarketQuery } from "./providers/tcgapi.js";

// Ordered provider registry. Add a provider module and register it here; the monitor core stays unchanged.
export const MARKET_PROVIDERS = [tcgApiProvider, priceChartingProvider];

export async function queryMarket(env, productName, games = []) {
  let firstError = null;
  for (const provider of MARKET_PROVIDERS) {
    if (!provider.supports(env, productName, games)) continue;
    try {
      const result = await provider.query(env, productName, games);
      if (result?.marketUsd) return result;
    } catch (error) {
      firstError ||= error;
    }
  }
  if (firstError) throw firstError;
  return null;
}
