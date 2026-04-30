# Google Ads API DEVELOPER_TOKEN_INVALID 排查記錄

> 日期：2026-03-20
> 狀態：待解決

## 基本資訊

| 項目 | 值 |
|------|-----|
| MCC 帳號 | 534-306-7958 (Simmpo-MCC帳戶) |
| MCC 擁有者 | amber.chen@simmpo.com |
| Developer Token | `_cRipdml1qUiOj6bl2dj3g` |
| Access Level | Basic Access（2026-03-18 核准） |
| GCP Project (舊) | `potent-bulwark-490107-f6` / client_id `845525702954-...` |
| GCP Project (新) | `openclaw202603-490808` / client_id `776235326664-...` |
| OAuth 帳號 | amber.chen@simmpo.com（已確認） |
| API 版本 | v20（v18 已淘汰、v19 已停用） |
| Case ID | 25327540079 |

## 錯誤訊息

```json
{
  "error": {
    "code": 401,
    "status": "UNAUTHENTICATED",
    "details": [{
      "@type": "type.googleapis.com/google.ads.googleads.v20.errors.GoogleAdsFailure",
      "errors": [{
        "errorCode": { "authenticationError": "DEVELOPER_TOKEN_INVALID" },
        "message": "The developer token is not valid."
      }],
      "requestId": "kTdb0153IUU--9WyGfXMiQ"
    }]
  }
}
```

## 已排除的可能

1. ❌ API 版本錯誤 → v20 回傳正確 JSON（非 HTML 404）
2. ❌ OAuth token 無效 → access token 可正常取得，scope 為 `adwords`
3. ❌ 帳號不對 → 已用 MCC 擁有者 amber.chen 的帳號測試
4. ❌ GCP project 綁定衝突 → 建了全新 project 也一樣失敗
5. ❌ Google Ads API 未啟用 → 已在 GCP project 啟用

## 待確認的可能原因

1. **傳播延遲** — 3/18 核准，僅 2 天，可能需要 3-5 個工作天生效
2. **Google Cloud Organization 不匹配** — GCP project 與 MCC 需在同一 Organization
3. **Developer token 字元問題** — `l`/`I` 容易混淆，需從 API Center 重新複製確認
4. **Developer token 已綁定特定 GCP project** — 若 Test Access 時期曾用舊 project 打過 API

## Request IDs（供 Google 支援查詢）

- `zmit7rX-igy49Pr0rln85A`
- `ejJ0iEJqduARf_htASqDAA`
- `EOhxcsoPukXNmT4-FcPL-g`
- `kTdb0153IUU--9WyGfXMiQ`
- `j1fX-h0krnGrr4WYx1jEWQ` ← 2026-03-25 v20 重測確認

## 進度紀錄

| 日期 | 事項 |
|------|------|
| 2026-03-18 | Basic Access 核准 |
| 2026-03-20 | 排查記錄建立，DEVELOPER_TOKEN_INVALID 持續 |
| 2026-03-25 | v20 重測確認仍 DEVELOPER_TOKEN_INVALID（request ID: j1fX-h0krnGrr4WYx1jEWQ）|
| 2026-03-25 | 寄送 follow-up 信給 Google 支援（Case #25327540079）|

## 下一步

- [x] 等到 3/23（核准後 5 個工作天）再測試
- [ ] 等待 Google Case #25327540079 回覆
- [ ] 從 API Center 重新複製 developer token 確認字元（若 Google 回覆無異常）
- [ ] 確認 GCP project 的 Cloud Organization 設定（若 Google 回覆建議）
