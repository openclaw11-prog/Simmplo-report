#!/usr/bin/env python3
"""
Simmpo Daily Report — v0.22
拉取指定日期的 Shopline 各地區營業額、Meta 廣告費、肖準（Looker Studio）、Google Ads（直接 API）。

Usage:
    python3 daily_report.py --date 2026-03-15
    python3 daily_report.py --date 2026-03-15 --tokens /path/to/simmpo_tokens.json
    python3 daily_report.py --date 2026-03-15 --fast   # 只跑 Meta，跳過 Shopline 翻頁（< 2s）
    python3 daily_report.py --date 2026-03-15 --agent-browser 'npx ...'  # 加入肖準資料
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

TZ_TPE = timezone(timedelta(hours=8))

# ── 預設 Token 路徑 ──────────────────────────────────────────────────────────
DEFAULT_TOKENS_PATH = "/Users/simmpo-claw/services/simmpo_tokens.json"

SHOPLINE_BASE = "https://open.shopline.io/v1"
META_GRAPH    = "https://graph.facebook.com/v19.0"

META_ACCOUNTS = [
    {"id": "act_1481816722260744", "name": "Simmpo 保護貼"},
    {"id": "act_882116043897323",  "name": "簡單貼 ez table"},
]

# 肖準行銷 — 資料來自 Looker Studio 報表（肖準使用獨立廣告帳號，不在我們的 Meta token 範圍內）
LOOKER_REPORT_URL = "https://lookerstudio.google.com/reporting/b46242ea-190d-47b3-94d7-ff2a7119ac76/page/p_bsqvr5te1d"

EXCLUDE_STATUSES = {"cancelled"}
REGIONS = ["TW", "HK", "MO", "MY"]

# Google Ads
GOOGLE_ADS_SIMMPO_CUSTOMER_ID = "1164087860"  # SIMMPO 主廣告帳號（MCC 子帳號）


# ── 工具函式 ─────────────────────────────────────────────────────────────────

def load_tokens(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def http_get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── Shopline ─────────────────────────────────────────────────────────────────

def fetch_shopline_daily(token: str, date: str) -> dict:
    """
    翻頁抓取指定日期（YYYY-MM-DD，台北時間）的有效訂單，依地區彙整 total 金額。
    已知限制：date filter 參數無效，改用逐頁比對 created_at 日期。
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Antigravity-Simmpo-Daily",
        "Accept": "application/json",
    }

    result = {r: {"count": 0, "total": 0.0} for r in REGIONS}
    result["OTHER"] = {"count": 0, "total": 0.0}

    # 從第一頁開始找到目標日期的起始頁（通常 3~4 天前約 page 10~15）
    # 用二分法也可，但資料量小直接從 page 1 往下找即可
    page = 1
    found_start = False

    while True:
        url = f"{SHOPLINE_BASE}/orders.json?page={page}&status=any"
        data = http_get(url, headers)
        items = data.get("items", [])

        if not items:
            break

        has_target = False
        passed_target = False

        for order in items:
            raw_dt = order.get("created_at", "")
            if raw_dt:
                order_date = datetime.fromisoformat(raw_dt).astimezone(TZ_TPE).strftime("%Y-%m-%d")
            else:
                order_date = ""

            if order_date == date:
                found_start = True
                has_target = True
                status = order.get("status", "")
                if status in EXCLUDE_STATUSES:
                    continue
                # 地區分類：跨境 7-11 門市取貨歸入 TW（對齊 Shopline 後台邏輯）
                # 其他訂單依收貨地址 country_code 分類
                order_delivery = order.get("order_delivery") or {}
                platform = (order_delivery.get("platform") or "").lower()
                if "cross_border" in platform and "store_pick_up" in platform:
                    key = "TW"
                else:
                    addr    = order.get("delivery_address") or {}
                    country = addr.get("country_code") or ""
                    key     = country if country in result else "OTHER"
                total = float((order.get("total") or {}).get("dollars", 0))
                result[key]["count"] += 1
                result[key]["total"] += total

            elif order_date < date:
                # 已超過目標日期，停止
                passed_target = True
                break

        if passed_target:
            break

        # 還沒找到目標日期，跳過這頁
        pagination = data.get("pagination", {})
        total_pages = pagination.get("total_pages", 1)
        if page >= total_pages:
            break

        page += 1

    return result


