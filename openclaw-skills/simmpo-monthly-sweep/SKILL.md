---
name: simmpo-monthly-sweep
version: 0.3
description: 掃描 Simmpo 指定月份所有日期的報表資料（Shopline / Meta / Google Ads / 肖準），並以電商營運報表格式寫入 Google Sheets（每月一個新 tab）。
---

# Simmpo Monthly Sweep Skill

> **v0.3**
> Sheet 改為電商營運報表格式：一列＝一渠道、一欄組＝一日期（轉置）。
> Meta act_1481816722260744 廣告費放在「官網（台灣）金額未稅」列；act_882116043897323 不使用。
> 新增 `parse_looker_csv_all`（整月一次解析）。

## 功能

- **Shopline**：單次翻頁抓整月訂單，按日期/地區彙整，跨境 7-11 取貨歸入 TW
- **Meta 廣告費**：`time_increment=1` 一次拉整月每日 spend（僅 act_1481816722260744）
- **Google Ads**：`segments.date BETWEEN` 一次拉整月每日費用/轉換值
- **肖準（Looker Studio）**：開一次 browser、切換整月日期範圍、下載 CSV、`parse_looker_csv_all` 解析所有列
- **Google Sheets**：新增 tab（`YYYY-MM`），轉置格式 + 顏色格式化

## Spreadsheet

**固定 ID**：`1fNw7BYrVZ6UCzcUOJanbkU5m5FAYzpQ1DwdherjsOOY`
（已設為預設值，可省略 `--spreadsheet`）

## 使用方式

### 完整版（含肖準）

```bash
export PATH="$HOME/local/bin:$PATH"
python3 ~/services/monthly_sweep.py \
  --month 2026-03 \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser' \
  --overwrite
```

### 快速版（跳過肖準，肖準欄填「待補」）

```bash
python3 ~/services/monthly_sweep.py \
  --month 2026-03 \
  --tokens ~/services/simmpo_tokens.json \
  --overwrite
```

## CLI Flags

| Flag | 說明 | 預設 |
|------|------|------|
| `--month` | 查詢月份（YYYY-MM） | 與 `--date` 二選一 |
| `--date` | 單日補列模式（YYYY-MM-DD） | 與 `--month` 二選一 |
| `--spreadsheet` | Google Spreadsheet ID | `1fNw7BYrVZ6UCzcUOJanbkU5m5FAYzpQ1DwdherjsOOY` |
| `--tokens` | simmpo_tokens.json 路徑 | `~/services/simmpo_tokens.json` |
| `--agent-browser` | agent-browser CLI 前綴 | 選填，沒有則跳過肖準 |
| `--overwrite` | tab 已存在時先刪除再重建（`--month` 模式） | 選填 |

## 檔案位置

| 項目 | 路徑 |
|------|------|
| 主腳本 | `~/services/monthly_sweep.py` |
| xiaozhun 模組 | `~/services/xiaozhun/` |
| csv_parser（含 parse_looker_csv_all）| `~/services/xiaozhun/csv_parser.py` |

## Sheet 格式（電商營運報表）

**欄配置**：A（空）| B（類別）| C（渠道）| D,E（日1 營業額,廣告費）| F,G（日2）...

**列配置**：

| 列 | 類別 | 渠道 | 營業額 | 廣告費 |
|----|------|------|--------|--------|
| 3 | 官網 | 官網（台灣）金額未稅 | Shopline TW ÷ 1.05 | Meta act_1481816722260744 |
| 4 | 官網 | 官網（台灣）含稅 | Shopline TW total | — |
| 5 | 官網 | 官網（香港） | Shopline HK | — |
| 6 | 官網 | 官網（澳門） | Shopline MO | — |
| 7 | 官網 | 官網（馬來） | Shopline MY | — |
| 8 | Google Ads | Google Ads | GA conversionsValue | GA spend |
| 9 | FB廣告 | FB廣告（域動） | — | — （手動填）|
| 10 | FB廣告 | FB廣告（肖準）實際投放 | xz purchase_value | xz spend |
| 11 | FB廣告 | FB廣告（肖準）10% 服務費 | — | xz spend × 10% |

**顏色**：官網（藍 #CFE2F3）、Google Ads（深綠 #1E4D2B）、FB廣告（深藍 #1F3864）

## 執行邏輯

### Phase 1 — 純 API（< 1 分鐘）

```
Shopline   → 翻頁至月初，跨境 7-11 取貨歸 TW
Meta       → single call，time_increment=1
Google Ads → single call，segments.date BETWEEN 月初-月末
```

### Phase 2 — 肖準（2-3 分鐘，需 browser）

```
open Looker Studio（--profile ~/agent-browser-profile 確保 session）
→ DateRangePicker.select_month_range(year, month)
→ open_chart_menu + select_export_data + click_export_button
→ wait_for_new_csv（snapshot diff）
→ parse_looker_csv_all → {date: {spend, purchase_value, purchases}}
close browser
```

### Phase 3 — 寫入 Sheets

```
gws spreadsheets batchUpdate → deleteSheet（--overwrite 時）→ addSheet
gws spreadsheets values update → 一次寫入全部 grid
gws spreadsheets batchUpdate → mergeCells（日期 header + B 欄類別）+ 顏色 + 數字格式
```

## 肖準資料缺失處理

- browser 未執行 或 CSV 中找不到該日期 → 填 `待補`
- CSV 有該日期但值為 0 → 填 `0`

## 已知限制／注意事項

- Shopline date filter 無效，翻頁方式較慢（約 1 分鐘）
- 肖準資料最晚隔天中午同步，補填時加 `--overwrite` 重跑
- agent-browser `open` 指令偶爾 timeout（60s）→ 先 `pkill -f "Google Chrome for Testing"` 重啟 daemon
- HK/MO/MY 營業額為原始幣別（HKD/MOP/MYR），尚未換算 NTD
- Meta act_882116043897323（簡單貼 ez table）不列入報表

## 給 OpenClaw 的執行指示

```
請執行以下指令，並將腳本的原始輸出完整回傳：

export PATH="$HOME/local/bin:$PATH" && python3 ~/services/monthly_sweep.py \
  --month 2026-03 \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser' \
  --overwrite 2>&1
```
