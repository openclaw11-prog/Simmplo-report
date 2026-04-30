---
name: simmpo-daily-report
version: 0.8
description: 拉取 Simmpo 指定日期的每日報表，包含 Shopline 各地區營業額、Meta 廣告費、肖準行銷 FB 廣告（Looker Studio CSV 下載，xiaozhun 模組）、Google Ads（直接 API），並可用 unified-renderer 渲染為 PNG 報表圖。
---

# Simmpo Daily Report Skill

> **v0.8**
> `_ensure_date_range` 改為委派給 `xiaozhun.date_range_picker.DateRangePicker`（TDD + SOLID 重構）。
> `menu_driver` 掃描範圍擴大至 y=400-1800、context 視窗由 5→15 行，修正跨月切換後找不到圖表的問題。
> 已驗證：2026-02-01、2026-03-01、2026-04-01 三個月份首日全部成功。

## 功能

- **Shopline 營業額**：依地區（TW/HK/MO/MY/SG）彙整指定日期的訂單金額，排除 `cancelled` 訂單
- **Meta 廣告費**：查兩個廣告帳號當日 spend
  - `act_1481816722260744`（Simmpo 保護貼）
  - `act_882116043897323`（簡單貼 ez table）
- **FB廣告（肖準）**：從 Looker Studio 報表抓取廣告費、購買轉換值（需 agent-browser）
- **Google Ads**：直接呼叫 Google Ads API v20，不需 agent-browser
  - MCC: `534-306-7958`，SIMMPO 子帳號: `1164087860`

## 使用方式

### 標準執行（在 simmpo-claw 上）

```bash
python3 ~/services/daily_report.py \
  --date 2026-03-30 \
  --tokens ~/services/simmpo_tokens.json
```

### 含肖準（需 agent-browser）

```bash
export PATH="$HOME/local/bin:$PATH"
python3 ~/services/daily_report.py \
  --date 2026-03-30 \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser'
```

## 檔案位置

| 項目 | 路徑 |
|------|------|
| 主腳本（simmpo-claw）| `~/services/daily_report.py` |
| xiaozhun 模組（simmpo-claw）| `~/services/xiaozhun/` |
| Token（simmpo-claw）| `~/services/simmpo_tokens.json` |
| agent-browser（simmpo-claw）| `npx agent-browser`（需 `PATH=$HOME/local/bin:$PATH`）|
| agent-browser profile | `~/agent-browser-profile`（保有 Google 登入 session）|
| 腳本備份（本機）| `skills-align/master/simmpo-daily-report/scripts/daily_report.py` |

## CLI Flags

| Flag | 說明 | 預設 |
|------|------|------|
| `--date` | 查詢日期（YYYY-MM-DD） | 必填 |
| `--tokens` | simmpo_tokens.json 路徑 | 必填 |
| `--agent-browser` | agent-browser CLI 前綴 | 選填，沒有則跳過肖準 |
| `--fast` | 只跑 Meta，跳過 Shopline 翻頁 | 選填 |

## 測試

```bash
# simmpo-claw 上執行
source /opt/homebrew/opt/api-dev-venv/bin/activate

# 單元測試（快速，不需 browser）
python3 -m pytest ~/services/xiaozhun/tests/ -m 'not slow' -q

# 整合測試（需真實 browser + Google session）
python3 -m pytest ~/services/xiaozhun/tests/ -m slow -v -s
```

## xiaozhun 模組架構

肖準 Looker Studio 抓取拆為 6 個責任模組：

| 模組 | 責任 |
|------|------|
| `date_range_picker.py` | Looker Studio 日期選擇器：跨月切換、左右 pane 獨立導航、Apply 重試 |
| `menu_driver.py` | browser 互動：hover 掃描 + 雙重驗證開 chart menu、點匯出 |
| `csv_parser.py` | CSV 解析：`parse_looker_csv`（單日）/ `parse_looker_csv_all`（整月，monthly_sweep 用）|
| `chart_locator.py` | snapshot 評分：找「廣告成效總預覽」chart container |
| `date_utils.py` | 日期正規化：支援 5 種格式 → YYYY-MM-DD |
| `download_watcher.py` | 偵測新下載：snapshot diff，不依賴固定檔名 |

### date_range_picker 關鍵設計

