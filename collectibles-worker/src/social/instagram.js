import { hashString, nowIso } from "../core/utils.js";

const DEFAULT_BASE_URL = "https://api.instagramapi.dev/v1";
const DEFAULT_FEEDS = ["stories", "posts", "reels"];
const VALID_FEEDS = new Set(["stories", "posts", "reels", "profile"]);
const DEFAULT_INTERVALS = {
  stories: 600,
  posts: 900,
  reels: 900,
  profile: 21600,
};
const MAX_SEEN_IDS = 100;

function normalizeUsername(value) {
  return String(value ?? "")
    .trim()
    .replace(/^https?:\/\/(?:www\.)?instagram\.com\//i, "")
    .replace(/^@+/, "")
    .split(/[/?#]/)[0]
    .trim();
}

function normalizeFeed(value) {
  const feed = String(value || "").trim().toLowerCase();
  if (feed === "story") return "stories";
  if (feed === "post") return "posts";
  if (feed === "reel") return "reels";
  return VALID_FEEDS.has(feed) ? feed : null;
}

function normalizeFeeds(value) {
  const requested = Array.isArray(value) ? value : DEFAULT_FEEDS;
  const feeds = requested.map(normalizeFeed).filter(Boolean);
  return [...new Set(feeds.length ? feeds : DEFAULT_FEEDS)];
}

function boundedNumber(value, fallback, min, max = Number.POSITIVE_INFINITY) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

function parseSeenCursor(cursor) {
  if (!cursor) return [];
  try {
    const parsed = JSON.parse(String(cursor));
    if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean).slice(0, MAX_SEEN_IDS);
  } catch {
    // Backward-compatible fallback if an operator manually seeded a single media id.
  }
  return [String(cursor)].filter(Boolean);
}

function locationName(value, fallback = "Singapore") {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (value && typeof value === "object") {
    return String(value.name || value.city || value.address || fallback);
  }
  return fallback;
}

function mediaText(item, account) {
  const caption = String(item?.caption || "").trim();
  if (caption) return caption;
  const context = String(account.mediaContext || "").trim();
  if (context) return context;
  const games = Array.isArray(account.games) ? account.games.map(String).filter(Boolean) : [];
  return games.length ? `${games.join(" ")} Instagram ${account.feed} update` : "";
}

function canonicalMediaUrl(item, username, feed) {
  if (item?.url) return item.url;
  if (feed === "stories" && item?.id) return `https://www.instagram.com/stories/${encodeURIComponent(username)}/${encodeURIComponent(item.id)}/`;
  if (item?.shortcode) return `https://www.instagram.com/p/${encodeURIComponent(item.shortcode)}/`;
  return `https://www.instagram.com/${encodeURIComponent(username)}/`;
}

function mapMediaItem(item, account) {
  const id = String(item?.id || item?.shortcode || "").trim();
  if (!id) return null;
  const username = normalizeUsername(account.username);
  const feed = account.feed;
  return {
    id,
    text: mediaText(item, account),
    createdAt: item?.taken_at || nowIso(),
    url: canonicalMediaUrl(item, username, feed),
    metrics: {
      likes: item?.like_count ?? null,
      comments: item?.comment_count ?? null,
      views: item?.view_count ?? null,
    },
    media: {
      platform: "instagram",
      feed,
      type: item?.type || null,
      productType: item?.product_type || null,
      shortcode: item?.shortcode || null,
      imageUrl: item?.image_url || null,
      videoUrl: item?.video_url || null,
      videoDuration: item?.video_duration ?? null,
    },
    source: account.name || `@${username}`,
    location: locationName(item?.location, account.location || "Singapore"),
  };
}

function mapProfile(profile, account) {
  const username = normalizeUsername(profile?.username || account.username);
  if (!username) return null;
  const biography = String(profile?.biography || "").trim();
  const externalUrl = String(profile?.external_url || "").trim();
  const signature = hashString(`${username}|${biography}|${externalUrl}`);
  return {
    id: `profile-${signature}`,
    text: [biography, externalUrl].filter(Boolean).join(" "),
    createdAt: nowIso(),
    url: `https://www.instagram.com/${encodeURIComponent(username)}/`,
    metrics: {
      followers: profile?.followers ?? null,
      following: profile?.following ?? null,
      posts: profile?.posts ?? null,
    },
    media: {
      platform: "instagram",
      feed: "profile",
      type: "profile",
      imageUrl: profile?.profile_pic_url || null,
      externalUrl: externalUrl || null,
    },
    source: account.name || profile?.full_name || `@${username}`,
    location: account.location || "Singapore",
  };
}

async function requestJson(env, path, username, cursor = null) {
  const base = String(env.INSTAGRAM_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/+$/, "");
  const url = new URL(`${base}${path}`);
  url.searchParams.set("handle", username);
  if (cursor) url.searchParams.set("cursor", cursor);
  const response = await fetch(url, {
    headers: {
      authorization: `Bearer ${env.INSTAGRAM_API_KEY}`,
      accept: "application/json",
    },
  });
  if (!response.ok) {
    let detail = "";
    try {
      const payload = await response.json();
      detail = String(payload?.error?.message || payload?.message || "").trim();
    } catch {
      // Keep the status-only error when the provider returns a non-JSON body.
    }
    throw new Error(`Instagram API ${path} HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }
  return response.json();
}

async function fetchProfile(env, account, seen) {
  const payload = await requestJson(env, "/profile", account.username);
  const post = mapProfile(payload?.data || {}, account);
  if (!post || seen.has(post.id)) return [];
  return [post];
}

async function fetchFeed(env, account, seen) {
  const endpoint = `/profile/${account.feed}`;
  const maxPages = seen.size ? boundedNumber(account.maxPages, 2, 1, 5) : 1;
  const items = [];
  let providerCursor = null;

  for (let page = 0; page < maxPages; page += 1) {
    const payload = await requestJson(env, endpoint, account.username, providerCursor);
    const pageItems = Array.isArray(payload?.data?.items) ? payload.data.items : [];
    items.push(...pageItems);

    const reachedSeenItem = pageItems.some((item) => seen.has(String(item?.id || item?.shortcode || "")));
    const nextCursor = payload?.data?.next_cursor || null;
    if (account.feed === "stories" || !seen.size || reachedSeenItem || !nextCursor) break;
    providerCursor = nextCursor;
  }

  return items
    .map((item) => mapMediaItem(item, account))
    .filter(Boolean)
    .filter((post) => !seen.has(post.id));
}

export function loadInstagramAccounts(env) {
  if (!env.INSTAGRAM_ACCOUNTS_JSON) return [];
  try {
    const rows = JSON.parse(env.INSTAGRAM_ACCOUNTS_JSON);
    if (!Array.isArray(rows)) return [];
    return rows
      .filter((row) => row && typeof row === "object")
      .flatMap((row) => {
        const username = normalizeUsername(row.username || row.handle || row.url);
        if (!username) return [];
        return normalizeFeeds(row.feeds).map((feed) => ({ ...row, username, feed }));
      })
      .slice(0, 100);
  } catch {
    return [];
  }
}

export const instagramAdapter = {
  id: "instagram",
  enabled(env) {
    return Boolean(env.INSTAGRAM_API_KEY);
  },
  loadAccounts: loadInstagramAccounts,
  key(account) {
    return `${normalizeUsername(account.username)}:${normalizeFeed(account.feed) || "posts"}`;
  },
  name(account) {
    const base = account.name || `@${normalizeUsername(account.username)}`;
    return `${base} · Instagram ${normalizeFeed(account.feed) || "posts"}`;
  },
  kind: "social",
  intervalSeconds(account) {
    const feed = normalizeFeed(account.feed) || "posts";
    const configured = account[`${feed}IntervalSeconds`] ?? account.intervalSeconds;
    return boundedNumber(configured, DEFAULT_INTERVALS[feed], 120);
  },
  async fetchPosts(env, account, cursor = null) {
    if (!env.INSTAGRAM_API_KEY || !account?.username) return [];
    const username = normalizeUsername(account.username);
    const feed = normalizeFeed(account.feed) || "posts";
    if (!username) return [];
    const normalizedAccount = { ...account, username, feed };
    const seen = new Set(parseSeenCursor(cursor));
    return feed === "profile"
      ? fetchProfile(env, normalizedAccount, seen)
      : fetchFeed(env, normalizedAccount, seen);
  },
  nextCursor(posts, priorCursor = null) {
    const ids = [
      ...posts.map((post) => String(post?.id || "")).filter(Boolean),
      ...parseSeenCursor(priorCursor),
    ];
    return JSON.stringify([...new Set(ids)].slice(0, MAX_SEEN_IDS));
  },
};
