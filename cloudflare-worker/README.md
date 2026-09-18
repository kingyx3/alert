# Lazada Pokémon TCG restock monitor

Cloudflare Worker + Durable Object + GitHub Actions monitor for Lazada Pokémon TCG inventory.

## Production architecture

- Cloudflare Cron runs once per minute during **08:00-19:59 Singapore time (SGT)**.
- Each Cron tick dispatches six GitHub Actions probe batches at 10-second offsets: `0, 10, 20, 30, 40, 50` seconds.
- Each GitHub Actions batch launches four independent Playwright probes against the two trusted Lazada listing endpoints. Rescue runners are used when the primary wave cannot produce a clean snapshot.
- Successful probes POST normalized snapshots to the Cloudflare Worker, where a Durable Object serializes inventory state and alert decisions.
- GitHub's `*/5` schedule is a delayed fallback only; it runs browsers when the Worker has not accepted a fresh snapshot recently.
- Production Telegram alerts are suppressed outside **08:00-20:00 SGT**.

The monitor is block-aware rather than block-evasive. HTTP 403/429 responses and anti-bot challenges are treated as failures; the system does not solve CAPTCHAs, rotate identities, or bypass access controls.

## Stock detection

The trusted Lazada endpoints are product-listing feeds. Lazada frequently omits an explicit `inStock` field for products that appear in these lists. For the two configured trusted feeds, listing presence is therefore treated as an in-stock fallback **only when no explicit stock signal exists**.

Explicit signals always take precedence. Fields such as `inStock`, `isAvailable`, `soldOut`, `isSoldOut`, `outOfStock`, quantity fields, and availability/status strings can explicitly mark a product available or unavailable. An explicit sold-out or zero-stock signal is never overridden by listing presence.

Unknown stock remains unknown for sources that are not configured with the trusted listing fallback.

## Alert behavior

- The first accepted snapshot establishes the inventory baseline. `ALERT_ON_FIRST_RUN=true` may alert for products already available on that first snapshot.
- After initialization, Telegram alerts are sent only for genuine **unavailable → available** transitions or newly discovered available SKUs.
- An already-available SKU appearing in later 10-second dispatch batches does **not** generate repeated "still in stock" alerts.
- Alert delivery is serialized with snapshot ingestion, and SKU/root-batch deduplication prevents redundant runners from sending duplicate transition alerts.
- Missing SKUs require two consecutive complete snapshots before being marked unavailable (`MISSING_CONFIRMATIONS=2`). Partial fast-path snapshots cannot mark unseen SKUs missing.
- Failed, blocked, unparseable, or failed-Telegram snapshots do not advance inventory state in a way that loses a retryable transition.

## Runtime configuration

`wrangler.toml` is the production source of non-secret runtime configuration. Key values currently include:

- `EXTERNAL_SNAPSHOT_MODE=true`
- `CHECK_INTERVAL_SECONDS=10`
- `EXTERNAL_HEALTH_STALE_SECONDS=300`
- `MISSING_CONFIRMATIONS=2`
- `ALERT_ON_FIRST_RUN=true`
- `ALERT_WINDOW_ENFORCED=true`
- `TCG_KEYWORDS=pokemon,pokémon,tcg,trading card`

The Cloudflare Cron expression is `*/1 0-11 * * *`, which maps to 08:00-19:59 SGT because Cloudflare Cron uses UTC.

## Required production values

Configure the GitHub `production` Environment with:

### Secrets

- `CLOUDFLARE_API_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `DEBUG_TOKEN`
- `GITHUB_ACTIONS_TOKEN` if the deployment workflow manages the dispatch token as a secret

### Variables / runtime configuration

- `CLOUDFLARE_ACCOUNT_ID`
- `TELEGRAM_CHANNEL_ID`
- `SCRAPING_URL`
- `SCRAPING_URL_2`

The Worker must also receive `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `DEBUG_TOKEN`, and the GitHub dispatch credential as runtime bindings/secrets as required by the deployment workflow.

## Health and diagnostics

- `GET /healthz` — public health status. During the active window, a snapshot older than the configured stale threshold is degraded. Outside the window the service reports sleeping/healthy behavior rather than treating the intentional pause as an outage.
- `GET /schedulerz` — scheduler configuration, active window, dispatch cadence, target repository/workflow, and fallback mode.
- `GET /debug` — detailed Durable Object state and recent events; requires `Authorization: Bearer <DEBUG_TOKEN>`.
- `POST /check` — protected manual check endpoint. In external snapshot mode the Worker itself does not scrape Lazada; production source reads come from GitHub Actions Playwright probes.
- GitHub Actions artifacts contain `probe.json` diagnostics for each runner, including product counts, block markers, ingestion status, and timings.

Useful events include `external.snapshot.accepted`, `external.snapshot.superseded`, `external.snapshot.duplicate`, `external.snapshot.telegram_error`, `telegram.sent`, and GitHub dispatch logs.

## Local validation

From `cloudflare-worker/` run:

```bash
npm install
npm run check
```

`npm run check` performs JavaScript syntax checks, unit/regression tests, and a Wrangler dry-run deployment. The regression suite specifically covers Lazada listing items with omitted stock fields and verifies that explicit sold-out/zero-quantity signals override the listing-presence fallback.

## Deployment

Changes merged to `main` are deployed through `.github/workflows/deploy-cloudflare-worker.yml`. The production Worker entrypoint is `src/dispatcher-entry.js`.

After deployment, verify:

1. `/schedulerz` reports the 10-second cadence and `08:00-20:00` SGT active window.
2. `/healthz` shows a recent `lastSuccessAt` during active hours.
3. Recent `Lazada Playwright Monitor` runs show at least one clean runner with `ingestOk: true`.
4. A controlled unavailable→available fixture or test snapshot produces one Telegram alert, while later batches with the same SKU still available do not produce another.