# ── Meta Ads ─────────────────────────────────────────────────────────────────

def fetch_meta_daily(token: str, date: str) -> list:
    """
    查詢各廣告帳號在指定日期的 spend。
    """
    rows = []
    time_range = urllib.parse.quote(json.dumps({"since": date, "until": date}))

    for acct in META_ACCOUNTS:
        url = (
            f"{META_GRAPH}/{acct['id']}/insights"
            f"?fields=account_name,spend,impressions,clicks"
            f"&time_range={time_range}"
            f"&access_token={token}"
        )
        data = http_get(url, {})
        insights = data.get("data", [])
        spend = float(insights[0]["spend"]) if insights else 0.0
        rows.append({
            "name":       acct["name"],
            "id":         acct["id"],
            "spend":      spend,
            "has_data":   bool(insights),
        })

    return rows


# ── FB廣告(肖準) — Looker Studio 日期範圍確保 ────────────────────────────────

# -- FB廣告(肖準) — Looker Studio 日期範圍確保 --

def _ensure_date_range(ab_run, dt) -> None:
    """
    確保 Looker Studio 報表顯示的日期範圍包含 dt 所在的整個月。
    v0.22: 委派給 xiaozhun.date_range_picker.DateRangePicker。
    """
    import re as _re, time as _time
    from xiaozhun.date_range_picker import DateRangePicker

    snap = ab_run("snapshot -i")

    # 快速檢查目前範圍是否已包含目標月份
    m = _re.search(r'(\d{4})年(\d{1,2})月\d{1,2}日\s*-\s*(\d{4})年(\d{1,2})月\d{1,2}日', snap)
    if m:
        start_ym = (int(m.group(1)), int(m.group(2)))
        end_ym   = (int(m.group(3)), int(m.group(4)))
        target_ym = (dt.year, dt.month)
        if start_ym <= target_ym <= end_ym:
            print(f"[ensure_date_range] 目前範圍已包含 {dt.year}/{dt.month}，跳過")
            return

    print(f"[ensure_date_range] 切換日期至 {dt.year}/{dt.month}")

    # 開啟日期選擇器
    btn_m = _re.search(r'button "getDateText\(\)" \[ref=(e\d+)\]', snap)
    if not btn_m:
        print("[ensure_date_range] 找不到日期選擇器 button，跳過")
        return
    ab_run(f'click {btn_m.group(1)}')
    _time.sleep(1.5)

    picker = DateRangePicker(ab_run)
    if picker.select_month_range(dt.year, dt.month):
        print(f"[ensure_date_range] 套用完成 {dt.year}/{dt.month}")
    else:
        print("[ensure_date_range] 日期切換失敗")
        ab_run("press Escape")



# ── FB廣告(肖準) — 從 Looker Studio 抓取 ────────────────────────────────────

