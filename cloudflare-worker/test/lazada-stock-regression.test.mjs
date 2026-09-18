import assert from "node:assert/strict";
import test from "node:test";

import { parseProducts } from "../scripts/lazada-product-parser.mjs";

const source = {
  collectAllLists: false,
  keywords: ["pokemon", "tcg", "trading card"],
};

function parseItem(item) {
  return parseProducts(JSON.stringify({
    mods: {
      listItems: [item],
    },
  }), source).tcgProducts[0];
}

test("real Lazada listItems sold-out schema is classified out of stock", () => {
  const product = parseItem({
    name: "Pokémon Trading Card Game: Mega Evolution - Pitch Black Sleeved Boosters [Limit 10 per person]",
    itemId: "13773062548",
    skuId: "124743649852",
    sku: "13773062548_SGAMZ",
    itemUrl: "//www.lazada.sg/products/pdp-i13773062548.html",
    priceShow: "$6.90",
    inStock: false,
    icons: [
      { domClass: "76328", type: "img", group: "6", showType: "0", bizType: "outofstock" },
      { domClass: "76083", type: "img", group: "3", showType: "0", bizType: "lazMall" },
    ],
    querystring: "search=1&sale=15639&price=6.9&stock=0&lang=en",
  });

  assert.ok(product);
  assert.equal(product.inStock, false);
});

test("listing presence by itself is not treated as stock", () => {
  const product = parseItem({
    name: "Pokémon TCG Unknown Stock Product",
    itemId: "12345",
    itemUrl: "//www.lazada.sg/products/pdp-i12345.html",
    priceShow: "$69.90",
  });

  assert.ok(product);
  assert.equal(product.inStock, null);
});

test("out-of-stock Lazada badge is a defensive fallback when inStock is absent", () => {
  const product = parseItem({
    name: "Pokémon TCG Badge Sold Out Product",
    itemId: "23456",
    itemUrl: "//www.lazada.sg/products/pdp-i23456.html",
    icons: [{ bizType: "outofstock" }],
  });

  assert.ok(product);
  assert.equal(product.inStock, false);
});

test("Lazada query-string stock is a fallback when stronger stock fields are absent", () => {
  const unavailable = parseItem({
    name: "Pokémon TCG Query Zero Product",
    itemId: "34567",
    itemUrl: "//www.lazada.sg/products/pdp-i34567.html",
    querystring: "search=1&stock=0&lang=en",
  });
  const available = parseItem({
    name: "Pokémon TCG Query Positive Product",
    itemId: "45678",
    itemUrl: "//www.lazada.sg/products/pdp-i45678.html",
    querystring: "search=1&stock=12&lang=en",
  });

  assert.equal(unavailable.inStock, false);
  assert.equal(available.inStock, true);
});

test("explicit inStock remains authoritative over fallback metadata", () => {
  const product = parseItem({
    name: "Pokémon TCG Explicit Available Product",
    itemId: "56789",
    itemUrl: "//www.lazada.sg/products/pdp-i56789.html",
    inStock: true,
    icons: [{ bizType: "outofstock" }],
    querystring: "search=1&stock=0&lang=en",
  });

  assert.ok(product);
  assert.equal(product.inStock, true);
});

test("conflicting fallback-only signals remain unknown rather than causing a false alert", () => {
  const product = parseItem({
    name: "Pokémon TCG Conflicting Fallback Product",
    itemId: "67890",
    itemUrl: "//www.lazada.sg/products/pdp-i67890.html",
    icons: [{ bizType: "outofstock" }],
    querystring: "search=1&stock=5&lang=en",
  });

  assert.ok(product);
  assert.equal(product.inStock, null);
});
