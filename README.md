# tw-warrant-radar

`tw-warrant-radar` 是一個 Python Flask 專案，用來自動讀取 TWSE/TPEX OpenAPI，建立「券商回收權證雷達」。

這個工具的目標是找出可能出現「低價買進、券商或市場仍願意掛買回收」條件的權證候選。它是研究與掃描工具，不保證獲利，也不是投資建議。

## 功能

- 自動讀取 TWSE/TPEX `swagger.json`
- 自動尋找權證相關 endpoint
- 抓取權證行情、成交、基本資料候選 API
- 自動整理欄位：
  - 代號
  - 名稱
  - 發行券商
  - 收盤價
  - 委買
  - 委賣
  - 成交量
  - 標的
  - 履約價
  - 到期日
- 建立 `market_maker_score`
- Flask 頁面：
  - `/` 首頁
  - `/radar` 顯示前 100 名候選權證
  - `/apis` 顯示目前抓到的權證 API
- PWA + RWD：
  - 可安裝為瀏覽器 APP
  - 支援離線快取已載入過的頁面
  - 手機版表格自動改為卡片式閱讀
- Goodinfo 參考連結：
  - 雷達清單的標的欄位會提供 Goodinfo 快速連結
  - 用於補充標的股概況、法人、融資融券、大盤環境
- SQLite 儲存每日掃描結果

## 評分邏輯

`market_maker_score` 目前由以下條件加總：

- 價格 `<= 0.02` 大幅加分
- 委買 `>= 0.01` 大幅加分
- 委賣存在加分
- 成交量存在加分
- bid/ask 價差小加分
- 剩餘天數 `>= 10` 加分

## 安裝

```powershell
cd C:\Users\Admin\Documents\華爾街模型\tw-warrant-radar
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果你的 Windows 沒有 `py -3.11`，也可以用：

```powershell
python -m venv .venv
```

## 啟動

```powershell
python run.py
```

開啟：

```text
http://127.0.0.1:5000/
```

## GitHub Pages 網站

本專案已包含 GitHub Pages 靜態網站：

```text
docs/index.html
docs/styles.css
```

也包含自動部署 workflow：

```text
.github/workflows/pages.yml
```

推到 GitHub 後，到 repository 的 `Settings -> Pages`，選擇 GitHub Actions，即可部署專案介紹網站。

注意：GitHub Pages 只能部署靜態網站；真正會掃描 TWSE/TPEX OpenAPI 的 Flask APP 需要在本機、Render、Railway、VPS 等可執行 Python 的服務上運行。詳細見 `DEPLOYMENT.md`。

## API 探測與掃描

進入首頁按「立即掃描」，或進入 `/apis` 按「重新讀取 Swagger」。

也可以用命令列測試 endpoint 與欄位 mapping：

```powershell
python tools\test_endpoints.py --limit 20
```

如果看到有資料但 `mapping` 少了欄位，就把新欄位名稱加進 `tw_warrant_radar\normalizer.py` 的 `FIELD_ALIASES`。

預設 swagger 來源：

```text
TWSE_SWAGGER_URL=https://openapi.twse.com.tw/v1/swagger.json
TPEX_SWAGGER_URL=https://www.tpex.org.tw/openapi/swagger.json
```

可複製 `.env.example` 的內容到你的啟動環境，改成自己的來源。

## 欄位 mapping

欄位名稱由 `tw_warrant_radar/normalizer.py` 自動推斷。如果 TWSE/TPEX 回傳欄位名稱不同，請把新欄位加到 `FIELD_ALIASES`。

例如：

```python
"bid": ("委買", "委買價", "最佳買價", "買價", "Bid", "BestBidPrice")
```

## 專案結構

```text
tw-warrant-radar/
  run.py
  requirements.txt
  tw_warrant_radar/
    app.py
    api_discovery.py
    config.py
    goodinfo.py
    models.py
    normalizer.py
    scanner.py
    scoring.py
  templates/
    base.html
    index.html
    radar.html
    apis.html
    _warrant_table.html
  static/
    app.js
    icon.svg
    manifest.webmanifest
    sw.js
    styles.css
  tools/
    test_endpoints.py
```
