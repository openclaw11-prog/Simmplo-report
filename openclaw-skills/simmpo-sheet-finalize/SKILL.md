---
name: simmpo-sheet-finalize
version: 2.0
description: 將 Simmpo 每日報表數據填入 Google Sheets「投廣告效益報表」。需先有當日報表數據。用法：/simmpo-sheet-finalize 2026-04-01 --tw 165419 --hk 11304 --meta 94626 --gads-rev 28128 --gads-spend 4712
user-invocable: true
allowed-tools:
  - Bash(python3 *)
  - Bash(export *)
  - Bash(gws *)
---

將 Simmpo 每日報表數據寫入 Google Sheets。

目標試算表 ID：`1fNw7BYrVZ6UCzcUOJanbkU5m5FAYzpQ1DwdherjsOOY`

從參數解析日期與各數值，執行：
```bash
export PATH="$HOME/local/bin:$PATH" && python3 ~/.openclaw/skills/simmpo-sheet-finalize/scripts/finalize_to_sheets.py \
  --date <DATE> \
  --tw-revenue <TW> \
  --hk-revenue <HK> \
  --mo-revenue <MO> \
  --meta-spend <META> \
  --gads-revenue <GADS_REV> \
  --gads-spend <GADS_SPEND> \
  [--xz-revenue <XZ_REV> --xz-spend <XZ_SPEND>] 2>&1
```

## 核心行為

### 目標 Tab
- 依日期自動選月份 tab（例如 `2026-04`）
- Tab 不存在時自動建立並寫入 row labels（A–C 欄結構）

### Row Mapping（動態偵測）
- 腳本讀取 col C 的 labels 自動找對應 row，不硬編碼
- 找不到 label 時使用 fallback 預設值：

| 項目 | col C label | rev 欄 | ads 欄 |
|------|------------|--------|--------|
| 官網（台灣）未稅 | 官網（台灣）金額未稅 | TW total ÷ 1.05 | Meta spend |
| 官網（台灣）含稅 | 官網（台灣）含稅 | TW total | — |
| 官網（香港）| 官網（香港）| HK total | — |
| 官網（澳門）| 官網（澳門）| MO total | — |
| Google Ads | Google Ads | 轉換值 | 花費 |
| FB廣告（域動）| FB廣告（域動）| 0 | 0 |
| FB廣告（肖準）| FB廣告（肖準）實際投放 | 肖準轉換值 | 肖準廣告費 |

### 非破壞寫入
- 寫入前讀取 row 1，若該日期已存在 → **不覆寫**，在右側新增 update 欄位對（+2 跳過原 rev+ads pair）
- 新欄位 row 1 header 格式：`4/8 (updated 08:39 CST)`
- row 1 新欄位自動跨欄合併（rev+ads 兩欄合為一格），與原始格式一致
- row 2 自動補上「營業額 / 廣告費」labels
- 第一次寫入（row 1 找不到日期）→ 新增 `4/8` header 並寫入

> ⚠️ **已知行為：Sheets API 尾端空格截斷問題**
> Google Sheets API 回傳 row 1 時，尾端空格欄會被自動截掉。
> 每個日期佔 2 欄（rev + ads），最後一個日期的 ads 欄（col 2）在 row 1 為空，不會出現在 API 回應中。
> 因此計算下一個可用欄位時必須用 `len(row) + 2`，而非 `len(row) + 1`。
> 若用 `+1` 會寫入最後日期的 ads 欄，破壞該日廣告費數據。（2026-04-10 曾發生此問題）

### cron_log Tab
每次執行（無論成功或失敗）都 append 一行至 `cron_log` tab：

| 欄位 | 內容 |
|------|------|
| A | 執行時間戳（台灣時間） |
| B | 報表日期 |
| C | 狀態：`SUCCESS` / `UPDATE` / `FAILED` / `UPDATE→FAILED` |
| D | 數據摘要 + 原值（如有） |

### 抓取失敗處理
傳入 `--failed` 時，所有欄位填入字串 `failed`：
```bash
python3 ~/.openclaw/skills/simmpo-sheet-finalize/scripts/finalize_to_sheets.py --date <DATE> --failed 2>&1
```

## 前置條件

`gws auth status` 需顯示 `token_valid: true`。若未登入執行 `gws auth login`。

詳細文件：`~/.openclaw/skills/simmpo-sheet-finalize/SKILL.md`
