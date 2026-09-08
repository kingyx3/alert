import { CollectiblesMonitor } from "./monitor.js";
import { bearerToken, constantTimeEqual, json } from "./core/utils.js";

export { CollectiblesMonitor };

function stub(env) {
  const id = env.COLLECTIBLES_MONITOR.idFromName("sg-collectibles-market-intel");
  return env.COLLECTIBLES_MONITOR.get(id);
}

function authorized(request, env) {
  return Boolean(env.DEBUG_TOKEN) && constantTimeEqual(bearerToken(request), env.DEBUG_TOKEN);
}

function ingestAuthorized(request, env) {
  const token = env.INGEST_TOKEN || env.DEBUG_TOKEN;
  return Boolean(token) && constantTimeEqual(bearerToken(request), token);
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(stub(env).fetch("https://internal/run", { method: "POST" }));
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return json({
        service: "sg-collectibles-market-intel",
        health: "/healthz",
        debug: "/debug (GET, Bearer token)",
        manualRun: "/run (POST, Bearer token)",
        socialIngest: "/ingest (POST, Bearer token)",
      });
    }

    if (request.method === "GET" && url.pathname === "/healthz") {
      return stub(env).fetch("https://internal/healthz");
    }

    if (request.method === "POST" && url.pathname === "/ingest") {
      if (!ingestAuthorized(request, env)) return json({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      return stub(env).fetch("https://internal/ingest", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: await request.text(),
      });
    }

    if (request.method === "GET" && url.pathname === "/debug") {
      if (!authorized(request, env)) return json({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      return stub(env).fetch("https://internal/debug");
    }

    if (request.method === "POST" && url.pathname === "/run") {
      if (!authorized(request, env)) return json({ error: "unauthorized" }, 401, { "www-authenticate": "Bearer" });
      return stub(env).fetch("https://internal/run", { method: "POST" });
    }

    return json({ error: "not_found" }, 404);
  },
};
