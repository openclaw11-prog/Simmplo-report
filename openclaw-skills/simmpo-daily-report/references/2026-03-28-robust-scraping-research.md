# Google Ads 與 Looker Studio 每日報表抓取方案研究報告

## 研究日期
2026 年 3 月 28 日

## 研究背景

目前 Simmpo 每日報表抓取的現況:

1. **Google Ads**: 透過 agent-browser 模擬點擊「變更日期範圍」並 fill textbox
   - **缺點**: UI 稍微變動 (例如 button 變成 div) 就會失效，不穩定
   
2. **Looker Studio (肖準)**: 透過模擬點擊「匯出資料」下載 CSV
   - **缺點**: Looker Studio 的圖表選單按鈕座標不穩定，且 virtual scroll 可能導致下載按鈕不在畫面中

---

## 研究目標

尋找比目前 agent-browser UI 模擬更穩定的報表抓取方案，針對:
1. Google Ads (Google Ads 與 Local Services Ads)
2. Looker Studio (肖準)

---

## 研究結果

### 一、Google Ads 報表抓取方案

#### 1. URL 參數直接強制顯示特定日期 ❌ **不可行**

**研究結論**: Google Ads **不支援**透過 URL 參數 (如 `TIMERANGE`, `startDate`, `endDate`) 直接強制顯示特定日期並下載 CSV。

**原因**:
- Google Ads 出於安全和隱私考量，並未提供可直接在瀏覽器中建構的帶有日期參數的公開下載 URL
- Google Ads 的報表日期範圍必須在 UI 中設定或透過 API 查詢語言定義
- 即使是 Local Services Ads API，日期參數也是透過 API 請求 (`startDate.day`, `startDate.month`, `startDate.year`) 而非 URL 參數

**官方文件來源**:
- https://developers.google.com/google-ads/api/docs/query/date-ranges

---

#### 2. Report Editor 的持久連結下載 CSV ❌ **部分可行但有局限**

**研究結論**: Google Ads 報表編輯器 **不直接提供**「永久 URL」來連結到帶有自訂日期範圍的編輯中報表。

**可行方案 - 使用 Google Ads 報表 API (推薦)**:
```python
# Google Ads API - 官方推薦的自動化方式
1. 使用 Google Ads API 構建 GAQL 查詢
2. 指定日期範圍 (自訂或預定義)
3. 執行查詢並下載 CSV 或 TSV

查詢語法範例 (GAQL):
    # 自訂日期範圍
    SELECT ... WHERE segments.date BETWEEN '2024-01-01' AND '2024-01-31'
    
    # 預定義日期範圍
    SELECT ... WHERE segments.date DURING LAST_30_DAYS

執行步驟:
    1. 使用 `GoogleAdsService.Search` 或 `SearchStream`
    2. API 傳回 JSON/row objects
    3. 前端程式轉換為 CSV
```

**可行方案 - Google Ads Scripts (可透過電報)**:
```javascript
// Google Ads Scripts - 支援自訂日期範圍
if (context.isNewReport()) {
    // 設定報表
    context.getReport().setName("Daily Report");
    context.getReport().setStartDate(new Date(year, month - 1, day));
    context.getReport().setEndDate(new Date(year, month - 1, day));
    context.getReport().setFrequency(RANGE_FREQUENCY_CUSTOM);
    
    // 執行報表並發送 CSV
    context.newJob().submit();
}
```

**可選方案 - 排程報表 (via API)**:
- 通過 API 建立報表後，可設定排程自動以 CSV 格式通過電子郵件發送
- 但排程報表無法直接通過 URL 訪問，必須配置報表 ID 和排程

**官方文件來源**:
- https://developers.google.com/google-ads/api/docs/reporting/overview
- https://developers.google.com/google-ads/api/docs/oauth/overview

---

#### 3. JavaScript injection (localStorage/sessionStorage) ❌ **不建議**

**研究結論**: **強烈不建議**使用 client-side JavaScript injection 來操縱 `localStorage` 或 `sessionStorage`。

**風險**:
1. **違反服務條款**: Google Ads 的條款明確禁止使用「任何自動化手段或爬蟲形式」存取廣告相關資訊
2. **XSS 漏洞**: localStorage/sessionStorage 易受跨站腳本攻擊
3. **不可靠**: UI 隨意變更就會失效
4. **不受支援**: Google 不支援任何未經授權的注入方式
5. **可能導致封鎖帳號**

**官方推薦方式**:
- **Google Ads API**: 官方推薦的程式化方式
- **Google Ads Scripts**: 適合在帳號內自動化的任務

**官方文件來源**:
- https://developers.google.com/google-ads/api/docs/api-policy/terms

---

### 二、Looker Studio 報表抓取方案

#### 1. 直接下載 CSV 的 URL ❌ **不可行**

**研究結論**: Looker Studio **不直接提供**可透過 URL 直接下載報表/圖表 CSV 的 API。

**原因**:
- Looker Studio 的 API 主要用於管理 Looker Studio 資產 (報表、資料來源)
- API **不支援**直接將報表資料匯出為 PDF/JSON/CSV
- 每次匯出 CSV 需要手動點擊「匯出資料」選單

**官方文件來源**:
- https://developers.google.com/looker-studio/integrate/api
- https://discuss.google.dev/t/export-pdf-or-metadata-from-looker-studio-with-api/177990

