import { xAdapter } from "./x.js";

// Polling social adapters return the same normalized post shape. Add a new adapter here without changing monitor orchestration.
export const SOCIAL_ADAPTERS = [xAdapter];

export function loadSocialSources(env) {
  const rows = [];
  for (const adapter of SOCIAL_ADAPTERS) {
    if (typeof adapter.enabled === "function" && !adapter.enabled(env)) continue;
    const accounts = adapter.loadAccounts(env);
    for (const account of accounts) {
      rows.push({
        adapter,
        account,
        id: `${adapter.id}:${adapter.key(account)}`,
        name: adapter.name(account),
        kind: adapter.kind || "social",
        location: account.location || "Singapore",
        intervalSeconds: adapter.intervalSeconds(account),
      });
    }
  }
  return rows;
}

export { loadXAccounts } from "./x.js";