```
select_month_range(year, month):
  1. nav 左 pane → 目標月份
  2. click 左 pane day 1（設 start date）
  3. nav 右 pane → 目標月份
  4. click 右 pane last day（設 end date）
  5. apply（最多重試 4 次，跳過 disabled 狀態）
```

### menu_driver 關鍵設計

```
hover y=400..1800（步距 50）
  → 找 button "顯示圖表選單"
  → 確認前 15 行有「廣告成效總預覽」  ← 雙重驗證，避免點到錯圖表
  → click → 確認 menu 有「匯出」選項
  → select_export_data → click_export_button
  → wait_for_new_csv（snapshot diff）
  → parse_looker_csv
```

已驗證：
- 2026-02-01 ✅（廣告費 NT$3,414 / 營業額 NT$52,922 / 購買 39筆）
- 2026-03-01 ✅（廣告費 NT$3,314 / 營業額 NT$13,683 / 購買 6筆）
- 2026-04-01 ✅（廣告費 NT$0 / 營業額 NT$2,451 / 購買 2筆）
- 三月第一週 7/7 ✅
- 三月最後一週 7/7 ✅

## 重要實作細節

### agent-browser session 管理
- Looker Studio 函數若 session 失效（title 含「登入」）會自動重啟 daemon with profile
- Google Ads 函數開頭會強制 `close` 再用 `--profile ~/agent-browser-profile` 重啟

### Google Ads Developer Token（已解決）
- Developer Token：`_cRipdmI1...`（注意第8位是**大寫 I**，不是小寫 l 或 1）
- API 正常運作，直接呼叫，**不需 agent-browser**

### Shopline
- date filter 參數（`created_at_min/max`）無效，腳本改用逐頁翻找比對日期
- 跨境 7-11 取貨訂單（HK 地址 + TWD 幣別）依 `order_delivery.platform` 歸入 TW（v0.16+）

### subprocess shell
- 所有 `ab_run()` 呼叫都加 `source ~/.zshrc &&` 前綴，並指定 `executable="/bin/zsh"`

## 給 OpenClaw 的執行指示

```
請執行以下指令，並將腳本的原始輸出完整回傳（不要重新計算或改寫數字）：

export PATH="$HOME/local/bin:$PATH" && python3 ~/services/daily_report.py \
  --date 2026-03-23 \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser' 2>&1
```

> **注意**：`npx agent-browser` 需要 `~/local/bin` 在 PATH 中，必須明確加上 `export PATH="$HOME/local/bin:$PATH"`。

### 若用 OpenCode 執行（9B 模型）

**工作目錄必須設為 `/private/tmp`**，不可用 `~/services`：

```bash
ssh simmpo-claw "nohup bash -c 'source ~/.zshrc && cd /private/tmp && ~/.opencode/bin/opencode run --model omlx/Qwen3.5-9B-8bit \"[prompt]\"' > /tmp/opencode_9b_output.txt 2>&1 &"
```

## 資料延遲說明

| 資料來源 | 延遲狀況 |
|----------|----------|
| Shopline 訂單 | 即時，當天可查 |
| Meta 廣告費 | 即時，當天可查 |
| Google Ads | 即時，當天可查 |
| 肖準（Looker Studio）| **更新時間不穩定**，有時當天晚上就有，有時要到隔天中午才同步 |

**處理方式**：若肖準出現「找不到資料」，屬正常現象，非腳本錯誤。需在報表中**注記「肖準資料待補」**，中午 12:00 後重新執行補齊。

## 報表 PNG 輸出（unified-renderer）

抓到資料後，用 `unified-renderer` skill 的 `report` 模式輸出品牌風格 PNG。

### Markdown 內容格式（`<style>` + `<table>`）

