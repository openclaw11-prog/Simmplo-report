---
name: simmpo-sheet-finalize
description: 將 Simmpo 每日報表數據填入 Google Sheets「投廣告效益報表」。需先有當日報表數據。用法：/simmpo-sheet-finalize 2026-04-01 --tw 165419 --hk 11304 --meta 94626 --gads-rev 28128 --gads-spend 4712 [--sg 1583]
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
  [--sg-revenue <SG>] \
  --meta-spend <META> \
  --gads-revenue <GADS_REV> \
  --gads-spend <GADS_SPEND> \
  [--xz-revenue <XZ_REV> --xz-spend <XZ_SPEND>] \
  [--manual] 2>&1
```

**`--manual` 參數**：手動補跑時加上，會將執行紀錄寫入 `~/services/simmpo_auto_report.log` 並標註「手動補跑」。cronjob 自動執行時不需加。

## 試算表填寫對應

| 項目 | 行號 | 說明 |
|------|------|------|
| 官網 TW 未稅 | Row 3 | TW total ÷ 1.05，廣告費欄填 Meta spend |
| 官網 TW 含稅 | Row 4 | TW total |
| 官網 HK | Row 5 | HK total |
| 官網 MO | Row 6 | MO total |
| 官網 SG | Row 8 | SG total（新加坡，選填）|
| Google Ads | Row 9 | 轉換值 / 花費 |
| FB廣告（域動）| Row 21 | 填 0 |
| FB廣告（肖準）| Row 23 | 肖準資料（無則填 0） |

## 前置條件

`gws auth status` 需顯示 `token_valid: true`。若未登入執行 `gws auth login`。

詳細文件：`~/.openclaw/skills/simmpo-sheet-finalize/SKILL.md`
