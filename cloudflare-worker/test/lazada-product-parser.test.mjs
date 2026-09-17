import assert from "node:assert/strict";
import test from "node:test";
import { parseProducts } from "../scripts/lazada-product-parser.mjs";

const payload = JSON.stringify({
  result: {
    components: {
      accessories: {
        productList: [
          { title: "Pokémon Center Original Deck Case", sku: "ACCESSORY-1", skuId: 1, inStock: 1 },
          { title: "Pokémon Center Original Deck Shield", sku: "ACCESSORY-2", skuId: 2, inStock: 1 },
          { title: "Pokémon Center Plush", sku: "ACCESSORY-3", skuId: 3, inStock: 1 },
        ],
      },
      cards: {
        productList: [
          { title: "Pokémon Trading Card Game Booster Box", sku: "TCG-1", skuId: 11, inStock: 1 },
          { title: "Pokémon TCG Elite Trainer Box", sku: "TCG-2", skuId: 12, inStock: 1 },
        ],
      },
    },
  },
});

test("SCRAPING_URL_3 mode scans all product lists and keeps only TCG titles", () => {
  const parsed = parseProducts(payload, {
    collectAllLists: true,
    keywords: ["tcg", "trading card game", "trading card"],
  });

  assert.equal(parsed.payloadFound, true);
  assert.equal(parsed.products.length, 5);
  assert.deepEqual(
    parsed.tcgProducts.map((product) => product.sku).sort(),
    ["TCG-1", "TCG-2"],
  );
});

test("legacy source mode still selects the largest candidate list", () => {
  const parsed = parseProducts(payload, {
    collectAllLists: false,
    keywords: ["pokemon"],
  });

  assert.equal(parsed.products.length, 3);
  assert.deepEqual(
    parsed.products.map((product) => product.sku).sort(),
    ["ACCESSORY-1", "ACCESSORY-2", "ACCESSORY-3"],
  );
});
