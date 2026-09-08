export function shouldDeliverTelegramAlert(alert) {
  const s = alert?.scoring || {};
  if (s.action === "BUY" || s.action === "WATCH") return true;

  // PASS-level DROP alerts are social-first. A single social post is an atomic
  // event; an aggregated website/news page is not reliable enough to imply a drop.
  if (s.action !== "PASS" || alert?.sourceKind !== "social" || !alert?.signalType) return false;

  const urgency = Number(s.urgencyScore || 0);
  const supplyRisk = Number(alert.supplyRisk || 0);
  const hasDirectSource = Boolean(alert.url || alert.timingHint || alert.retailSgd || alert.marketSgd);

  if (alert.signalType === "DROP") {
    // Social drop/restock language is more impactful than a weak aggregate score,
    // so do not require demand/overall-score thresholds when the post itself is strong.
    return urgency >= 66 && hasDirectSource;
  }

  if (alert.signalType === "SUPPLY") {
    return supplyRisk >= 80 && hasDirectSource;
  }

  return false;
}

export function buildTelegramMessage(alert) {
  const s = alert.scoring || {};
  const signalOnly = s.action === "PASS" && Boolean(alert.signalType);
  const socialDrop = signalOnly && alert.sourceKind === "social" && alert.signalType === "DROP";
  const socialSupply = signalOnly && alert.sourceKind === "social" && alert.signalType === "SUPPLY";
  const heading = s.action === "BUY"
    ? "🔥 BUY OPPORTUNITY"
    : s.action === "WATCH"
      ? "👀 WATCH"
      : socialDrop
        ? "📣 SOCIAL DROP"
        : socialSupply
          ? "📦 SOCIAL SUPPLY"
          : alert.signalType === "SUPPLY" ? "⚠️ SUPPLY CHECK" : "⚡ CHECK NOW";
  const action = s.action === "BUY"
    ? "BUY"
    : s.action === "WATCH"
      ? "WATCH"
      : alert.signalType === "SUPPLY" ? "RECHECK SUPPLY" : "CHECK DROP";

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
      : "Next step: Open the social post and verify stock, price and timing before travelling or buying.");
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
