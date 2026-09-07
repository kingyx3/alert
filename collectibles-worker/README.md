# SG Collectibles Market-Intelligence Worker

A separate Cloudflare Worker that discovers Singapore collectible drops, enriches them with secondary-market data, scores margin **and liquidity**, and sends Telegram alerts only when the opportunity clears configurable thresholds.

## What it watches by default

Retail / procurement signals:
- Toys"R"Us Singapore: Pokemon and Beyblade X category pages
- Tom & Stefanie
- Metro Pokemon
- HammerHouse Beyblade X
- Kiddy Palace toys / Beyblade X
- Game Academia TCG catalog
- POP MART Singapore
- LEGO Singapore new sets and bestsellers

Upstream / official signals:
- Maxsoft trading-card pages and Singapore retailer network
- Pokemon Singapore / Pokemon Center Singapore
- One Piece Card Game official product/store channels
- Magic official products/news
- Takara Tomy Beyblade X news
- TCGCards.sg Singapore news aggregation

Optional X accounts can be added with `X_ACCOUNTS_JSON`. Instagram should be supplied through a compliant social-listening provider or another JSON/webhook bridge; Meta's first-party Instagram API is primarily for professional accounts managed by the authenticated app and is not a general arbitrary-public-account feed.

## Market and demand model

For TCG products, set `TCG_API_KEY` to use `tcgapi.dev` search/pricing across Pokemon, One Piece, Magic, Yu-Gi-Oh!, Lorcana, Digimon, Flesh and Blood, Star Wars Unlimited, Riftbound and other supported games.

For non-TCG collectibles such as Beyblade, LEGO, Funko, Hot Wheels and designer toys, optionally set `PRICECHARTING_TOKEN`. The adapter uses PriceCharting's current new/sealed value and annual sales-volume field (converted to an approximate monthly velocity). Treat it as a market benchmark, not a guaranteed Singapore sale price. PriceCharting limits API calls to one per second; the Worker throttles requests and caches market lookups for six hours by default.

The score intentionally separates **margin** from **demand**:

- estimated net margin after platform fee, shipping and risk buffer
- 30-day sales velocity when price-history access is enabled
- 7/30-day price momentum
- active listing count / scarcity
- retailer sell-out and social heat
- urgency language (drop, restock, first-come-first-served, limited quantity)
- reprint / supply-expansion risk
- confidence in product matching

A high spread with weak sales velocity does **not** become a BUY alert.

Default thresholds:
- BUY: score >= 76, net margin >= 22%, demand >= 62, dead-inventory risk <= 60
- WATCH: score >= 58 with positive-enough economics
- PASS: everything else

## Carousell strategy

Do not make the Worker depend on scraping Carousell. Carousell's own Account Insights / Professional / CarouBiz tools provide clicks, search keywords, estimated revenue and competitor insights for your own selling account. Use those as a local-demand calibration source.

For v1, market price and sell-through are sourced from contracted/explicit APIs. The `/ingest` webhook accepts `carousellInterest`, observed local market price, sales velocity and listing-count fields from your own analytics/export pipeline, allowing Singapore demand to override or reinforce global market data. Public search snapshots can be added as a low-frequency optional source, but disappearance of a listing should not be treated as a confirmed sale.

## Supply-chain signals

The Worker monitors upstream official/distributor pages separately from retail pages. That lets us penalize an apparent resale opportunity when reprints, additional production or broad retailer availability indicate supply is about to expand.

Useful additional feeds for a later version:
- Maxsoft product/preorder announcements and retailer network changes
- Bandai TCG+ events and One Piece release calendars
- Pokemon Singapore release/event news
- Wizards product/release and Secret Lair queues
- Takara Tomy launch/B4-store announcements
- Singapore trade statistics (EnterpriseSG/SingStat) as a slow aggregate category-level signal
- paid shipment intelligence (e.g. Panjiva) where supplier/importer records are actually granular enough

Trade statistics are a macro corroboration signal only; they are not SKU-level inventory.

## Secrets and variables

Required for alerts/debug:
```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHANNEL_ID
DEBUG_TOKEN
```

