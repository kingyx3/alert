import worker, { LazadaMonitor as BaseLazadaMonitor } from "./index.js";

// Deployment entrypoint for the aggressive healthy-path polling cadence.
// Keep the core monitor/backoff logic in index.js unchanged; only the normal
// successful-check interval is allowed down to 5 seconds here.
export class LazadaMonitor extends BaseLazadaMonitor {
  intervalMs() {
    const parsed = Number.parseInt(String(this.env.CHECK_INTERVAL_SECONDS ?? ""), 10);
    const seconds = Number.isFinite(parsed)
      ? Math.min(3600, Math.max(5, parsed))
      : 5;
    return seconds * 1000;
  }
}

export default worker;