```html
<style>
.rpt { width:100%; border-collapse:collapse; font-size:13px; }
.rpt th, .rpt td { border:1.5px solid #0a0a0a; padding:6px 10px; text-align:right; }
.rpt th { background:#0a0a0a; color:#fff; font-weight:700; text-align:center; }
.rpt td:first-child { text-align:left; font-weight:600; }
.rpt .date-hd { background:#1a1a2e; color:#00E6FF; font-size:14px; font-weight:800; }
.rpt .sub-hd  { background:#2d2d2d; color:#ddd; font-size:12px; }
.rpt .row-tw  { background:#e8f4e8; }
.rpt .row-ga  { background:#1a472a; color:#fff; }
.rpt .row-ga td:first-child { color:#fff; }
.rpt .row-xz  { background:#fff3e0; }
.rpt .row-nd  { background:#f5f5f5; color:#aaa; }
.rpt .na      { color:#bbb; text-align:center !important; }
.rpt .pending { color:#e67e22; font-style:italic; text-align:center !important; font-size:11px; }
</style>

<table class="rpt">
  <thead>
    <tr>
      <th rowspan="2" style="text-align:left">渠道</th>
      <th colspan="2" class="date-hd">3/23（週日）</th>
    </tr>
    <tr>
      <th class="sub-hd">營業額</th><th class="sub-hd">廣告費</th>
    </tr>
  </thead>
  <tbody>
    <tr class="row-tw"><td>官網（台灣）</td><td>166,176</td><td>75,825</td></tr>
    <tr class="row-tw"><td>官網（香港）</td><td>8,963</td><td class="na">—</td></tr>
    <tr class="row-tw"><td>官網（澳門）</td><td class="na">—</td><td class="na">—</td></tr>
    <tr class="row-tw"><td>官網（馬來）</td><td class="na">—</td><td class="na">—</td></tr>
    <tr class="row-ga"><td>Google Ads</td><td>29,443</td><td>5,285</td></tr>
    <tr class="row-xz"><td>FB廣告（肖準）</td><td>48,031</td><td>12,824</td></tr>
    <tr class="row-nd"><td>FB廣告（域動）</td><td class="pending">待接入</td><td class="pending">待接入</td></tr>
  </tbody>
</table>
```

### 渲染指令

```bash
cd .agent/skills/unified-renderer
go run scripts/render.go \
  -mode report \
  -md simmpo_data.md \
  -title "Simmpo 每日報表" \
  -subtitle "2026-03-23" \
  -brand "Simmpo" \
  -footer "Generated YYYY-MM-DD  by Castle Studio" \
  -out simmpo_report.png
```

### 渠道資料對應

| 渠道 | 資料來源 | 備註 |
|------|----------|------|
| 官網 TW 營業額（未稅）| Shopline TW total ÷ 1.05 | 跨境 7-11 取貨訂單歸入 TW |
| 官網 TW 營業額（含稅）| Shopline TW total | — |
| 官網 TW 廣告費 | Meta act_1481816722260744 | 僅台灣官網投放，報表放於未稅列 |
| 官網 HK/MO/MY 營業額 | Shopline HK/MO/MY | 按收貨地址分類；原始幣別（HKD/MOP/MYR），未換算 NTD |
| Google Ads | Google Ads API 直接呼叫 | 轉換值有事後歸因調整 ±5% |
| FB廣告（肖準）| Looker Studio（agent-browser）| 小數捨入差 ≤18 元屬正常 |
| FB廣告（域動）| 尚未接入 | 需手動補充 |
| Meta act_882116043897323（簡單貼 ez table）| 不列入報表 | — |

## 自動排程（cron）

`~/services/simmpo_auto_report.sh` 每天跑兩輪：

| 時間 | 參數 | 說明 |
|------|------|------|
| 02:00 | `first` | 抓昨日數據、寫入 Sheets，在 log 寫 `FIRST_ROUND_DATA: TW=... HK=...` |
| 08:00 | `check` | 重抓數據，與 first 比對；一致寫 `CHECK_RESULT: OK`；有差異寫 `CHECK_RESULT: MISMATCH TW: 舊→新, HK: 舊→新 ...` 並以 8am 數字更新 Sheets |

**設計原因**：Shopline 午夜前（尤其 HK）可能還有訂單進來，2am 跑完後有機會漏掉，8am 補跑確保數字準確。

## 已知狀態

- Google Ads API：✅ 2026-04-01 起正常（developer token 字元修正）
- 肖準 Looker Studio：✅ 穩定（DateRangePicker 跨月切換，2/1、3/1、4/1 驗證通過）
- Shopline date filter 參數無效，腳本改用逐頁翻找
- SG（新加坡）地區：✅ 2026-04-08 起新增支援，不再歸入 OTHER
