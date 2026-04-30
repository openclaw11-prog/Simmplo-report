#!/usr/bin/env python3
"""
Simmpo 葉黃素銷售報表

抓取指定日期的葉黃素相關訂單，計算：
1. 葉黃素銷售總金額（含加購、定檔、正常購買）
2. 含葉黃素訂單的定檔總金額

用法：
    python3 bh_report.py --date 2026-04-03
    python3 bh_report.py --date 2026-04-03 --tokens ~/services/simmpo_tokens.json
"""

import argparse
import json
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

TZ_TPE = timezone(timedelta(hours=8))
SHOPLINE_BASE = "https://open.shopline.io/v1"
DEFAULT_TOKENS = "/Users/simmpo-claw/services/simmpo_tokens.json"

# ── 葉黃素商品識別規則 ────────────────────────────────────────────────────────
# 正常購買：SKU 以 BH 開頭（BH0100=1盒, BH0104=10盒...）
BH_SKU_PREFIX = "BH"

# 加購版本：Shopline 加購促銷商品是獨立 item_id，沒有 SKU
# item_type=AddonProduct，靠 item_id 識別
# 如有新加購品項出現，在此新增
BH_ADDON_ITEM_IDS = {
    "681da95ea88cb008fc0c3c27",  # 葉黃素加購1盒 NT$480（2026-04 發現）
}

# ── Shopline API ──────────────────────────────────────────────────────────────

def fetch_orders_for_date(token: str, date: str) -> list:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Antigravity-Simmpo-Daily",
    }
    found, page = [], 1
    while True:
        url = f"{SHOPLINE_BASE}/orders.json?page={page}&status=any"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=_SSL_CTX) as r:
            data = json.loads(r.read())
        items = data.get("items", [])
        if not items:
            break
        passed = False
        for order in items:
            raw_dt = order.get("created_at", "")
            odate = datetime.fromisoformat(raw_dt).astimezone(TZ_TPE).strftime("%Y-%m-%d") if raw_dt else ""
            if odate == date:
                found.append(order)
            elif odate < date:
                passed = True
                break
        if passed:
            break
        page += 1
    return found


def is_bh_item(si: dict) -> bool:
    """判斷一個 subtotal_item 是否為葉黃素商品"""
    itype = si.get("item_type", "")
    # 正常購買：SKU 以 BH 開頭
    if itype == "Product":
        vd = (si.get("item_data") or {}).get("variation_data") or {}
        sku = vd.get("sku", "")
        if sku.startswith(BH_SKU_PREFIX):
            return True
    # 加購版：靠 item_id 識別
    if itype == "AddonProduct":
        if si.get("item_id", "") in BH_ADDON_ITEM_IDS:
            return True
    return False


def is_buy_one_get_one(si: dict) -> bool:
    """判斷是否為買一送一活動商品（title 含「買一送一」）"""
    title = ""
    for v in (si.get("title_translations") or {}).values():
        if "買一送一" in (v or ""):
            return True
    return False


def get_item_price(si: dict) -> float:
    """取商品的實際成交金額（item_price × 計費數量）
    買一送一：只計一半數量（送的那盒不計）
    """
    itype = si.get("item_type", "")
    qty = si.get("quantity", 1) or 1
    if itype == "AddonProduct":
        return float((si.get("item_price") or {}).get("dollars", 0)) * qty
    # 買一送一：只算付費的盒數
    if is_buy_one_get_one(si):
        qty = qty // 2
    # 用 item_price（商品定價）× 數量
    return float((si.get("item_price") or {}).get("dollars", 0)) * qty


def get_sku_label(si: dict) -> str:
    itype = si.get("item_type", "")
    if itype == "Product":
        vd = (si.get("item_data") or {}).get("variation_data") or {}
        return vd.get("sku", "")
    if itype == "AddonProduct":
        return f"加購({si.get('item_id','')})"
    return itype


# ── 主邏輯 ────────────────────────────────────────────────────────────────────

def run(date: str, tokens_path: str):
    with open(tokens_path) as f:
        tokens = json.load(f)
    token = tokens["shopline"]["access_token"]

    orders = fetch_orders_for_date(token, date)
    print(f"日期: {date}  總訂單數: {len(orders)}")
    print("=" * 50)

    bh_revenue = 0.0        # 葉黃素品項金額加總
    bh_order_count = 0      # 含葉黃素的訂單數
    bh_order_total = 0.0    # 含葉黃素訂單的整張 total 加總
    details = []

    EXCLUDE = {"cancelled"}

    for order in orders:
        status = order.get("status", "")
        if status in EXCLUDE:
            continue

        bh_items = [si for si in (order.get("subtotal_items") or []) if is_bh_item(si)]
        if not bh_items:
            continue

        order_total = float((order.get("total") or {}).get("dollars", 0))
        bh_amount = sum(get_item_price(si) for si in bh_items)
        qty_total = sum(si.get("quantity", 1) or 1 for si in bh_items)

        bh_order_count += 1
        bh_revenue += bh_amount
        bh_order_total += order_total

        detail_skus = ", ".join(
            f"{get_sku_label(si)} x{si.get('quantity',1)} @{get_item_price(si):.0f}"
            for si in bh_items
        )
        details.append(
            f"  {order['order_number']}  訂單total={order_total:.0f}  葉黃素={bh_amount:.0f}  [{detail_skus}]"
        )

    print(f"含葉黃素訂單數:       {bh_order_count}")
    print(f"葉黃素銷售總金額:     NT$ {bh_revenue:,.0f}")
    print(f"含葉黃素訂單定檔金額: NT$ {bh_order_total:,.0f}")
    print()
    print("訂單明細:")
    for d in details:
        print(d)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--tokens", default=DEFAULT_TOKENS)
    args = parser.parse_args()
    run(args.date, args.tokens)
