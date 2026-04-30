#!/bin/bash
# 解密 tokens.tar.gpg 並還原到正確位置
# 用法：bash decrypt_tokens.sh
# 前提：gpg 已安裝（brew install gnupg）

set -e
SRC="$HOME/simmplo-report/secrets/tokens.tar.gpg"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -f "$SRC" ]; then
    echo "找不到 $SRC，請先 git pull"
    exit 1
fi

# 解密（會要求輸入密碼）
gpg --batch \
    --output "$TMP/tokens.tar.gz" \
    --decrypt "$SRC"

tar -xzf "$TMP/tokens.tar.gz" -C "$TMP"

# 還原
mkdir -p "$HOME/services"
cp "$TMP/simmpo_tokens.json" "$HOME/services/simmpo_tokens.json"
chmod 600 "$HOME/services/simmpo_tokens.json"

mkdir -p "$HOME/.claude"
cp "$TMP/cron_token" "$HOME/.claude/.cron_token"
chmod 600 "$HOME/.claude/.cron_token"

echo "✓ 解密完成"
echo "  ~/services/simmpo_tokens.json"
echo "  ~/.claude/.cron_token"
