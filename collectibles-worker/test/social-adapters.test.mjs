import test from "node:test";
import assert from "node:assert/strict";
import { loadSocialSources } from "../src/social/index.js";
import { instagramAdapter, loadInstagramAccounts } from "../src/social/instagram.js";
import { loadXAccounts, xAdapter } from "../src/social/x.js";

test("disabled X adapter does not appear as a healthy polling source", () => {
  const env = { X_ACCOUNTS_JSON: JSON.stringify([{ username: "PokemonTCG" }]) };
  assert.deepEqual(loadSocialSources(env), []);
});

test("configured X adapter loads normalized account handles", () => {
  const env = {
    X_BEARER_TOKEN: "test-token",
    X_ACCOUNTS_JSON: JSON.stringify([
      { username: "  @PokemonTCG  ", name: "Pokemon" },
      { username: "   " },
    ]),
  };
  const accounts = loadXAccounts(env);
  assert.equal(accounts.length, 1);
  assert.equal(accounts[0].username, "PokemonTCG");

  const sources = loadSocialSources(env);
  assert.equal(sources.length, 1);
  assert.equal(sources[0].id, "x:PokemonTCG");
});

test("X cursor advances by numeric post id and never moves backwards", () => {
  assert.equal(xAdapter.nextCursor([{ id: "9" }, { id: "10" }]), "10");
  assert.equal(xAdapter.nextCursor([{ id: "10" }], "11"), "11");
});

test("X catch-up polls request up to 100 posts after a cursor exists", async () => {
  const originalFetch = globalThis.fetch;
  const urls = [];
  globalThis.fetch = async (url) => {
    urls.push(String(url));
    if (String(url).includes("/users/by/username/")) {
      return { ok: true, json: async () => ({ data: { id: "123" } }) };
    }
    return { ok: true, json: async () => ({ data: [] }) };
  };

  try {
    await xAdapter.fetchPosts({ X_BEARER_TOKEN: "test-token" }, { username: "PokemonTCG" }, "456");
  } finally {
    globalThis.fetch = originalFetch;
  }

  const timeline = new URL(urls[1]);
  assert.equal(timeline.searchParams.get("max_results"), "100");
  assert.equal(timeline.searchParams.get("since_id"), "456");
});

test("disabled Instagram adapter does not appear as a healthy polling source", () => {
  const env = { INSTAGRAM_ACCOUNTS_JSON: JSON.stringify([{ username: "shop" }]) };
  assert.deepEqual(loadSocialSources(env), []);
});

test("Instagram accounts expand into independently scheduled feed sources", () => {
  const env = {
    INSTAGRAM_API_KEY: "ig-test",
    INSTAGRAM_ACCOUNTS_JSON: JSON.stringify([
      {
        username: " https://www.instagram.com/@sg_cards/ ",
        name: "SG Cards",
        feeds: ["story", "posts", "reel", "profile"],
        storiesIntervalSeconds: 240,
      },
    ]),
  };

  const accounts = loadInstagramAccounts(env);
  assert.deepEqual(accounts.map((account) => account.feed), ["stories", "posts", "reels", "profile"]);
  assert.ok(accounts.every((account) => account.username === "sg_cards"));

  const sources = loadSocialSources(env);
  assert.deepEqual(sources.map((source) => source.id), [
    "instagram:sg_cards:stories",
    "instagram:sg_cards:posts",
    "instagram:sg_cards:reels",
    "instagram:sg_cards:profile",
  ]);
  assert.equal(sources[0].intervalSeconds, 240);
});

test("Instagram feed polling authenticates, paginates until a seen id, and deduplicates", async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options = {}) => {
    const parsed = new URL(String(url));
    requests.push({ url: parsed, options });
    if (parsed.searchParams.get("cursor") === "page-2") {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          data: {
            items: [
              { id: "101", shortcode: "new101", caption: "Pokemon restock tomorrow", taken_at: "2026-09-09T12:01:00Z" },
              { id: "100", shortcode: "seen100", caption: "old", taken_at: "2026-09-09T12:00:00Z" },
            ],
            next_cursor: "page-3",
          },
        }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        data: {
          items: [
            { id: "103", shortcode: "new103", caption: "OP-13 available now", taken_at: "2026-09-09T12:03:00Z", like_count: 10 },
            { id: "102", shortcode: "new102", caption: "Pokemon preorder", taken_at: "2026-09-09T12:02:00Z" },
          ],
          next_cursor: "page-2",
        },
      }),
    };
  };

  try {
    const posts = await instagramAdapter.fetchPosts(
      { INSTAGRAM_API_KEY: "ig-test" },
      { username: "sg_cards", feed: "posts", maxPages: 3 },
      JSON.stringify(["100"]),
    );
    assert.deepEqual(posts.map((post) => post.id), ["103", "102", "101"]);
    assert.equal(posts[0].metrics.likes, 10);
    assert.equal(posts[0].media.feed, "posts");
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(requests.length, 2);
  assert.equal(requests[0].url.pathname, "/v1/profile/posts");
  assert.equal(requests[0].url.searchParams.get("handle"), "sg_cards");
  assert.equal(requests[1].url.searchParams.get("cursor"), "page-2");
  assert.equal(requests[0].options.headers.authorization, "Bearer ig-test");
});

test("Instagram stories preserve media and use configured game context when captions are absent", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      data: {
        items: [{
          id: "555",
          type: "photo",
          taken_at: "2026-09-09T12:00:00Z",
          image_url: "https://cdn.example/story.jpg",
        }],
        next_cursor: null,
      },
    }),
  });

  try {
    const posts = await instagramAdapter.fetchPosts(
      { INSTAGRAM_API_KEY: "ig-test" },
      { username: "sg_cards", feed: "stories", games: ["pokemon"] },
    );
    assert.equal(posts.length, 1);
    assert.match(posts[0].text, /pokemon/i);
    assert.equal(posts[0].media.imageUrl, "https://cdn.example/story.jpg");
    assert.equal(posts[0].url, "https://www.instagram.com/stories/sg_cards/555/");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Instagram rolling cursor suppresses already-seen media ids", () => {
  const first = instagramAdapter.nextCursor([{ id: "3" }, { id: "2" }], JSON.stringify(["1"]));
  assert.deepEqual(JSON.parse(first), ["3", "2", "1"]);
  const next = instagramAdapter.nextCursor([{ id: "3" }], first);
  assert.deepEqual(JSON.parse(next), ["3", "2", "1"]);
});
