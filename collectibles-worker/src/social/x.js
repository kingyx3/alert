import { nowIso } from "../core/utils.js";

function normalizeUsername(value) {
  return String(value ?? "").trim().replace(/^@+/, "");
}

function compareIds(a, b) {
  const left = String(a ?? "");
  const right = String(b ?? "");
  if (/^\d+$/.test(left) && /^\d+$/.test(right)) {
    const leftId = BigInt(left);
    const rightId = BigInt(right);
    if (leftId === rightId) return 0;
    return leftId < rightId ? -1 : 1;
  }
  return left.localeCompare(right);
}

export function loadXAccounts(env) {
  if (!env.X_ACCOUNTS_JSON) return [];
  try {
    const rows = JSON.parse(env.X_ACCOUNTS_JSON);
    if (!Array.isArray(rows)) return [];
    return rows
      .filter((x) => x && typeof x === "object")
      .map((x) => ({ ...x, username: normalizeUsername(x.username) }))
      .filter((x) => x.username)
      .slice(0, 100);
  } catch { return []; }
}

async function fetchPosts(env, account, cursor = null) {
  if (!env.X_BEARER_TOKEN || !account?.username) return [];
  const username = normalizeUsername(account.username);
  if (!username) return [];
  const auth = { authorization: `Bearer ${env.X_BEARER_TOKEN}` };
  const userResp = await fetch(`https://api.x.com/2/users/by/username/${encodeURIComponent(username)}`, { headers: auth });
  if (!userResp.ok) throw new Error(`X user lookup HTTP ${userResp.status}`);
  const user = await userResp.json();
  const id = user?.data?.id;
  if (!id) return [];

  const params = new URLSearchParams({ max_results: "10", exclude: "retweets,replies", "tweet.fields": "created_at,public_metrics,entities" });
  if (cursor) params.set("since_id", cursor);
  const postResp = await fetch(`https://api.x.com/2/users/${id}/tweets?${params}`, { headers: auth });
  if (!postResp.ok) throw new Error(`X posts HTTP ${postResp.status}`);
  const payload = await postResp.json();
  return (payload.data || []).map((p) => ({
    id: p.id,
    text: p.text || "",
    createdAt: p.created_at || nowIso(),
    url: `https://x.com/${username}/status/${p.id}`,
    metrics: p.public_metrics || {},
    source: account.name || `@${username}`,
    location: account.location || "Singapore",
  }));
}

export const xAdapter = {
  id: "x",
  enabled(env) { return Boolean(env.X_BEARER_TOKEN); },
  loadAccounts: loadXAccounts,
  key(account) { return normalizeUsername(account.username); },
  name(account) { return account.name || `@${normalizeUsername(account.username)}`; },
  kind: "social",
  intervalSeconds(account) { return Math.max(60, Number(account.intervalSeconds || 180)); },
  fetchPosts,
  nextCursor(posts, priorCursor = null) {
    return posts.reduce((latest, post) => {
      const id = post?.id;
      if (!id) return latest;
      return latest === null || compareIds(id, latest) > 0 ? String(id) : latest;
    }, priorCursor ? String(priorCursor) : null);
  },
};
