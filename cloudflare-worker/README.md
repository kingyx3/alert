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

`SCRAPING_URL` and `SCRAPING_URL_2` return Lazada `listItems`. **Listing presence is not itself an availability signal**: Lazada keeps sold-out products in the listing.

Stock is determined in this order:

1. explicit availability fields such as `inStock`, `isAvailable`, or `available`;
2. inverse sold-out fields such as `soldOut`, `isSoldOut`, `outOfStock`, or `isOutOfStock`;
3. numeric quantity fields such as `stock`, `stockCount`, `quantity`, or `availableStock`;
4. availability/status text;
5. Lazada's `icons[].bizType = "outofstock"` marker and the listing `querystring` `stock=` value as defensive fallbacks.

If fallback signals conflict, stock is left unknown rather than risking a false in-stock alert. If no stock signal exists at all, stock remains unknown. Explicit fields always take precedence over fallback metadata.

The production payloads supplied on 2026-09-18 contained `inStock: false`, an `outofstock` icon, and `stock=0` for the listed products, so those items should correctly be treated as unavailable even though they remain present in `listItems`.

## Alert behavior

- The first accepted snapshot establishes the inventory baseline. `ALERT_ON_FIRST_RUN=true` may alert for products already available on that first snapshot.
- Unavailable → available transitions are alerted immediately during the active window.
- The dispatcher also supports the existing persistent in-stock notification behavior across later Cloudflare root batches while preventing duplicate alerts from redundant runners within the same root batch.
- Alert delivery is serialized with snapshot ingestion, and SKU/root-batch deduplication prevents redundant runners from sending duplicate notifications.
- Missing SKUs require two consecutive complete snapshots before being marked unavailable (`MISSING_CONFIRMATIONS=2`). Partial fast-path snapshots cannot mark unseen SKUs missing.
- Failed, blocked, unparseable, or failed-Telegram snapshots preserve retryable inventory state.

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

`npm run check` performs JavaScript syntax checks, unit/regression tests, and a Wrangler dry-run deployment. The stock regression suite covers the current Lazada `listItems` sold-out schema, verifies that listing presence alone stays unknown, checks the out-of-stock badge and `stock=` fallbacks, and ensures conflicting fallback signals cannot create a false positive.

## Deployment

Changes merged to `main` are deployed through `.github/workflows/deploy-cloudflare-worker.yml`. The production Worker entrypoint is `src/dispatcher-entry.js`.

After deployment, verify:

1. `/schedulerz` reports the 10-second cadence and `08:00-20:00` SGT active window.
2. `/healthz` shows a recent `lastSuccessAt` during active hours.
3. Recent `Lazada Playwright Monitor` runs show at least one clean runner with `ingestOk: true`.
4. A known `inStock: false` item remains unavailable even though it is present in `listItems`, and a controlled false→true stock transition is recognized and alerted.
