# SG Collectibles Market-Intelligence Worker

A separate Cloudflare Worker that discovers Singapore collectible drops, enriches them with secondary-market data, scores margin **and liquidity**, and sends Telegram alerts only when the opportunity clears configurable thresholds.

The implementation is intentionally modular. See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for extension points for market providers, social adapters, retailer parsers, storage/history sinks, and new collectible categories.
