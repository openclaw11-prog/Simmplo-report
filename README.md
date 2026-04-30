# Simmplo Report

Simmpo 每日銷售報表系統。抓取 Shopline 各地區營業額、Meta 廣告費、Google Ads，自動寫入 Google Sheets，並支援肖準（Looker Studio）。

---

## 重灌後還原指南

> 開一個新終端機，照以下步驟執行，完成後報表系統就全部回來了。

### 前置條件

重灌前先確認以下兩件事都做了：

1. **執行加密備份**（在舊機器上）：
   ```bash
   bash ~/simmplo-report/scripts/encrypt_tokens.sh
   cd ~/simmplo-report && git add secrets/tokens.tar.gpg && git commit -m "update encrypted tokens" && git push
   ```
2. **記住解密密碼**（存在 1Password 或記在腦子裡）

---

### 步驟一：安裝 Xcode Command Line Tools 與 Git

```bash
xcode-select --install
```

### 步驟二：Clone 此 repo

```bash
git clone https://github.com/openclaw11-prog/Simmplo-report ~/simmplo-report
```

### 步驟三：執行一鍵還原腳本

```bash
bash ~/simmplo-report/scripts/setup.sh
```

這個腳本會自動完成：
- 安裝 Homebrew（若未安裝）
- 安裝 `gnupg`、`python@3.14`
- **解密 tokens**（會要求輸入密碼，還原 `~/services/simmpo_tokens.json` 和 `~/.claude/.cron_token`）
- 建立 `~/services/daily_report.py`、`~/services/simmpo_auto_report.sh`、`~/services/xiaozhun/` 的 symlinks
- 建立 `~/.claude/skills/` 和 `~/.openclaw/skills/` 的 symlinks
- 設定 cron jobs（每天 02:00 first / 08:00 check）

### 步驟四：安裝 Claude Code CLI

```bash
brew install claude
# 或從官網下載：https://claude.ai/download
claude login
```

### 步驟五：取得 Cron OAuth Token

Cron job 用的是一個 1 年有效的 OAuth token，存在 `~/.claude/.cron_token`。  
若備份中的 token 已過期（報表停止寫入 Sheets），需要重新取得：

```bash
# 重新登入後執行（具體指令視 Claude Code 版本而定）
claude setup-token
```

### 步驟六：安裝 agent-browser（肖準 Looker Studio 用）

```bash
mkdir -p ~/local/bin
npm install -g agent-browser   # 或 npx agent-browser（免安裝）
export PATH="$HOME/local/bin:$PATH"   # 加進 ~/.zshrc
```

**重新登入 Google**（必要，browser profile 無法備份）：

```bash
export PATH="$HOME/local/bin:$PATH"
npx agent-browser --profile ~/agent-browser-profile open "https://lookerstudio.google.com"
# 在彈出的瀏覽器視窗中登入 Google 帳號
```

登入後 profile 會存在 `~/agent-browser-profile`，之後 cron 可自動使用。

### 步驟七：驗證

```bash
# 測試昨日報表（不含肖準）
python3 ~/services/daily_report.py \
  --date $(date -v-1d +%Y-%m-%d) \
  --tokens ~/services/simmpo_tokens.json

# 測試含肖準
export PATH="$HOME/local/bin:$PATH"
python3 ~/services/daily_report.py \
  --date $(date -v-1d +%Y-%m-%d) \
  --tokens ~/services/simmpo_tokens.json \
  --agent-browser 'npx agent-browser'
```

---

## 系統架構

```
~/simmplo-report/               ← 本 repo（單一事實來源）
├── scripts/
│   ├── daily_report.py         ← 每日報表主腳本（symlink ← ~/services/）
│   ├── simmpo_auto_report.sh   ← cron 驅動腳本（symlink ← ~/services/）
│   ├── setup.sh                ← 重灌還原腳本
│   ├── encrypt_tokens.sh       ← 加密 tokens → secrets/tokens.tar.gpg
│   └── decrypt_tokens.sh       ← 解密 tokens → ~/services/ & ~/.claude/
├── openclaw-skills/
│   ├── simmpo-daily-report/    ← 含 xiaozhun 模組（symlink ← ~/.openclaw/skills/）
│   ├── simmpo-sheet-finalize/  ← Google Sheets 寫入腳本
│   ├── simmpo-bh-report/       ← 葉黃素銷售報表
│   └── simmpo-monthly-sweep/   ← 月報
├── skills/                     ← Claude skills（symlink ← ~/.claude/skills/）
├── secrets/
│   └── tokens.tar.gpg          ← AES-256 加密的 token 包（git 追蹤）
└── logs/                       ← cron 執行 log（git 忽略）
```

### Cron 排程

| 時間 | 指令 | 說明 |
|------|------|------|
| 每天 02:00 | `simmpo_auto_report.sh first` | 抓昨日數據，寫入 Sheets，記錄到 log |
| 每天 08:00 | `simmpo_auto_report.sh check` | 重抓比對，若有差異以 8am 為準更新 Sheets |

### 地區對應

| 地區 | 來源 | 備註 |
|------|------|------|
| TW | Shopline（台灣地址）| 跨境 7-11 取貨訂單歸入 TW |
| HK | Shopline（香港地址）| 原始幣別 HKD |
| MO | Shopline（澳門地址）| 原始幣別 MOP |
| MY | Shopline（馬來西亞地址）| 原始幣別 MYR |
| SG | Shopline（新加坡地址）| 2026-04-08 起支援 |
| Meta | Meta Ads API | act_1481816722260744（保護貼）|
| Google Ads | Google Ads API v20 | MCC 534-306-7958，子帳號 1164087860 |
| 肖準 | Looker Studio（agent-browser）| 資料延遲最長 1 天 |

---

## Token 管理

所有 token 加密備份在 `secrets/tokens.tar.gpg`（AES-256）。

| Token | 解密後位置 |
|-------|-----------|
| Shopline / Meta / Google Ads | `~/services/simmpo_tokens.json` |
| Claude cron OAuth | `~/.claude/.cron_token` |

**更新 token 後記得重新備份：**
```bash
bash ~/simmplo-report/scripts/encrypt_tokens.sh
cd ~/simmplo-report && git add secrets/tokens.tar.gpg && git commit -m "update tokens" && git push
```

---

## 常用指令

```bash
# 手動跑報表
python3 ~/services/daily_report.py --date 2026-04-30 --tokens ~/services/simmpo_tokens.json

# 葉黃素銷售報表
python3 ~/.openclaw/skills/simmpo-bh-report/scripts/bh_report.py --date 2026-04-30

# 查 cron log
tail -100 ~/simmplo-report/logs/simmpo_auto_report.log

# 更新加密備份
bash ~/simmplo-report/scripts/encrypt_tokens.sh && cd ~/simmplo-report && git add secrets/tokens.tar.gpg && git commit -m "update tokens" && git push
```
