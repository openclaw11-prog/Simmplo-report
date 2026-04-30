---
name: simmpo-daily-report
description: 拉取 Simmpo 指定日期的每日報表，包含 Shopline 各地區營業額、Meta 廣告費、Google Ads。可選加入肖準（需 agent-browser）。用法：/simmpo-daily-report 2026-04-01 或 /simmpo-daily-report 2026-04-01 --with-xiaozhun
user-invocable: true
allowed-tools:
  - Bash(python3 *)
  - Bash(export *)
---

執行 Simmpo 每日報表。

從參數取得日期（格式 YYYY-MM-DD）。若無日期參數，使用昨天的台北時間日期。
若有 `--with-xiaozhun` 參數，加上 `--agent-browser 'npx agent-browser'`。

執行指令：
```bash
export PATH="$HOME/local/bin:$PATH" && python3 ~/services/daily_report.py \
  --date <DATE> \
  --tokens ~/services/simmpo_tokens.json [--agent-browser 'npx agent-browser'] 2>&1
```

將腳本原始輸出完整回傳，不要重新計算或改寫數字。

詳細文件：`~/.openclaw/skills/simmpo-daily-report/SKILL.md`
