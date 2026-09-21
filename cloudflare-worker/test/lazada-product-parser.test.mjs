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

test("collect-all-lists mode scans all product lists and keeps only TCG titles", () => {
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

test("trusted source mode still selects the largest candidate list", () => {
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

test("seller allowlist keeps only the official Pokemon Lazada shop", () => {
  const parsed = parseProducts(JSON.stringify({
    mods: {
      listItems: [
        {
          name: "Pokémon TCG Official Product",
          itemId: "OFFICIAL-1",
          inStock: true,
          sellerId: "1628720011",
          sellerName: "Pokémon Store Online Singapore",
        },
        {
          name: "Pokémon TCG Third Party Product",
          itemId: "THIRD-PARTY-1",
          inStock: true,
          sellerId: "999999",
          sellerName: "Pokémon Store Online Singapore",
        },
        {
          name: "Pokémon TCG Official Product Without Seller ID",
          itemId: "OFFICIAL-2",
          inStock: true,
          sellerName: "Pokemon Store Online Singapore",
        },
        {
          name: "Pokémon TCG Unknown Seller Product",
          itemId: "UNKNOWN-1",
          inStock: true,
        },
      ],
    },
  }), {
    collectAllLists: false,
    keywords: ["pokemon", "tcg"],
    sellerIds: ["1628720011"],
    sellerNames: ["pokemon store online singapore"],
  });

  assert.deepEqual(
    parsed.tcgProducts.map((product) => product.skuId),
    ["OFFICIAL-1", "OFFICIAL-2"],
  );
});

test("ambiguous explicit stock fields fall through to stronger quantity/status signals", () => {
  const parsed = parseProducts(JSON.stringify({
    data: {
      products: [
        {
          title: "Pokémon TCG Quantity Product",
          sku: "QTY-1",
          inStock: null,
          stockCount: 3,
        },
        {
          title: "Pokémon TCG Status Product",
          sku: "STATUS-1",
          soldOut: "unknown",
          stockStatus: "in stock",
        },
        {
          title: "Pokémon TCG Empty Quantity Product",
          sku: "EMPTY-1",
          inStock: null,
          stock: "",
          availability: "available",
        },
      ],
    },
  }), {
    collectAllLists: false,
    keywords: ["tcg"],
  });

  assert.deepEqual(
    Object.fromEntries(parsed.tcgProducts.map((product) => [product.sku, product.inStock])),
    {
      "QTY-1": true,
      "STATUS-1": true,
      "EMPTY-1": true,
    },
  );
});
