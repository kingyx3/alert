# Lazada Pokémon TCG Cloudflare monitor

Cloudflare Worker + Durable Object restock monitor. The scheduled Worker wakes the singleton Durable Object every minute, while the Durable Object keeps its own 30-second alarm loop between cron ticks.

The monitor is deliberately **block-aware, not block-evasive**: HTTP 403/429 or anti-bot challenge pages are logged, state is preserved, and checks back off. It does not rotate identities, solve CAPTCHAs, spoof browser fingerprints, use proxies, or otherwise bypass access controls.

## Detection behavior

- First successful fetch creates a baseline and sends no alert by default.
- A Telegram alert is sent when a known SKU transitions from unavailable to available, or when a newly discovered TCG SKU is already available after baseline initialization.
- Missing SKUs must be absent for two consecutive successful snapshots before being marked unavailable, reducing false restock alerts caused by transient/incomplete payloads.
- Failed, blocked, or unparseable source responses never advance inventory state.

## Diagnostics

- `GET /healthz` — public minimal health status.
- `GET /debug` — detailed state, recent structured events, source metadata, and tracked SKUs. Requires `Authorization: Bearer <DEBUG_TOKEN>`.
- `POST /check` — force an immediate check. Requires the same bearer token.
- Cloudflare logs are structured JSON and include run IDs and events such as `source.fetch.ok`, `source.blocked`, `stock.diff`, `telegram.sent`, and `alarm.scheduled`.
- `npm run tail` streams Worker logs via Wrangler.

Secrets are injected at deploy time by `.github/workflows/deploy-cloudflare-worker.yml`; do not commit them here.
