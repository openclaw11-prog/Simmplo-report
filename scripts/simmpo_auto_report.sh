#!/bin/bash
# Simmpo 每日自動報表
# crontab:
#   0 2 * * *  /Users/simmpo-claw/services/simmpo_auto_report.sh first
#   0 8 * * *  /Users/simmpo-claw/services/simmpo_auto_report.sh check
#
# first（2am）：抓昨日數據，寫入 Sheets，記錄數字到 log
# check（8am）：再抓一次，比對 first 的數字，若有不一致以 8am 為準更新 Sheets，並在 log 記錄差異

export TZ=Asia/Taipei
source "$HOME/.claude/.cron_token"  # 1-year OAuth token，到期需重新執行 claude setup-token

ROUND="${1:-first}"   # first or check
LOG="$HOME/services/simmpo_auto_report.log"
DATE=$(date -v-1d +%Y-%m-%d)

echo "========================================" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始執行 ${DATE} 報表（${ROUND}）" >> "$LOG"

export PATH="$HOME/local/bin:/opt/homebrew/bin:$PATH"

if [ "$ROUND" = "first" ]; then
  PROMPT="自動執行 Simmpo 每日報表任務（第一輪 2am）。昨天日期：${DATE}。全程不要詢問確認，直接執行。

步驟 1：執行每日報表腳本（不含肖準）：
\`\`\`bash
export PATH=\"\$HOME/local/bin:/opt/homebrew/bin:\$PATH\" && python3 ~/services/daily_report.py --date ${DATE} --tokens ~/services/simmpo_tokens.json 2>&1
\`\`\`

步驟 2：從步驟 1 的輸出解析以下數值（不要重新計算或改寫數字）：
TW 營業額、HK 營業額、MO 營業額、Meta 廣告費、Google Ads 轉換值、Google Ads 廣告費。

步驟 3：填入 Google Sheets：
- 如果步驟 1 成功，執行：
\`\`\`bash
export PATH=\"\$HOME/local/bin:/opt/homebrew/bin:\$PATH\" && python3 ~/.openclaw/skills/simmpo-sheet-finalize/scripts/finalize_to_sheets.py --date ${DATE} --tw-revenue <TW> --hk-revenue <HK> --mo-revenue <MO> --meta-spend <META> --gads-revenue <GADS_REV> --gads-spend <GADS_SPEND> 2>&1
\`\`\`
- 如果步驟 1 失敗（無法取得數據），執行：
\`\`\`bash
export PATH=\"\$HOME/local/bin:/opt/homebrew/bin:\$PATH\" && python3 ~/.openclaw/skills/simmpo-sheet-finalize/scripts/finalize_to_sheets.py --date ${DATE} --failed 2>&1
\`\`\`

步驟 4：在 log 最後補一行，格式固定如下（方便 8am check 輪解析），數字只填整數不含逗號：
FIRST_ROUND_DATA: TW=<TW> HK=<HK> MO=<MO> SG=<SG> META=<META> GADS_REV=<GADS_REV> GADS_SPEND=<GADS_SPEND>

將這行用 bash 寫入 log：
\`\`\`bash
echo \"FIRST_ROUND_DATA: TW=<TW> HK=<HK> MO=<MO> SG=<SG> META=<META> GADS_REV=<GADS_REV> GADS_SPEND=<GADS_SPEND>\" >> \"$LOG\"
\`\`\`"

else
  # check round（8am）：讀取 first 的數字，比對後決定是否更新
  FIRST_LINE=$(grep "FIRST_ROUND_DATA:" "$LOG" | grep -A0 "" | tail -1)

  PROMPT="自動執行 Simmpo 每日報表任務（第二輪 8am 比對）。昨天日期：${DATE}。全程不要詢問確認，直接執行。

第一輪（2am）記錄的數字如下：
${FIRST_LINE}

步驟 1：執行每日報表腳本（不含肖準）取得最新數字：
\`\`\`bash
export PATH=\"\$HOME/local/bin:/opt/homebrew/bin:\$PATH\" && python3 ~/services/daily_report.py --date ${DATE} --tokens ~/services/simmpo_tokens.json 2>&1
\`\`\`

步驟 2：從步驟 1 的輸出解析最新數值：TW、HK、MO、SG、Meta 廣告費、Google Ads 轉換值、Google Ads 廣告費。

步驟 3：比對第一輪與第二輪數字。
- 若完全相同：在 log 寫入一行：\`CHECK_RESULT: OK（與 first 一致）\`
- 若有差異：
  a. 在 log 寫入差異明細，格式：
     \`CHECK_RESULT: MISMATCH TW: <first值> → <8am值>, HK: <first值> → <8am值>, ...\`（只列出有差異的欄位）
  b. 以 8am 數字為準，更新 Google Sheets：
     \`\`\`bash
     export PATH=\"\$HOME/local/bin:/opt/homebrew/bin:\$PATH\" && python3 ~/.openclaw/skills/simmpo-sheet-finalize/scripts/finalize_to_sheets.py --date ${DATE} --tw-revenue <TW> --hk-revenue <HK> --mo-revenue <MO> --sg-revenue <SG> --meta-spend <META> --gads-revenue <GADS_REV> --gads-spend <GADS_SPEND> 2>&1
     \`\`\`

將 CHECK_RESULT 這行用 bash 寫入 log：
\`\`\`bash
echo \"CHECK_RESULT: ...\" >> \"$LOG\"
\`\`\`"
fi

/opt/homebrew/bin/claude -p \
  --dangerously-skip-permissions \
  "$PROMPT" \
  2>&1 | tee -a "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 執行完畢（${ROUND}）" >> "$LOG"
