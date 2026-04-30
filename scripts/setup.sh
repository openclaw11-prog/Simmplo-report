#!/bin/bash
# Simmpo 報表系統 — 重灌後一鍵還原
# 用法：bash ~/simmplo-report/scripts/setup.sh
# 前提：此 repo 已 clone 到 ~/simmplo-report，且 secrets/tokens.tar.gpg 已存在

set -e
REPO="$HOME/simmplo-report"

echo "=== Simmpo 報表系統還原 ==="

# ── 1. 系統工具 ────────────────────────────────────────────────────────────────
echo "[1/6] 檢查依賴..."
if ! command -v brew &>/dev/null; then
    echo "  安裝 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
for pkg in gnupg python@3.14; do
    if ! brew list --formula | grep -q "^${pkg}$"; then
        echo "  brew install $pkg..."
        brew install "$pkg"
    fi
done
echo "  依賴 OK"

# ── 2. 解密 tokens ─────────────────────────────────────────────────────────────
echo "[2/6] 解密 tokens（會要求輸入密碼）..."
bash "$REPO/scripts/decrypt_tokens.sh"

# ── 3. services 目錄與 symlinks ────────────────────────────────────────────────
echo "[3/6] 建立 services symlinks..."
mkdir -p "$HOME/services"

# 主腳本
ln -sf "$REPO/scripts/daily_report.py"      "$HOME/services/daily_report.py"
ln -sf "$REPO/scripts/simmpo_auto_report.sh" "$HOME/services/simmpo_auto_report.sh"
chmod +x "$REPO/scripts/simmpo_auto_report.sh"

# xiaozhun 模組（daily_report.py 從 ~/services/ 啟動時用相對路徑找 xiaozhun）
ln -sfn "$REPO/openclaw-skills/simmpo-daily-report/scripts/xiaozhun" \
        "$HOME/services/xiaozhun"
echo "  services OK"

# ── 4. Claude skills ────────────────────────────────────────────────────────────
echo "[4/6] 建立 Claude skills symlinks..."
mkdir -p "$HOME/.claude/skills"
for skill in simmpo-daily-report simmpo-bh-report simmpo-sheet-finalize simmpo-monthly-sweep; do
    ln -sfn "$REPO/skills/$skill" "$HOME/.claude/skills/$skill"
done
echo "  ~/.claude/skills/ OK"

# ── 5. OpenClaw skills ──────────────────────────────────────────────────────────
echo "[5/6] 建立 OpenClaw skills symlinks..."
mkdir -p "$HOME/.openclaw/skills"
for skill in simmpo-daily-report simmpo-bh-report simmpo-sheet-finalize simmpo-monthly-sweep; do
    ln -sfn "$REPO/openclaw-skills/$skill" "$HOME/.openclaw/skills/$skill"
done
echo "  ~/.openclaw/skills/ OK"

# ── 6. Cron jobs ────────────────────────────────────────────────────────────────
echo "[6/6] 設定 cron jobs..."
CRON_ENTRY_1="0 2 * * * /Users/$(whoami)/services/simmpo_auto_report.sh first"
CRON_ENTRY_2="0 8 * * * /Users/$(whoami)/services/simmpo_auto_report.sh check"

( crontab -l 2>/dev/null | grep -v "simmpo_auto_report"; \
  echo "$CRON_ENTRY_1"; \
  echo "$CRON_ENTRY_2" ) | crontab -
echo "  cron OK（2am first / 8am check）"

# ── 完成 ────────────────────────────────────────────────────────────────────────
mkdir -p "$REPO/logs"
echo ""
echo "=== 還原完成 ==="
echo ""
echo "剩餘手動步驟（見 README.md）："
echo "  A. 安裝 Claude Code CLI"
echo "  B. claude 登入 → 取得 cron OAuth token"
echo "  C. 安裝 agent-browser 並重新登入 Google（Looker Studio 用）"
echo "  D. 驗證：python3 ~/services/daily_report.py --date \$(date -v-1d +%Y-%m-%d) --tokens ~/services/simmpo_tokens.json"
