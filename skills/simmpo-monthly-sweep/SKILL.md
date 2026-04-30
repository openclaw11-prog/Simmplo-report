---
name: simmpo-monthly-sweep
description: 抓取 Simmpo 指定月份的肖準 Looker Studio 整月廣告數據（需 agent-browser）。用法：/simmpo-monthly-sweep 2026-03
user-invocable: true
allowed-tools:
  - Bash(python3 *)
  - Bash(export *)
---

執行 Simmpo 月度肖準資料抓取。

從參數取得月份（格式 YYYY-MM）。

執行指令：
```bash
export PATH="$HOME/local/bin:$PATH" && python3 ~/services/monthly_sweep.py \
  --month <YYYY-MM> \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser' 2>&1
```

將腳本原始輸出完整回傳，不要重新計算或改寫數字。

詳細文件：`~/.openclaw/skills/simmpo-monthly-sweep/SKILL.md`
