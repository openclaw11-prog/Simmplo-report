# Simmpo 報表系統 — 重灌還原流程

> 重灌後照這份文件一步一步做，完成後報表系統全部回來。

---

## 事前準備（舊機器上）

在換機器之前，確認已在舊機器執行過：

```bash
bash ~/simmplo-report/scripts/encrypt_tokens.sh
cd ~/simmplo-report
git add secrets/tokens.tar.gpg
git commit -m "update tokens"
git push
```

**解密密碼存好**（1Password 或其他密碼管理器）。

---

## 步驟一：安裝基礎工具

```bash
xcode-select --install
```

---

## 步驟二：Clone repo

```bash
git clone https://github.com/openclaw11-prog/Simmplo-report ~/simmplo-report
```

---

## 步驟三：一鍵還原

```bash
bash ~/simmplo-report/scripts/setup.sh
```

途中會要求輸入解密密碼（輸入一次即可）。  
完成後自動還原：tokens、腳本 symlinks、Claude skills、cron jobs。

---

## 步驟四：安裝 Claude Code

```bash
brew install claude
claude login
```

---

## 步驟五：更新 cron OAuth token（若過期）

`.cron_token` 有效期一年，若 cron 執行失敗（Sheets 沒更新），重新取得：

```bash
claude setup-token
```

---

## 步驟六：安裝 agent-browser 並登入 Google

```bash
# 安裝
npm install -g agent-browser

# 把 ~/local/bin 加進 PATH（寫入 ~/.zshrc）
echo 'export PATH="$HOME/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 開啟 Looker Studio 並登入 Google 帳號
npx agent-browser --profile ~/agent-browser-profile open "https://lookerstudio.google.com"
```

登入後關閉視窗即可，session 已存在 `~/agent-browser-profile`。

---

## 步驟七：驗證

```bash
python3 ~/services/daily_report.py \
  --date $(date -v-1d +%Y-%m-%d) \
  --tokens ~/services/simmpo_tokens.json
```

看到 TW / HK / Meta / Google Ads 數字出現就表示還原成功。

---

## 完成後提醒

每次 token 更新（Shopline / Meta / Google Ads 重新授權）後，記得重新加密備份：

```bash
bash ~/simmplo-report/scripts/encrypt_tokens.sh
cd ~/simmplo-report && git add secrets/tokens.tar.gpg && git commit -m "update tokens" && git push
```