---

#### 2. 確保「匯出資料」選單一定出現 ✅ **可行的技術方案**

**方案 A: 使用 component ID 直接操作 (推薦)**

```python
# 使用 document.querySelector 直接點擊內部 component ID
# Looker Studio 使用 web component 結構

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://lookerstudio.google.com/reporting/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX")
    page.wait_for_load_state("networkidle")
    
    # 進入檢視模式
    page.click('text="檢視"')  # 或直接點擊視圖選單
    
    # 使用 CSS selector 定位匯出按鈕
    # 假设匯出按鈕的 component ID 相對穩定
    page.click('.looker-toolbar__export-button')  # 或類似的穩定 selector
    
    # 選擇 CSV 格式
    page.click("text='CSV'")
    
    # 等待下載
    page.wait_for_timeout(2000)
```

**方案 B: 使用 iframe 或 Shadow DOM**

```python
# 有些按鈕可能在 iframe 或 Shadow DOM 內
frame = page.frame('#some-iframe-id')  # 或等待 shadow dom
frame.click('.looker-export-dropdown')
```

**方案 C: 使用定位結合屬性**

```python
# 使用更精確的定位方式 (css属性、data-testid 等)
page.click('button[data-testid="export-data-action"]')  # 如果有 data-testid
# 或
page.click('button:has-text("匯出資料")')
```

---

#### 3. 其他可行方案 (推薦)

**方案 A: 透過 Google Sheets API 間接獲取**

```python
# 步驟:
# 1. 在 Looker Studio 中將報表匯出到 Google Sheets
# 2. 使用 Google Sheets API 讀取 Sheets
# 3. 使用 Sheets API 匯出 CSV

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

service = build('sheets', 'v4', credentials=creds)
spreadsheet = service.spreadsheets().get(spreadsheetId='...')

# 下載特定 sheet
body = MediaIoBaseDownload.from_uri(
    filename='report.csv',
    media=...
)
request = body.request()
...
```

**方案 B: 直接使用原始資料來源 API**

```python
# 如果 Looker Studio 報表連接的是 BigQuery/Sheets/其他 API
# 直接從原始來源查詢，完全跳過 Looker Studio UI

# 範例：從 BigQuery 直接查詢
from google.cloud import bigquery

query = f"SELECT * FROM `project.dataset.table` WHERE date BETWEEN '2024-01-01' AND '2024-01-31'"
query_job = client.query(query)
query_job.to_dataframe()
query_job.to_csv('output.csv')
```

**方案 C: 使用 Looker (非 Looker Studio) API**

```python
# 如果使用的是 Google Cloud Looker (與 Looker Studio 不同)
# Looker 提供完整的 API 可運行查詢並匯出 CSV/JSON

from looker_sdk import client, model4

# 運行查詢
query = client.looker.run_query(query_id, query_format='looker4')
results = query.run(result_format='csv')
```

**官方文件來源**:
- https://docs.cloud.google.com/looker/docs/reference/looker-api/latest/methods/Query/run_query
- https://docs.cloud.google.com/looker/docs/studio/export-data-from-a-chart

---

## 總結建議

### 針對 Google Ads:

| 方案 | 穩定性 | 可行性 | 推薦度 |
|------|--------|--------|---------|
| Google Ads API (Search) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Google Ads Scripts | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Report Editor URL | ⭐ | ⭐ | ⭐ |
| JS Injection (localStorage) | ⭐⭐ | ⭐⭐ | ❌ **不建議** |

**推薦方案**: **Google Ads API**
- 優點: 官方 API、穩定、可程式化、有完整文件支持
- 可以自訂日期範圍 (使用 GAQL)
- 可下載 CSV/TSV 格式
- 支援大資料量 (SearchStream)

---

### 針對 Looker Studio:

| 方案 | 穩定性 | 可行性 | 推薦度 |
|------|--------|--------|---------|
| 原始資料來源 API | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Looker API (非 Studio) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Google Sheets API | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| UI 自動化 (穩定 selector) | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

**推薦方案**: **使用原始資料來源 API**
- 優點: 最穩定、可程式化、無 UI 依賴
- 如果 Looker Studio 連接的是 BigQuery/Sheets，直接從來源查詢
- 完全跳過 UI 操作的不穩定性

---

## 改良版 `daily_report_robust.py` 範例

詳細實作代碼請參見下方 `daily_report_robust.py` 檔案

---

## 後續注意事項

1. **API Key/credential 管理**: 請妥善管理 Google Ads 和 Looker Studio API 的 credential
2. **Rate Limit**: Google Ads API 有 Rate Limit 限制，請注意使用
3. **Data Refresh**: 報表資料有延遲，請注意數據的即時性
4. **Error Handling**: 請加入完善的錯誤處理和重試機制

---

## 參考文獻

1. Google Ads API: https://developers.google.com/google-ads/api
2. Google Ads Query Language (GAQL): https://developers.google.com/google-ads/api/docs/query/date-ranges
3. Google Ads Scripts: https://developers.google.com/google-ads/scripts/docs/start
4. Looker Studio API: https://developers.google.com/looker-studio/integrate/api
5. Google Ads Report CSV: https://support.google.com/google-ads/answer/6072565