def fetch_xiaozhun_daily(date: str, agent_browser: str = "") -> dict:
    """
    從 Looker Studio 報表抓取肖準行銷在指定日期的廣告費與購買轉換值。
    方法一（主要）：下載 CSV — 穩定、完整，不依賴 virtual scroll。
    方法二（備援）：scroll + parse DOM — 舊有邏輯，在 CSV 下載失敗時啟用。
    date 格式: YYYY-MM-DD
    """
    import subprocess, re, time, os, glob, csv as csv_module

    if not agent_browser:
        return {"spend": 0, "purchases": 0, "purchase_value": 0, "has_data": False,
                "error": "需指定 --agent-browser 路徑"}

    def ab_run(cmd: str) -> str:
        full = f"source ~/.zshrc && {agent_browser} {cmd}"
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=60,
                           executable="/bin/zsh")
        return r.stdout + r.stderr

    dt = datetime.strptime(date, "%Y-%m-%d")
    target = f"{dt.year}年{dt.month}月{dt.day}日"

    # ── 共用：開啟 Looker Studio 頁面 ────────────────────────────
    ab_run(f'open "{LOOKER_REPORT_URL}"')
    time.sleep(8)
    title = ab_run("eval 'document.title'")
    if "登入" in title or "Sign in" in title:
        ab_run("close")
        time.sleep(2)
        ab_run(f'--profile ~/agent-browser-profile open "{LOOKER_REPORT_URL}"')
        time.sleep(8)

    # ── 方法一：CSV 下載（主要，v0.19 改用 xiaozhun 模組）────────────────
    def try_csv_download() -> "dict | None":
        try:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from xiaozhun.menu_driver import open_chart_menu, select_export_data, click_export_button
            from xiaozhun.download_watcher import snapshot_csvs, wait_for_new_csv
            from xiaozhun.csv_parser import parse_looker_csv

            ab_run("set viewport 1600 2400")
            time.sleep(3)

            _ensure_date_range(ab_run, dt)
            time.sleep(5)  # 等頁面資料重新渲染

            dl_dir = os.path.expanduser("~/Downloads")
            before = snapshot_csvs(dl_dir)

            menu_snap = open_chart_menu(ab_run)
            if menu_snap is None:
                return None
            if not select_export_data(ab_run, menu_snap):
                return None
            time.sleep(1)
            if not click_export_button(ab_run):
                return None

            csv_path = wait_for_new_csv(before, dl_dir, timeout=30)
            if not csv_path:
                return None

            with open(csv_path, encoding="utf-8-sig") as _f:
                return parse_looker_csv(_f.read(), date)

        except Exception as _e:
            print(f"[try_csv_download] exception: {_e}")
            return None

    csv_result = try_csv_download()
    if csv_result is not None:
        ab_run("close")
        return csv_result

    # ── 方法二：scroll + parse DOM（備援）──────────────────────
    # 先捲動主容器讓每日明細表出現在 DOM
    ab_run('eval "(function(){ var mb = document.querySelector(\'.mainBlock\'); if(mb) mb.scrollTop = 2500; })()"')

    # 輪詢等待 centerColsContainer 出現（最多 30 秒）
    for _ in range(10):
        time.sleep(3)
        ready = ab_run('eval "(function(){ var cs=document.querySelectorAll(\'.centerColsContainer\'); for(var i=0;i<cs.length;i++){ if(cs[i].textContent.indexOf(\'年\')>-1) return \'ready\'; } return \'not-ready\'; })()"')
        if 'ready' in ready:
            break

    # 捲動到底部讓全月資料載入
    ab_run('eval "(function(){ var cs = document.querySelectorAll(\'.centerColsContainer\'); for(var i=0;i<cs.length;i++){ if(cs[i].textContent.indexOf(\'年\')>-1){ cs[i].scrollTop=9000; break; }} })()"')
    time.sleep(3)

    # 用 cell-by-cell 方式讀取目標日期的行
    js = (
        "(function(){"
        " var cs = document.querySelectorAll('.centerColsContainer');"
        " for(var i=0;i<cs.length;i++){"
        "  if(cs[i].textContent.indexOf('年')>-1 && cs[i].textContent.indexOf('月')>-1){"
        "   var rows=cs[i].querySelectorAll('.row');"
        "   for(var j=0;j<rows.length;j++){"
        f"    if(rows[j].textContent.indexOf('{target}')>-1){{"
        "     var cells=rows[j].querySelectorAll('.cell');"
        "     var out=[];"
        "     cells.forEach(function(c){out.push(c.textContent.trim())});"
        "     return out.join('|');"
        "  }}}}"
        " return 'not-found';"
        "})()"
    )
    output = ab_run(f'eval "{js}"')

    ab_run('close')

    # 解析 cell 資料
    # 欄位順序: Date|花費|曝光|觸及|點擊|CPC|CTR|加購|購買|CPA|購買轉換值|客單價|ROAS
    for line in output.split("\n"):
        if target not in line:
            continue
        cells = line.strip().strip('"').split("|")
        if len(cells) >= 13:
            def parse_num(s):
                return float(re.sub(r'[^\d.]', '', s) or '0')
            return {
                "spend": parse_num(cells[1]),
                "purchases": int(parse_num(cells[8])),
                "purchase_value": parse_num(cells[10]),
                "has_data": True,
            }

    return {"spend": 0, "purchases": 0, "purchase_value": 0, "has_data": False,
            "error": f"找不到 {target} 的資料"}


