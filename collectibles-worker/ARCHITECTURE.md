# Collectibles Worker Architecture

The Worker is intentionally split by responsibility so integrations can be added or replaced without editing the scheduler core.

```text
src/
  index.js                      Cloudflare entrypoint and auth/routing only
  monitor.js                    Durable Object orchestration only
  scoring.js                    Pure BUY/WATCH/PASS scoring functions
  core/
    config.js                   Tunables/defaults/health projection
    utils.js                    Small reusable primitives
  storage/
    state.js                    Operational persistence boundary
  market/
    index.js                    Ordered market-provider registry
    providers/
      tcgapi.js                 TCG pricing/liquidity provider
      pricecharting.js          General collectibles provider
  sources/
    index.js                    Source registry + optional EXTRA_SOURCES_JSON
    catalog.js                  Checked-in Singapore watchlist
    detection.js                Product category, urgency, location, supply-risk detection
    web.js                      HTTP fetch + pluggable product parser registry
  social/
    index.js                    Social polling adapter registry
    x.js                        X adapter producing normalized posts
  notifications/
    telegram.js                 Telegram rendering + delivery
```

## Extension rules

### Add a market-price provider

1. Create `src/market/providers/<provider>.js` exporting `{ id, supports, query }`.
2. Normalize the result to the existing market shape (`marketUsd`, `sales30d`, `totalListings`, momentum fields when available).
3. Register the provider in `src/market/index.js`.
4. Add provider-specific tests. `monitor.js` should not change.

This is the intended path for eBay/completed-sales data, a Singapore marketplace provider, Cardmarket, a future Carousell-authorized feed, or another collectibles database.

### Add a social network

1. Create `src/social/<network>.js` that returns normalized posts (`id`, `text`, `createdAt`, `url`, optional `location`/metrics).
2. Register it in `src/social/index.js`.
3. The generic social processing in `monitor.js` handles detection/scoring/alerts.

If polling is not appropriate, send normalized events to `/ingest` instead; Instagram/Facebook/TikTok/provider bridges can use that route without touching monitor code.

### Add a retailer/upstream source

For a normal HTML source, add it to `sources/catalog.js` or `EXTRA_SOURCES_JSON`. No code change is needed.

If a retailer needs bespoke product extraction, add a parser to `PRODUCT_PARSERS` in `sources/web.js` (or split that parser into its own module and register it), then set the source's `parser` field. The scheduler and scoring logic remain unchanged.

### Add a collectible category

Extend the vocabulary in `sources/detection.js`. Market-provider support is independent, so a category can be discovered before a dedicated pricing provider exists.

### Add D1/history later

`storage/state.js` is the operational storage boundary. The Durable Object should continue to own scheduler consistency, deduplication, cache, and alert cooldowns. Add a separate history sink/repository when long-term analytics are needed, e.g. D1 tables for observations, price history, sell-through, opportunities, inventory/P&L, and backtesting. That avoids coupling analytical storage to the live scheduler.

## Dependency direction

Higher-level modules may depend on lower-level modules, not the reverse:

```text
index -> monitor -> adapters/services -> core
                 -> scoring
                 -> storage
```

Market providers, social adapters, parsers, and notification transports must not import `monitor.js` or `index.js`. This keeps them independently testable and prevents circular dependencies.

## CI guardrails

`test/module-boundaries.test.mjs` imports the Worker entrypoint and verifies the provider, social-adapter, parser, source-catalog, and FX configuration extension points. `npm test`, `npm run check`, and Wrangler dry-run packaging must all pass before merge.
