---
name: simmpo-bh-report
description: 抓取 Simmpo 官網指定日期的葉黃素（BH系列）銷售數據。輸出葉黃素銷售總金額與含葉黃素訂單的定檔總金額。用法：/simmpo-bh-report 2026-04-03
user-invocable: true
allowed-tools:
  - Bash(python3 *)
---

執行 Simmpo 葉黃素銷售報表。

從參數取得日期（格式 YYYY-MM-DD）。若無日期參數，使用昨天的台北時間日期。

執行指令：
```bash
python3 ~/.openclaw/skills/simmpo-bh-report/scripts/bh_report.py \
  --date <DATE> \
  --tokens ~/services/simmpo_tokens.json 2>&1
```

將腳本原始輸出完整回傳，不要重新計算或改寫數字。

## 葉黃素識別規則（重要）

- 正常購買：`item_type=Product`，SKU 前綴 `BH`（BH0100=1盒 NT$1180, BH0104=10盒 NT$5800）
- 加購促銷：`item_type=AddonProduct`，靠 `item_id` 識別（SKU 欄位為空）
  - `681da95ea88cb008fc0c3c27` → 葉黃素加購1盒 NT$480（2026-04 發現）

若出現新的加購 item_id，在 `~/.openclaw/skills/simmpo-bh-report/scripts/bh_report.py` 的 `BH_ADDON_ITEM_IDS` 新增。

詳細文件：`~/.openclaw/skills/simmpo-bh-report/SKILL.md`
