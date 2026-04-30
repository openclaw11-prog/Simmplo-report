#!/bin/bash
# 將所有 Simmpo token 加密為 tokens.tar.gpg（AES-256）
# 用法：bash encrypt_tokens.sh
# 輸出：~/simmplo-report/secrets/tokens.tar.gpg

set -e
OUT_DIR="$HOME/simmplo-report/secrets"
OUT_FILE="$OUT_DIR/tokens.tar.gpg"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$OUT_DIR"

# 收集 token 檔
cp "$HOME/services/simmpo_tokens.json"   "$TMP/simmpo_tokens.json"
cp "$HOME/.claude/.cron_token"           "$TMP/cron_token"

# 打包 + AES-256 加密（會要求輸入密碼兩次）
BUNDLE="$(mktemp).tar.gz"
tar -C "$TMP" -czf "$BUNDLE" simmpo_tokens.json cron_token
gpg --yes \
    --cipher-algo AES256 \
    --symmetric \
    --output "$OUT_FILE" \
    "$BUNDLE"
rm -f "$BUNDLE"

chmod 600 "$OUT_FILE"
echo "✓ 加密完成：$OUT_FILE"
echo "  現在可以 git add secrets/tokens.tar.gpg && git push"
