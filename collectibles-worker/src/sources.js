const DEFAULT_SOURCES = [
  {
    id: "toysrus-sg-pokemon",
    name: "Toys\"R\"Us Singapore - Pokemon",
    kind: "retailer",
    url: "https://www.toysrus.com.sg/pokemon/",
    intervalSeconds: 300,
    location: "Toys\"R\"Us Singapore stores / online",
    games: ["pokemon", "collectibles"],
    priority: 92,
  },
  {
    id: "toysrus-sg-beyblade",
    name: "Toys\"R\"Us Singapore - Beyblade",
    kind: "retailer",
    url: "https://www.toysrus.com.sg/beyblade/",
    intervalSeconds: 300,
    location: "Toys\"R\"Us Singapore stores / online",
    games: ["beyblade", "collectibles"],
    priority: 92,
  },
  {
    id: "tom-stefanie",
    name: "Tom & Stefanie",
    kind: "retailer",
    url: "https://tomandstefanie.com.sg/",
    intervalSeconds: 300,
    location: "Woodlands Civic Centre / PLQ / EastPoint Mall",
    games: ["pokemon", "beyblade", "collectibles"],
    priority: 94,
  },
  {
    id: "metro-sg-pokemon",
    name: "Metro Singapore - Pokemon",
    kind: "retailer",
    url: "https://metro.com.sg/search?q=pokemon",
    intervalSeconds: 600,
    location: "Metro Singapore stores / online",
    games: ["pokemon", "collectibles"],
    priority: 82,
  },
  {
    id: "hammerhouse-beyblade",
    name: "HammerHouse - Beyblade X",
    kind: "retailer",
    url: "https://hammerhouse.com.sg/collections/beyblade-x",
    intervalSeconds: 300,
    location: "Singapore",
    games: ["beyblade", "collectibles"],
    priority: 90,
  },
  {
    id: "kiddy-palace-toys",
    name: "Kiddy Palace - Toys / Beyblade X",
    kind: "retailer",
    url: "https://kiddypalace.com.sg/collections/toys",
    intervalSeconds: 300,
    location: "Kiddy Palace Singapore stores / online",
    games: ["pokemon", "beyblade", "collectibles"],
    priority: 90,
  },
  {
    id: "game-academia-tcg",
    name: "Game Academia - TCG",
    kind: "retailer",
    url: "https://game-academia.myshopify.com/collections/all-tcg",
    intervalSeconds: 300,
    location: "Peninsula Shopping Complex",
    games: ["pokemon", "one-piece", "digimon", "union-arena", "gundam", "collectibles"],
    priority: 84,
  },
  {
    id: "popmart-sg",
    name: "POP MART Singapore",
    kind: "retailer",
    url: "https://www.popmart.com/sg",
    intervalSeconds: 300,
    location: "Singapore stores / online",
    games: ["pop-mart", "collectibles"],
    priority: 90,
  },
  {
    id: "lego-sg-new",
    name: "LEGO Singapore - New Sets",
    kind: "retailer",
    url: "https://www.lego.com/en-sg/categories/new-sets-and-products",
    intervalSeconds: 900,
    location: "LEGO Singapore online / certified stores",
    games: ["lego", "collectibles"],
    priority: 78,
  },
  {
    id: "lego-sg-bestsellers",
    name: "LEGO Singapore - Bestsellers",
    kind: "retailer",
    url: "https://www.lego.com/en-sg/categories/bestsellers",
    intervalSeconds: 1800,
    location: "LEGO Singapore online / certified stores",
    games: ["lego", "collectibles"],
    priority: 80,
  },
  {
    id: "maxsoft-trading-cards",
    name: "Maxsoft - Trading Cards",
    kind: "upstream",
    url: "https://maxsoftonline.com/collections/trading-card-games",
    intervalSeconds: 1800,
    location: "Singapore",
    games: ["pokemon", "one-piece", "magic", "collectibles"],
    priority: 88,
  },
  {
    id: "pokemon-sg",
    name: "Pokemon Singapore",
    kind: "upstream",
    url: "https://sg.portal-pokemon.com/card/",
    intervalSeconds: 1800,
    location: "Singapore",
    games: ["pokemon"],
    priority: 92,
  },
  {
    id: "one-piece-official",
    name: "One Piece Card Game - Official Asia",
    kind: "upstream",
    url: "https://asia-en.onepiece-cardgame.com/products/",
    intervalSeconds: 1800,
    location: "Asia / Singapore",
    games: ["one-piece"],
    priority: 90,
  },
  {
    id: "magic-products",
    name: "Magic: The Gathering - Products",
    kind: "upstream",
    url: "https://magic.wizards.com/en/products",
    intervalSeconds: 3600,
    location: "Global / Singapore WPN",
    games: ["magic"],
    priority: 82,
  },
  {
    id: "beyblade-official",
    name: "Takara Tomy - Beyblade X",
    kind: "upstream",
    url: "https://beyblade.takaratomy.co.jp/beyblade-x/",
    intervalSeconds: 3600,
    location: "Japan / Singapore retail pipeline",
    games: ["beyblade"],
    priority: 84,
  },
  {
    id: "tcgcards-sg-news",
    name: "TCGCards.sg Singapore News",
    kind: "community",
    url: "https://www.tcgcards.sg/",
    intervalSeconds: 900,
    location: "Singapore",
    games: ["pokemon", "collectibles"],
    priority: 78,
  },
];

