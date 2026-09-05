#!/usr/bin/env python3
"""Lazada TCG restock monitor.

This monitor intentionally does not attempt to bypass CAPTCHA, bot challenges,
rate limits, or other access controls. A blocked/challenged response is treated
as a source failure so the last known stock state is preserved.
"""

from __future__ import annotations

import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from notification_service import create_notification_service

STATE_PATH = Path(os.getenv("STOCK_STATE_PATH", ".state/lazada_stock.json"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
ALERT_ON_FIRST_RUN = os.getenv("ALERT_ON_FIRST_RUN", "false").lower() in {"1", "true", "yes"}
DEFAULT_KEYWORDS = "pokemon,pokémon,tcg,trading card"

# Deliberately stable and identifiable. Do not rotate/spoof headers to evade controls.
HEADERS = {
    "User-Agent": "kingyx3-alert/2.0 (+https://github.com/kingyx3/alert)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
}

BLOCK_MARKERS = (
    "captcha",
    "security check",
    "verify you are human",
    "access denied",
    "unusual traffic",
    "robot check",
)


class SourceBlocked(RuntimeError):
    pass


class SourceParseError(RuntimeError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalized_text(value: Any) -> str:
    text = str(value or "").lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def keyword_list() -> List[str]:
    raw = os.getenv("TCG_KEYWORDS", DEFAULT_KEYWORDS)
    return [normalized_text(x.strip()) for x in raw.split(",") if x.strip()]


def fetch_source(url: str) -> tuple[Optional[Dict[str, Any]], str]:
    if not url:
        raise RuntimeError("SCRAPING_URL is not set")

    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    body = response.text
    lower_body = body.lower()

    if response.status_code in {403, 429} or any(marker in lower_body for marker in BLOCK_MARKERS):
        raise SourceBlocked(
            f"Source refused/challenged the monitor (HTTP {response.status_code}). "
            "No bypass will be attempted."
        )

    response.raise_for_status()

    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            return parsed, body
    except ValueError:
        pass

    # Lazada-like pages/endpoints may embed a JSON object in otherwise textual HTML.
    # Parse a normal embedded payload if present; do not execute JS or circumvent a challenge.
    decoder = json.JSONDecoder()
    for marker in ('{"mods"', '{"modsData"', '{"data"'):
        start = body.find(marker)
        if start >= 0:
            try:
                parsed, _ = decoder.raw_decode(body[start:])
                if isinstance(parsed, dict):
                    return parsed, body
            except ValueError:
                continue

    return None, body


def candidate_item_lists(node: Any) -> Iterable[List[Dict[str, Any]]]:
    """Yield arrays that look like Lazada product collections."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"listItems", "items", "products"} and isinstance(value, list):
                dict_items = [x for x in value if isinstance(x, dict)]
                if dict_items:
                    yield dict_items
            yield from candidate_item_lists(value)
    elif isinstance(node, list):
        for value in node:
            yield from candidate_item_lists(value)


def infer_in_stock(item: Dict[str, Any]) -> bool:
    if "inStock" in item:
        return bool(item.get("inStock"))
    if "soldOut" in item:
        return not bool(item.get("soldOut"))

    for key in ("stock", "stockCount", "quantity", "availableStock"):
        if key in item:
            try:
                return float(item[key]) > 0
            except (TypeError, ValueError):
                pass

    availability = normalized_text(item.get("availability"))
    if availability:
        if any(x in availability for x in ("out of stock", "sold out", "unavailable")):
            return False
        if any(x in availability for x in ("in stock", "available")):
            return True

    # Do not guess that a product is available when the payload has no stock signal.
    return False


def normalize_product(item: Dict[str, Any]) -> Dict[str, Any]:
    item_url = item.get("itemUrl") or item.get("url") or ""
    if isinstance(item_url, str) and item_url.startswith("//"):
        item_url = "https:" + item_url

    price = item.get("price")
    try:
        price = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price = None

    return {
        "name": item.get("name") or item.get("title") or "",
        "price": price,
        "priceShow": item.get("priceShow") or item.get("originalPriceShow") or "",
        "inStock": infer_in_stock(item),
        "sold": item.get("itemSoldCntShow") or item.get("itemSoldCnt") or "",
        "url": item_url or None,
        "image": item.get("image"),
        "skuId": item.get("skuId") or item.get("itemId"),
        "sku": item.get("sku"),
        "sellerName": item.get("sellerName"),
        "sellerId": item.get("sellerId"),
    }


def extract_products(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    best: List[Dict[str, Any]] = []
    for items in candidate_item_lists(payload):
        normalized = [normalize_product(item) for item in items]
        # Prefer the largest product-looking collection and avoid nested SKU option lists.
        product_like = [
            p for p in normalized
            if p.get("name") and (p.get("url") or p.get("skuId") or p.get("sku"))
        ]
        if len(product_like) > len(best):
            best = product_like
    return best


def is_tcg_product(product: Dict[str, Any]) -> bool:
    haystack = normalized_text(product.get("name"))
    return any(keyword in haystack for keyword in keyword_list())


def product_key(product: Dict[str, Any]) -> str:
    for field in ("skuId", "sku", "url", "name"):
        value = product.get(field)
        if value not in (None, ""):
            return f"{field}:{value}"
    raise ValueError("Product has no stable identity")


def load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"initialized": False, "available": {}, "updated_at": None}
    except (ValueError, OSError) as exc:
        raise RuntimeError(f"Could not read state file {STATE_PATH}: {exc}") from exc


def save_state(available: Dict[str, Dict[str, Any]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "initialized": True,
        "available": available,
        "updated_at": timestamp(),
    }
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_PATH)


def main() -> int:
    url = os.getenv("SCRAPING_URL", "").strip()
    print(f"[{timestamp()}] Checking configured Lazada source")

    try:
        payload, body = fetch_source(url)
    except SourceBlocked as exc:
        print(f"[{timestamp()}] {exc}", file=sys.stderr)
        return 2
    except requests.RequestException as exc:
        print(f"[{timestamp()}] Request failed: {exc}", file=sys.stderr)
        return 3

    if payload is None:
        preview = body[:300].replace("\n", " ")
        print(f"[{timestamp()}] No parseable product payload. Preview: {preview}", file=sys.stderr)
        return 4

    products = extract_products(payload)
    if not products:
        print(
            f"[{timestamp()}] Parsed the source but found no recognizable products; preserving prior state.",
            file=sys.stderr,
        )
        return 5

    tcg_products = [product for product in products if is_tcg_product(product)]
    available = {
        product_key(product): product
        for product in tcg_products
        if product.get("inStock") is True
    }

    previous = load_state()
    previous_available = previous.get("available") or {}
    initialized = bool(previous.get("initialized"))

    if initialized:
        restocked_keys = sorted(set(available) - set(previous_available))
    else:
        restocked_keys = sorted(available) if ALERT_ON_FIRST_RUN else []

    restocked = [available[key] for key in restocked_keys]

    print(
        f"[{timestamp()}] Products={len(products)} TCG={len(tcg_products)} "
        f"available={len(available)} new_restocks={len(restocked)}"
    )

    if restocked:
        notifier = create_notification_service()
        if not notifier.notify_products(restocked):
            print(f"[{timestamp()}] Restock detected but notification failed; state not advanced.", file=sys.stderr)
            return 6
        print(f"[{timestamp()}] Sent restock alert for {len(restocked)} SKU(s)")
    elif not initialized:
        print(f"[{timestamp()}] First successful run: baseline recorded without alert")
    else:
        print(f"[{timestamp()}] No new restock transitions")

    save_state(available)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
