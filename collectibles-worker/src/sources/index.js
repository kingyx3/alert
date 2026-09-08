import { DEFAULT_SOURCES } from "./catalog.js";

function validSource(row) {
  if (!row || typeof row !== "object" || !row.id || !row.url) return null;
  let parsed;
  try { parsed = new URL(row.url); } catch { return null; }
  if (!/^https?:$/.test(parsed.protocol)) return null;
  return {
    id: String(row.id).slice(0, 80),
    name: String(row.name || row.id).slice(0, 120),
    kind: ["retailer", "upstream", "community"].includes(row.kind) ? row.kind : "retailer",
    url: parsed.toString(),
    intervalSeconds: Math.max(120, Math.min(21600, Number(row.intervalSeconds || 600))),
    location: row.location ? String(row.location).slice(0, 160) : "Singapore",
    games: Array.isArray(row.games) ? row.games.map(String).slice(0, 20) : ["collectibles"],
    priority: Math.max(0, Math.min(100, Number(row.priority || 70))),
    parser: row.parser ? String(row.parser).slice(0, 50) : "generic",
  };
}

export function loadSources(env) {
  const rows = [...DEFAULT_SOURCES];
  if (env.EXTRA_SOURCES_JSON) {
    try {
      const extra = JSON.parse(env.EXTRA_SOURCES_JSON);
      if (Array.isArray(extra)) rows.push(...extra);
    } catch { /* invalid optional config ignored */ }
  }
  const seen = new Set();
  return rows.map(validSource).filter((row) => row && !seen.has(row.id) && seen.add(row.id));
}

export { DEFAULT_SOURCES } from "./catalog.js";
