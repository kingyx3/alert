export function shouldDeliverTelegramAlert(alert) {
  const s = alert?.scoring || {};
  if (s.action === "BUY" || s.action === "WATCH") return true;

  // PASS rows may still be useful when they come from a concrete social post,
  // but aggregated website/news pages are too broad to bypass opportunity scoring.
  if (s.action !== "PASS" || alert?.sourceKind !== "social" || !alert?.signalType) return false;

  const urgency = Number(s.urgencyScore || 0);
  const supplyRisk = Number(alert.supplyRisk || 0);
  const demand = Number(s.demandScore || 0);
  const score = Number(s.score || 0);
  const strongSignal = Math.max(urgency, supplyRisk) >= 66;
  const concreteContext = Boolean(alert.timingHint || alert.retailSgd || alert.marketSgd || supplyRisk >= 80);
  return strongSignal && demand >= 45 && score >= 40 && concreteContext;
}

export function buildTelegramMessage(alert) {
  const s = alert.scoring || {};
  const signalOnly = s.action === "PASS" && Boolean(alert.signalType);
  const heading = s.action === "BUY"
    ? "🔥 BUY OPPORTUNITY"
    : s.action === "WATCH"
      ? "👀 WATCH"
      : alert.signalType === "SUPPLY" ? "⚠️ SUPPLY CHECK" : "⚡ CHECK NOW";
  const action = s.action === "BUY"
    ? "BUY"
    : s.action === "WATCH"
      ? "WATCH"
      : alert.signalType === "SUPPLY" ? "RECHECK SUPPLY" : "CHECK NOW";

  const lines = [`${heading} · Score ${s.score ?? 0}/100`, alert.name, `Action: ${action}`, `Source: ${alert.sourceName}`];
  if (alert.location) lines.push(`Where: ${alert.location}`);
  if (alert.timingHint) lines.push(`When: ${alert.timingHint}`);
  if (alert.retailSgd) lines.push(`Retail: S$${alert.retailSgd.toFixed(2)}`);
  if (alert.marketSgd) lines.push(`Market est.: S$${alert.marketSgd.toFixed(2)}`);
  if (s.netMarginPct !== null && s.netMarginPct !== undefined) lines.push(`Est. net margin: ${s.netMarginPct}% (gross ${s.grossMarginPct}%)`);

  const hasOpportunityEvidence = Boolean(
    alert.retailSgd || alert.marketSgd ||
    alert.market?.sales30d !== null && alert.market?.sales30d !== undefined ||
    alert.market?.totalListings !== null && alert.market?.totalListings !== undefined
  );

  if (hasOpportunityEvidence) {
    lines.push(`Demand ${s.demandScore ?? 0}/100 · Dead inventory risk ${s.deadInventoryRisk ?? 0}/100`);
    if (alert.market?.sales30d !== null && alert.market?.sales30d !== undefined) lines.push(`30d sales velocity: ${alert.market.sales30d}`);
    if (alert.market?.totalListings !== null && alert.market?.totalListings !== undefined) lines.push(`Active market listings: ${alert.market.totalListings}`);
    if (alert.market?.provider) lines.push(`Market data: ${alert.market.provider}`);
  } else if (signalOnly) {
    const signalParts = [];
    if (s.urgencyScore) signalParts.push(`drop urgency ${s.urgencyScore}/100`);
    if (alert.supplyRisk) signalParts.push(`supply/reprint risk ${alert.supplyRisk}/100`);
    if (signalParts.length) lines.push(`Signal: ${signalParts.join(" · ")}`);
    lines.push(alert.signalType === "SUPPLY"
      ? "Next step: Re-check the source and supply/reprint details before buying or holding inventory."
      : "Next step: Open the source and verify stock, price and timing before travelling or buying.");
  }

  if (alert.reason?.length) lines.push(`Why: ${alert.reason.slice(0, 4).join("; ")}`);
  if (alert.url) lines.push(alert.url);
  return lines.join("\n");
}

export async function sendTelegram(env, alert) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHANNEL_ID) return { skipped: true, reason: "not-configured" };
  if (!shouldDeliverTelegramAlert(alert)) return { skipped: true, reason: "not-actionable" };

  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHANNEL_ID, text: buildTelegramMessage(alert), disable_web_page_preview: false }),
  });
  if (!resp.ok) throw new Error(`Telegram HTTP ${resp.status}: ${(await resp.text()).slice(0, 180)}`);
  return { skipped: false };
}