# ── Google Ads API（直接呼叫，不需 agent-browser）────────────────────────────

def fetch_google_ads_api(tokens: dict, date: str) -> dict:
    """
    透過 Google Ads API v20 直接拉取指定日期的廣告費與轉換價值。
    Developer token: _cRipdmI1...（注意第8位是大寫 I）
    """
    ga = tokens["google_ads"]

    # 取得 access token
    data = urllib.parse.urlencode({
        "client_id":     ga["client_id"],
        "client_secret": ga["client_secret"],
        "refresh_token": ga["refresh_token"],
        "grant_type":    "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as r:
        access_token = json.loads(r.read())["access_token"]

    mcc_id = ga["mcc_customer_id"].replace("-", "")
    headers = {
        "Authorization":    f"Bearer {access_token}",
        "developer-token":  ga["developer_token"],
        "login-customer-id": mcc_id,
        "Content-Type":     "application/json",
    }

    url = (f"https://googleads.googleapis.com/v20/customers/"
           f"{GOOGLE_ADS_SIMMPO_CUSTOMER_ID}/googleAds:search")
    query = (
        "SELECT metrics.cost_micros, metrics.conversions_value, metrics.conversions, segments.date "
        f"FROM customer WHERE segments.date = '{date}'"
    )
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    rows = result.get("results", [])
    if not rows:
        return {"spend": 0, "conv_value": 0, "conversions": 0, "has_data": False,
                "error": f"API 回傳無資料（日期：{date}）"}

    metrics = rows[0]["metrics"]
    spend      = int(metrics.get("costMicros", 0)) / 1_000_000
    conv_value = float(metrics.get("conversionsValue", 0))
    conversions = float(metrics.get("conversions", 0))
    return {"spend": spend, "conv_value": conv_value, "conversions": conversions, "has_data": True}


# ── Google Ads（via agent-browser，fallback 用）──────────────────────────────

GOOGLE_ADS_MCC_OCID = "6733387111"
GOOGLE_ADS_ACCOUNT_KEYWORD = "SIMMPO"

def fetch_google_ads_daily(date: str, agent_browser: str = "") -> dict:
    """
    透過 agent-browser 從 Google Ads 後台抓取指定日期的廣告費與轉換價值。
    使用 URL 日期參數（__r.TIMERANGE.*）直接導航，不需操作 date picker UI。
    需要 agent-browser 已登入 Google 帳號（使用 --profile 持久化 session）。
    """
    import subprocess, re

    if not agent_browser:
        return {"spend": 0, "conv_value": 0, "has_data": False,
                "error": "需指定 --agent-browser 路徑"}

    def ab_run(cmd: str) -> str:
        full = f"source ~/.zshrc && {agent_browser} {cmd}"
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=60,
                           executable="/bin/zsh")
        return r.stdout + r.stderr

    import time

    # 強制重啟 daemon with --profile 確保 Google session 有效
    ab_run("close")
    time.sleep(2)

    base_url = f"https://ads.google.com/aw/accounts?ocid={GOOGLE_ADS_MCC_OCID}"
    ab_run(f'--profile ~/agent-browser-profile open "{base_url}"')
    time.sleep(8)

    title = ab_run("eval 'document.title'")
    if "登入" in title or "Sign in" in title:
        return {"spend": 0, "conv_value": 0, "has_data": False,
                "error": "Google Ads session 無法建立，請手動重新登入"}

    # 用 date picker 設定日期（snapshot ref 方式，繞過 native setter 限制）
    import re as _re
    from datetime import datetime as _dt
    _d = _dt.strptime(date, "%Y-%m-%d")
    date_slash = f"{_d.year}/{_d.month}/{_d.day}"  # e.g. 2026/3/23

    # 1. snapshot 找「變更日期範圍」按鈕 ref
    snap1 = ab_run("snapshot")
    btn_ref = _re.search(r'button "變更日期範圍" \[ref=(e\d+)\]', snap1)
    if not btn_ref:
        return {"spend": 0, "conv_value": 0, "has_data": False,
                "error": "找不到「變更日期範圍」按鈕"}
    ab_run(f"click {btn_ref.group(1)}")
    time.sleep(2)

    # 2. snapshot 找日期 input refs 與套用按鈕
    snap2 = ab_run("snapshot")
    start_ref = _re.search(r'textbox "開始日期[^"]*" \[required, ref=(e\d+)\]', snap2)
    end_ref   = _re.search(r'textbox "結束日期[^"]*" \[required, ref=(e\d+)\]', snap2)
    apply_ref = _re.search(r'button "套用" \[ref=(e\d+)\]', snap2)

    if start_ref and end_ref and apply_ref:
        ab_run(f'fill {start_ref.group(1)} "{date_slash}"')
        ab_run(f'fill {end_ref.group(1)} "{date_slash}"')
        ab_run(f'click {apply_ref.group(1)}')
        # 等待頁面更新：輪詢 snapshot 確認日期已套用（最多 30 秒）
        month_zh = str(_d.month)
        day_zh = str(_d.day)
        for _ in range(10):
            time.sleep(3)
            snap3 = ab_run("snapshot")
            if f"{_d.year}年{month_zh}月{day_zh}日" in snap3 or f"自訂{_d.year}年{month_zh}月{day_zh}日" in snap3:
                break
    else:
        return {"spend": 0, "conv_value": 0, "has_data": False,
                "error": "找不到日期 picker refs，請確認 Google Ads UI 結構"}

    # 讀取帳戶表格中的數據
    js_extract = (
        "(function(){"
        " var rows=document.querySelectorAll('[role=row]');"
        " for(var i=0;i<rows.length;i++){"
        f"  if(rows[i].textContent.indexOf('{GOOGLE_ADS_ACCOUNT_KEYWORD}')>-1&&rows[i].textContent.indexOf('116-408')>-1){{"
        "   var cells=rows[i].querySelectorAll('[role=gridcell]');"
        "   var line=[];"
        "   cells.forEach(function(c){var t=c.textContent.trim();if(t)line.push(t);});"
        "   return line.join('|');"
        "  }}"
        " return 'not-found';"
        "})()"
    )
    output = ab_run(f'eval "{js_extract}"')

    # 解析數據
    # 欄位順序: 帳戶資訊 | 最佳化分數 | MCC | 管道 | 點擊 | 曝光 | 點閱率 | 平均CPC | 費用 | 轉換 | 轉換率 | 轉換價值
    for line in output.split("\n"):
        if GOOGLE_ADS_ACCOUNT_KEYWORD not in line:
            continue
        cells = line.strip().strip('"').split("|")
        if len(cells) >= 10:
            def parse_money(s):
                return float(re.sub(r'[^\d.]', '', s) or '0')
            # 費用在 index 8，轉換價值在 index 11
            spend = parse_money(cells[8]) if len(cells) > 8 else 0
            conv_value = parse_money(cells[11]) if len(cells) > 11 else 0
            return {
                "spend": spend,
                "conv_value": conv_value,
                "has_data": True,
            }

    return {"spend": 0, "conv_value": 0, "has_data": False,
            "error": "找不到帳戶數據"}


# ── 主程式 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simmpo 每日報表 v0.8")
    parser.add_argument("--date",   required=True, help="日期，格式 YYYY-MM-DD")
    parser.add_argument("--tokens", default=DEFAULT_TOKENS_PATH, help="simmpo_tokens.json 路徑")
    parser.add_argument("--fast",   action="store_true", help="只跑 Meta，跳過 Shopline 翻頁（用於測試 subagent 回傳）")
    parser.add_argument("--agent-browser", default="", help="agent-browser CLI 前綴（用於抓取肖準 Looker Studio 及 Google Ads 資料）")
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("錯誤：日期格式應為 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    tokens = load_tokens(args.tokens)

    print(f"\n{'='*50}")
    print(f"  Simmpo 每日報表  {args.date}  (v0.22)")
    print(f"{'='*50}\n")

    # Shopline
    print("📦 Shopline 營業額（排除 cancelled）")
    shopline_token = tokens["shopline"]["access_token"]
    shopline = fetch_shopline_daily(shopline_token, args.date)
    for region in REGIONS:
        d = shopline[region]
        print(f"  {region}: {d['count']} 筆  NT$ {d['total']:,.0f}")
    if shopline["OTHER"]["count"] > 0:
        d = shopline["OTHER"]
        print(f"  OTHER: {d['count']} 筆  NT$ {d['total']:,.0f}")
    total_revenue = sum(shopline[r]["total"] for r in REGIONS)
    print(f"  {'─'*30}")
    print(f"  合計: NT$ {total_revenue:,.0f}\n")

    # Meta
    print("📣 Meta 廣告費")
    meta_token = tokens["meta"]["access_token"]
    meta_rows  = fetch_meta_daily(meta_token, args.date)
    total_spend = 0.0
    for row in meta_rows:
        spend = row["spend"]
        total_spend += spend
        tag = f"NT$ {spend:,.0f}" if row["has_data"] else "（無投放）"
        print(f"  {row['name']}: {tag}")
    print(f"  {'─'*30}")
    print(f"  合計廣告費: NT$ {total_spend:,.0f}\n")

    # FB廣告(肖準)
    print("🎯 FB廣告(肖準)")
    ab = getattr(args, 'agent_browser', '')
    if ab:
        xz = fetch_xiaozhun_daily(args.date, ab)
        if xz["has_data"]:
            print(f"  廣告費:  NT$ {xz['spend']:,.0f}")
            print(f"  營業額:  NT$ {xz['purchase_value']:,.0f}")
            print(f"  購買數:  {xz['purchases']} 筆")
            if xz["spend"] > 0:
                print(f"  ROAS:    {xz['purchase_value'] / xz['spend']:.2f}")
        else:
            err = xz.get("error", "")
            print(f"  ⚠️  無法取得資料{f'（{err}）' if err else ''}")
    else:
        print("  ⚠️  需指定 --agent-browser 參數（從 Looker Studio 抓取）")
    print()

    # Google Ads（優先 API，失敗才 fallback agent-browser）
    print("🔍 Google Ads")
    gads = None
    try:
        gads = fetch_google_ads_api(tokens, args.date)
    except Exception as e:
        print(f"  ⚠️  API 失敗：{e}，嘗試 agent-browser fallback...")
        if ab:
            gads = fetch_google_ads_daily(args.date, ab)

    if gads and gads["has_data"]:
        print(f"  廣告費:    NT$ {gads['spend']:,.0f}")
        print(f"  轉換價值:  NT$ {gads['conv_value']:,.0f}")
        if gads["spend"] > 0:
            print(f"  ROAS:      {gads['conv_value'] / gads['spend']:.2f}")
    else:
        err = (gads or {}).get("error", "")
        print(f"  ⚠️  無法取得資料{f'（{err}）' if err else ''}")
    print()

    print("="*50)


if __name__ == "__main__":
    main()
