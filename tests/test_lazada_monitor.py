import unittest

from lazada_monitor import (
    extract_products,
    infer_in_stock,
    is_tcg_product,
    parse_bool,
    product_key,
    stable_state_entry,
)


class LazadaMonitorTests(unittest.TestCase):
    def test_parse_bool_handles_string_false(self):
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("sold out"))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("in stock"))

    def test_stock_inference_uses_explicit_signals(self):
        self.assertTrue(infer_in_stock({"inStock": True}))
        self.assertFalse(infer_in_stock({"inStock": "false"}))
        self.assertFalse(infer_in_stock({"isSoldOut": True}))
        self.assertTrue(infer_in_stock({"quantity": 2}))
        self.assertFalse(infer_in_stock({"quantity": 0}))
        self.assertFalse(infer_in_stock({"name": "No stock signal"}))

    def test_extracts_product_list_and_normalizes_url(self):
        payload = {
            "mods": {
                "listItems": [
                    {
                        "name": "Pokémon TCG Elite Trainer Box",
                        "skuId": "123",
                        "itemUrl": "//www.lazada.sg/products/example-i123.html",
                        "inStock": True,
                        "price": "89.90",
                    },
                    {
                        "name": "Unrelated Toy",
                        "skuId": "456",
                        "itemUrl": "//www.lazada.sg/products/toy-i456.html",
                        "inStock": False,
                    },
                ]
            }
        }

        products = extract_products(payload)
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["url"], "https://www.lazada.sg/products/example-i123.html")
        self.assertEqual(products[0]["price"], 89.90)
        self.assertTrue(products[0]["inStock"])

    def test_pokemon_accent_matches_default_keywords(self):
        product = {"name": "Pokémon Scarlet & Violet Trading Card Game"}
        self.assertTrue(is_tcg_product(product))

    def test_state_entry_ignores_changing_price_and_sold_count(self):
        product = {
            "name": "Pokemon TCG Booster",
            "url": "https://example.test/item",
            "skuId": "sku-1",
            "sku": None,
            "price": 10.0,
            "sold": "10 sold",
        }
        before = stable_state_entry(product)
        product["price"] = 12.0
        product["sold"] = "11 sold"
        after = stable_state_entry(product)
        self.assertEqual(before, after)
        self.assertEqual(product_key(product), "skuId:sku-1")


if __name__ == "__main__":
    unittest.main()