const GAME_TERMS = {
  pokemon: ["pokemon", "pokémon", "pokemon tcg", "scarlet & violet", "elite trainer box", "etb"],
  "one-piece": ["one piece card game", "one piece tcg", "op-", "eb-", "prb-", "starter deck st-"],
  magic: ["magic the gathering", "magic: the gathering", "mtg", "secret lair", "collector booster"],
  lorcana: ["lorcana"],
  yugioh: ["yu-gi-oh", "yugioh"],
  digimon: ["digimon card game", "digimon tcg"],
  "star-wars-unlimited": ["star wars unlimited"],
  "flesh-and-blood": ["flesh and blood", "fab tcg"],
  riftbound: ["riftbound"],
  "union-arena": ["union arena"],
  gundam: ["gundam card game", "gundam tcg"],
  beyblade: ["beyblade", "beyblade x", "takara tomy", "bx-", "ux-", "cx-"],
  lego: ["lego", "lego exclusive", "lego icons", "lego ideas", "gift with purchase", "gwp"],
  "pop-mart": ["pop mart", "popmart", "labubu", "the monsters", "skullpanda", "hirono", "crybaby", "dimoo", "molly"],
  funko: ["funko", "funko pop", "funko exclusive"],
  "hot-wheels": ["hot wheels", "treasure hunt", "super treasure hunt", "sth"],
  tamagotchi: ["tamagotchi"],
};

const URGENCY_TERMS = [
  "restock", "restocked", "drop", "dropping", "available now", "available today", "launch",
  "limited stock", "limited stocks", "limited quantity", "limited quantities", "while stocks last",
  "first come first served", "first-come-first-served", "queue", "in-store only", "tomorrow", "this weekend",
  "new arrival", "just arrived", "exclusive",
];

const REPRINT_TERMS = [
  "reprint", "reprinted", "additional production", "additional allocation", "second printing", "new shipment",
  "restock wave", "more stock coming", "more units", "wide release", "mass release", "new allocation",
];

export const SG_LOCATION_TERMS = [
  "Jewel Changi Airport", "PLQ", "Paya Lebar Quarter", "EastPoint Mall", "Woodlands Civic Centre",
  "VivoCity", "NEX", "Suntec City", "Plaza Singapura", "Bugis Junction", "Jurong Point",
  "Northpoint City", "Waterway Point", "Tampines Mall", "Orchard", "Peninsula Shopping Complex",
];

