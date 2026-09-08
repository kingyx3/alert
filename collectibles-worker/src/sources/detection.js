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

export function normalize(text) {
  return decodeEntities(text).toLowerCase().replace(/\s+/g, " ").trim();
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

export function urgencyScore(text) { return termScore(text, URGENCY_TERMS); }
export function reprintRiskScore(text) { return termScore(text, REPRINT_TERMS); }
