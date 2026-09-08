export async function sendTelegram(env, alert) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) return { skipped: true };
  const s = alert.scoring || {};
  const heading = alert.signalType === "SUPPLY"
    ? "📦 SUPPLY SIGNAL"
    : alert.signalType === "DROP" && s.action === "PASS"
      ? "🚨 DROP SIGNAL"
      : s.action === "BUY" ? "🔥 BUY OPPORTUNITY" : "👀 WATCH";
  const lines = [`${heading} · Score ${s.score ?? 0}/100`, alert.name, `Source: ${alert.sourceName}`];
  if (alert.location) lines.push(`Where: ${alert.location}`);
  if (alert.timingHint) lines.push(`When: ${alert.timingHint}`);
  if (alert.retailSgd) lines.push(`Retail: S$${alert.retailSgd.toFixed(2)}`);
  if (alert.marketSgd) lines.push(`Market est.: S$${alert.marketSgd.toFixed(2)}`);
  if (s.netMarginPct !== null && s.netMarginPct !== undefined) lines.push(`Est. net margin: ${s.netMarginPct}% (gross ${s.grossMarginPct}%)`);
  lines.push(`Demand ${s.demandScore ?? 0}/100 · Dead inventory risk ${s.deadInventoryRisk ?? 0}/100`);
  if (alert.market?.sales30d !== null && alert.market?.sales30d !== undefined) lines.push(`30d sales velocity: ${alert.market.sales30d}`);
  if (alert.market?.totalListings !== null && alert.market?.totalListings !== undefined) lines.push(`Active market listings: ${alert.market.totalListings}`);
  if (alert.market?.provider) lines.push(`Market data: ${alert.market.provider}`);
  if (alert.reason?.length) lines.push(`Why: ${alert.reason.slice(0, 4).join("; ")}`);
  if (alert.url) lines.push(alert.url);

  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHANNEL_ID, text: lines.join("\n"), disable_web_page_preview: false }),
  });
  if (!resp.ok) throw new Error(`Telegram HTTP ${resp.status}: ${(await resp.text()).slice(0, 180)}`);
  return { skipped: false };
}