function decodeEntities(text) {
  return String(text || "")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function normalize(text) {
  return decodeEntities(text).toLowerCase().replace(/\s+/g, " ").trim();
}

function absoluteUrl(value, baseUrl) {
  try { return new URL(value, baseUrl).toString(); } catch { return baseUrl; }
}

function numericPrice(value) {
  const cleaned = String(value ?? "").replace(/,/g, "").match(/(?:s\$|sgd|\$)?\s*(\d{1,5}(?:\.\d{1,2})?)/i);
  if (!cleaned) return null;
  const n = Number(cleaned[1]);
  return Number.isFinite(n) && n > 0 && n < 100000 ? n : null;
}

export function stripHtml(html) {
  return decodeEntities(String(html || "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " "))
    .trim();
}

export function detectGames(text) {
  const haystack = normalize(text);
  const found = [];
  for (const [game, terms] of Object.entries(GAME_TERMS)) {
    if (terms.some((term) => haystack.includes(normalize(term)))) found.push(game);
  }
  return found;
}

export function extractLocationHint(text, fallback = null) {
  const raw = String(text || "");
  const found = SG_LOCATION_TERMS.find((term) => raw.toLowerCase().includes(term.toLowerCase()));
  return found || fallback || null;
}

export function extractTimingHint(text) {
  const raw = String(text || "").replace(/\s+/g, " ");
  const patterns = [
    /\b(?:today|tomorrow|this weekend|this saturday|this sunday)\b[^.!?]{0,45}/i,
    /\b(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?\b[^.!?]{0,55}/i,
    /\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b[^.!?]{0,45}/i,
    /\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b/i,
  ];
  const parts = [];
  for (const pattern of patterns) {
    const match = raw.match(pattern);
    if (match) parts.push(match[0].trim());
  }
  return [...new Set(parts)].join(" · ").slice(0, 140) || null;
}

export function termScore(text, terms) {
  const haystack = normalize(text);
  if (!haystack) return 0;
  let hits = 0;
  for (const term of terms) if (haystack.includes(normalize(term))) hits += 1;
  return Math.min(100, hits * 22);
}

export function urgencyScore(text) {
  return termScore(text, URGENCY_TERMS);
}

export function reprintRiskScore(text) {
  return termScore(text, REPRINT_TERMS);
}

function walkJsonLd(node, rows, baseUrl) {
  if (!node) return;
  if (Array.isArray(node)) {
    for (const item of node) walkJsonLd(item, rows, baseUrl);
    return;
  }
  if (typeof node !== "object") return;
  const type = node["@type"];
  if (type === "Product" || (Array.isArray(type) && type.includes("Product"))) {
    const offers = Array.isArray(node.offers) ? node.offers[0] : node.offers || {};
    const name = node.name || node.headline || "";
    const priceSgd = numericPrice(offers.price ?? offers.lowPrice ?? node.price);
    const url = absoluteUrl(node.url || offers.url || "", baseUrl);
    if (name) rows.push({ name: stripHtml(name), priceSgd, url });
  }
  for (const value of Object.values(node)) walkJsonLd(value, rows, baseUrl);
}

export function extractProductsFromHtml(html, baseUrl) {
  const body = String(html || "");
  const rows = [];

  for (const match of body.matchAll(/<script[^>]+type=[#']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)) {
    try { walkJsonLd(JSON.parse(match[1]), rows, baseUrl); } catch { /* malformed JSON-LD */ }
  }

  // Common Shopify/product-card fallback. Deliberately bounded and heuristic.
  const anchors = [...body.matchAll(/<a\b[^>]*href=["']([^"']*(?:\/products\/|\/product\/)[^"']*)["'][^>]*>([\s\S]{0,1800}?)<\/a>/gi)].slice(0, 120);
  for (const [, href, inner] of anchors) {
    const text = stripHtml(inner);
    if (text.length < 3) continue;
    const priceSgd = numericPrice(text);
    const name = text.replace(/(?:s\$|sgd|\$)\s*\d[\d,.]*/gi, " ").replace(/\s+/g, " ").trim().slice(0, 180);
    if (name) rows.push({ name, priceSgd, url: absoluteUrl(href, baseUrl) });
  }

  const seen = new Set();
  return rows.filter((row) => {
    const key = `${normalize(row.name)}|${row.url}`;
    if (!row.name || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 150);
}

export async function fetchText(url) {
  const response = await fetch(url, {
    method: "GET",
    redirect: "follow",
    headers: {
      "user-agent": "kingyx3-collectibles-monitor/1.0 (+https://github.com/kingyx3/alert)",
      accept: "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.7",
      "accept-language": "en-SG,en;q=0.9",
    },
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`Source HTTP ${response.status}`);
  if (body.length < 80) throw new Error("Source response was unexpectedly small");
  return { body, status: response.status, finalUrl: response.url || url, contentType: response.headers.get("content-type") || "" };
}

function validSource(row) {
  if (!row || typeof row !== "object" || !row.id || !row.url) return null;
  let parsed;
  try { parsed = new URL(row.url); } catch { return null; }
  if (!/^https?:$/.test(parsed.protocol)) return null;
  return {
    id: String(row.id).slice(0, 80),
    name: String(row.name || row.id).slice(0, 120),
    kind: ["retailer", "upstream", "community"].includes(row.kind) ? row.kind : "retailer",
    url: parsed.toString(),
    intervalSeconds: Math.max(120, Math.min(21600, Number(row.intervalSeconds || 600))),
    location: row.location ? String(row.location).slice(0, 160) : "Singapore",
    games: Array.isArray(row.games) ? row.games.map(String).slice(0, 20) : ["collectibles"],
    priority: Math.max(0, Math.min(100, Number(row.priority || 70))),
  };
}

export function loadSources(env) {
  const rows = [...DEFAULT_SOURCES];
  if (env.EXTRA_SOURCES_JSON) {
    try {
      const extra = JSON.parse(env.EXTRA_SOURCES_JSON);
      if (Array.isArray(extra)) rows.push(...extra);
    } catch { /* invalid optional config ignored */ }
  }
  const seen = new Set();
  return rows.map(validSource).filter((row) => row && !seen.has(row.id) && seen.add(row.id));
}
