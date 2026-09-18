export function normalizeSearchText(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function parseBooleanSignal(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "1", "yes", "available", "in stock", "instock"].includes(normalized)) return true;
    if (["false", "0", "no", "unavailable", "out of stock", "sold out"].includes(normalized)) return false;
  }
  return null;
}

function iconStockSignal(item) {
  if (!Array.isArray(item?.icons)) return null;
  for (const icon of item.icons) {
    if (!icon || typeof icon !== "object") continue;
    const bizType = String(icon.bizType || "").trim().toLowerCase();
    if (["outofstock", "out_of_stock", "soldout", "sold_out"].includes(bizType)) return false;
  }
  return null;
}

function queryStringStockSignal(item) {
  const raw = item?.querystring ?? item?.queryString ?? "";
  if (!raw) return null;
  try {
    const params = new URLSearchParams(String(raw).replace(/^\?/, ""));
    if (!params.has("stock")) return null;
    const value = Number(params.get("stock"));
    return Number.isFinite(value) ? value > 0 : null;
  } catch {
    return null;
  }
}

function inferInStock(item) {
  for (const key of ["inStock", "isAvailable", "available"]) {
    if (!Object.prototype.hasOwnProperty.call(item, key)) continue;
    const signal = parseBooleanSignal(item[key]);
    if (signal !== null) return signal;
  }

  for (const key of ["soldOut", "isSoldOut", "outOfStock", "isOutOfStock"]) {
    if (!Object.prototype.hasOwnProperty.call(item, key)) continue;
    const signal = parseBooleanSignal(item[key]);
    if (signal !== null) return !signal;
  }

  for (const key of ["stock", "stockCount", "quantity", "availableStock"]) {
    if (!Object.prototype.hasOwnProperty.call(item, key)) continue;
    const raw = item[key];
    if (raw === null || raw === undefined || String(raw).trim() === "") continue;
    const value = Number(raw);
    if (Number.isFinite(value)) return value > 0;
  }

  const availability = String(item.availability || item.stockStatus || item.status || "").toLowerCase();
  if (["out of stock", "sold out", "unavailable"].some((value) => availability.includes(value))) return false;
  if (["in stock", "available"].some((value) => availability.includes(value))) return true;

  const iconSignal = iconStockSignal(item);
  const querySignal = queryStringStockSignal(item);
  if (iconSignal !== null && querySignal !== null) {
    return iconSignal === querySignal ? iconSignal : null;
  }
  if (iconSignal !== null) return iconSignal;
  if (querySignal !== null) return querySignal;

  return null;
}

function normalizeProduct(item) {
  let itemUrl = item.itemUrl || item.url || item.productUrl || item.pdpUrl || item.mobileUrl || "";
  if (typeof itemUrl === "string" && itemUrl.startsWith("//")) itemUrl = `https:${itemUrl}`;

  let price = item.price ?? item.salePrice ?? null;
  if (price !== null && price !== "") {
    const parsed = Number(price);
    price = Number.isFinite(parsed) ? parsed : null;
  } else {
    price = null;
  }

  return {
    name: String(item.name || item.title || item.productName || ""),
    price,
    priceShow: String(item.priceShow || item.priceFormatted || item.originalPriceShow || item.salePriceShow || ""),
    inStock: inferInStock(item),
    sold: String(item.itemSoldCntShow || item.itemSoldCnt || item.sold || ""),
    url: itemUrl || null,
    image: item.image || item.imageUrl || null,
    skuId: item.skuId || item.itemId || item.productId || null,
    sku: item.sku || item.skuCode || null,
    sellerName: item.sellerName || null,
    sellerId: item.sellerId || null,
    categoryId: item.categoryId || null,
  };
}

function productKey(product) {
  for (const field of ["skuId", "sku", "url", "name"]) {
    const value = product[field];
    if (value !== null && value !== undefined && value !== "") return `${field}:${value}`;
  }
  return null;
}

export function mergeProducts(productGroups) {
  const merged = new Map();
  for (const products of productGroups) {
    for (const product of products) {
      const key = productKey(product);
      if (!key) continue;
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, product);
        continue;
      }

      let inStock = null;
      if (existing.inStock === true || product.inStock === true) inStock = true;
      else if (existing.inStock === false || product.inStock === false) inStock = false;
      merged.set(key, { ...product, ...existing, inStock });
    }
  }
  return [...merged.values()];
}

function parseJsonObjectAt(text, start) {
  if (text[start] !== "{") return null;
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < text.length; i += 1) {
    const char = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') inString = false;
      continue;
    }
    if (char === '"') inString = true;
    else if (char === "{") depth += 1;
    else if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        try {
          return JSON.parse(text.slice(start, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function extractEmbeddedJson(body) {
  for (const marker of ['{"templates"', '{"mods"', '{"modsData"', '{"data"']) {
    let start = body.indexOf(marker);
    while (start >= 0) {
      const parsed = parseJsonObjectAt(body, start);
      if (parsed && typeof parsed === "object") return parsed;
      start = body.indexOf(marker, start + marker.length);
    }
  }
  return null;
}

function* candidateItemLists(node, depth = 0) {
  if (depth > 12 || node === null || node === undefined) return;
  if (Array.isArray(node)) {
    for (const value of node) yield* candidateItemLists(value, depth + 1);
    return;
  }
  if (typeof node !== "object") return;
  for (const [key, value] of Object.entries(node)) {
    if (["listItems", "items", "products", "productList"].includes(key) && Array.isArray(value)) {
      const items = value.filter((item) => item && typeof item === "object" && !Array.isArray(item));
      if (items.length) yield items;
    }
    yield* candidateItemLists(value, depth + 1);
  }
}

export function parseProducts(sourceBody, source) {
  let payload = null;
  try {
    payload = JSON.parse(sourceBody);
  } catch {
    payload = extractEmbeddedJson(sourceBody);
  }
  if (!payload || typeof payload !== "object") {
    return { payloadFound: false, products: [], tcgProducts: [] };
  }

  const normalizedGroups = [];
  for (const items of candidateItemLists(payload)) {
    const normalized = items
      .map(normalizeProduct)
      .filter((product) => product.name && (product.url || product.skuId || product.sku));
    if (normalized.length) normalizedGroups.push(normalized);
  }

  const products = source.collectAllLists
    ? mergeProducts(normalizedGroups)
    : normalizedGroups.reduce((best, current) => (current.length > best.length ? current : best), []);

  const tcgProducts = products.filter((product) => {
    const name = normalizeSearchText(product.name);
    return source.keywords.some((keyword) => name.includes(keyword));
  });

  return { payloadFound: true, products, tcgProducts };
}
