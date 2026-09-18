import assert from "node:assert/strict";
import test from "node:test";

import { parseProducts } from "../scripts/lazada-product-parser.mjs";

const source = {
  collectAllLists: false,
  listedMeansInStock: true,
  keywords: ["pokemon", "tcg", "trading card"],
};

function parseItem(item) {
  return parseProducts(JSON.stringify({
    mods: {
      listItems: [item],
    },
  }), source).tcgProducts[0];
}

test("trusted Lazada listing presence is an in-stock fallback when stock fields are absent", () => {
  const product = parseItem({
    name: "Pokémon TCG Booster Box",
    itemId: "12345",
    itemUrl: "//www.lazada.sg/products/pokemon-tcg-booster-box-i12345.html",
    priceShow: "$69.90",
    itemSoldCntShow: "42 sold",
  });

  assert.ok(product);
  assert.equal(product.inStock, true);
});

test("explicit sold-out signals override the listing-presence fallback", () => {
  const product = parseItem({
    name: "Pokémon TCG Sold Out Box",
    itemId: "99999",
    itemUrl: "//www.lazada.sg/products/pokemon-tcg-sold-out-i99999.html",
    isSoldOut: true,
  });

  assert.ok(product);
  assert.equal(product.inStock, false);
});

test("explicit zero quantity overrides the listing-presence fallback", () => {
  const product = parseItem({
    name: "Pokémon TCG Zero Stock Box",
    itemId: "77777",
    itemUrl: "//www.lazada.sg/products/pokemon-tcg-zero-stock-i77777.html",
    stockCount: 0,
  });

  assert.ok(product);
  assert.equal(product.inStock, false);
});
