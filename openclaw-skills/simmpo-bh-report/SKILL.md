---
name: simmpo-bh-report
version: 1.0
description: 抓取 Simmpo 官網指定日期的葉黃素（BH系列）銷售數據，包含正常購買、加購促銷兩種情境，輸出銷售總金額與含葉黃素訂單的定檔總金額。
---

# Simmpo 葉黃素銷售報表

## 功能

- **葉黃素銷售總金額**：該日期所有葉黃素品項的成交金額加總
- **含葉黃素訂單定檔總金額**：只要訂單內有任一葉黃素品項，整張訂單 total 納入加總

## 葉黃素識別規則

| 購買方式 | item_type | 識別方式 |
|----------|-----------|---------|
| 正常購買 | `Product` | SKU 前綴 `BH`（BH0100=1盒, BH0104=10盒） |
| 加購促銷 | `AddonProduct` | `item_id` 對照表（SKU 欄位為空） |

### 已知加購 item_id

| item_id | 說明 | 單價 | 發現日期 |
|---------|------|------|---------|
| `681da95ea88cb008fc0c3c27` | 葉黃素加購1盒 | NT$480 | 2026-04-03 |

> 若出現新的加購促銷，在 `scripts/bh_report.py` 的 `BH_ADDON_ITEM_IDS` 中新增 item_id。

## 使用方式

```bash
python3 ~/.openclaw/skills/simmpo-bh-report/scripts/bh_report.py \
  --date 2026-04-03 \
  --tokens ~/services/simmpo_tokens.json
```

## 給 OpenClaw 的執行指示

```
請執行以下指令，並將腳本的原始輸出完整回傳：

python3 ~/.openclaw/skills/simmpo-bh-report/scripts/bh_report.py \
  --date 2026-04-03 \
  --tokens ~/services/simmpo_tokens.json 2>&1
```

## 注意事項

- `cancelled` 訂單排除在外
- AddonProduct 金額取 `item_price`（原始加購價），Product 取 `order_discounted_price`（折後價）
- 定檔金額 = 整張訂單 total，不只是葉黃素品項金額
