# GitHub 部署說明

這個專案分成兩層：

1. `docs/`：GitHub Pages 靜態網站，展示專案與使用方式。
2. Flask APP：真正掃描 TWSE/TPEX OpenAPI 的 Python 後端，需部署到可執行 Python 的服務。

## GitHub Pages

推到 GitHub 後，到 repository：

```text
Settings -> Pages -> Build and deployment -> GitHub Actions
```

然後 workflow 會使用 `.github/workflows/pages.yml` 部署 `docs/`。

## Flask APP 本機啟動

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

開啟：

```text
http://127.0.0.1:5000/
```

## 後端正式部署

GitHub Pages 不能執行 Flask 後端。若要讓雷達在網路上真的掃描資料，建議部署到：

- Render
- Railway
- Fly.io
- VPS

啟動命令：

```bash
python run.py
```

正式環境可把 `DATABASE_URL` 改成持久化資料庫；預設是 SQLite。