Recommended:
```text
TCG_API_KEY
```

Optional:
```text
PRICECHARTING_TOKEN
X_BEARER_TOKEN
INGEST_TOKEN
X_ACCOUNTS_JSON
EXTRA_SOURCES_JSON
TCG_API_HISTORY_ENABLED=true
MARKET_CACHE_SECONDS=21600
MARKET_NEGATIVE_CACHE_SECONDS=900
MAX_MARKET_LOOKUPS_PER_RUN=24
USD_SGD_RATE=1.30
```

`USD_SGD_RATE` is a configurable conversion input. The checked-in fallback is `1.30`; replace it with a live FX feed later if you want tighter real-time margin estimates.

Example `X_ACCOUNTS_JSON`:
```json
[
  {"username":"retailer_handle","name":"Retailer Name","location":"Singapore","intervalSeconds":180}
]
```

Example extra source:
```json
[
  {
    "id":"local-shop-news",
    "name":"Local Shop",
    "kind":"retailer",
    "url":"https://example.com/collections/new-arrivals",
    "intervalSeconds":300,
    "location":"Singapore",
    "games":["pokemon","one-piece","magic"],
    "priority":80
  }
]
```


## Cloudflare storage strategy

D1 is **not required for v1**. This Worker already uses one named Durable Object (`CollectiblesMonitor`) with SQLite-backed persistent storage for:

- per-source health / next-due state
- social-post and retailer deduplication
- alert cooldowns
- the persistent positive/negative market-data cache
- recent ranked opportunities and events

That keeps the deployment simple and gives the monitor strongly consistent state. Add D1 later when the project needs analytical history rather than just operational state — for example multi-month price observations, sell-through history, backtesting, portfolio/P&L, thousands of tracked products, or SQL queries across categories and retailers. The scoring and source adapters are kept independent so a D1 history sink can be added without replacing the Durable Object scheduler.

## Endpoints

- `GET /healthz` public summary
- `GET /debug` Bearer `DEBUG_TOKEN`: source health, configuration, ranked opportunities and recent events
- `POST /run` Bearer `DEBUG_TOKEN`: immediate manual cycle
- `POST /ingest` Bearer `INGEST_TOKEN` (or `DEBUG_TOKEN` fallback): accept normalized Instagram/Facebook/TikTok/Carousell/provider signals


## Social/provider ingest

Use `/ingest` as the bridge for Instagram, Facebook, TikTok, social-listening providers, retailer email parsers, or your own Carousell analytics pipeline. This avoids coupling the core system to unsupported public-page scraping.

Example payload:
```json
{
  "id": "instagram-post-123",
  "platform": "instagram",
  "sourceName": "Retailer Name",
  "text": "OP-17 restock tomorrow 10am at PLQ. Limited quantities, first come first served.",
  "url": "https://...",
  "retailSgd": 110,
  "location": "PLQ",
  "carousellInterest": 82
}
```

The Worker extracts game/category, urgency, Singapore location and timing hints, enriches the product with market data where possible, applies liquidity/dead-inventory gates, and only then decides BUY/WATCH/PASS.

## Telegram alert example

```text
🔥 BUY OPPORTUNITY · Score 84/100
OP-17 The World's Strongest Warriors Booster Box
Source: Singapore retailer
Where: Singapore
Retail: S$110.00
Market est.: S$159.00
Est. net margin: 29.8% (gross 44.5%)
Demand 81/100 · Dead inventory risk 25/100
30d sales velocity: 74
Active market listings: 18
Why: 29.8% est. net margin; 74 market sales in 30d; time-sensitive drop/restock language
https://...
```

## Local validation

```powershell
cd collectibles-worker
npm install
npm test
npm run check
npx wrangler deploy --dry-run
```

## Design constraint

The monitor is intentionally source-friendly: per-source schedules, bounded request rates, six-hour market-data caching, PriceCharting one-request-per-second throttling, exponential failure backoff, and no CAPTCHA or anti-bot bypass behavior.

This system is a decision-support tool, not a guarantee of profit. Market prices can move quickly, local sell-through can differ from global data, fees and condition matter, and limited products can be reprinted.
