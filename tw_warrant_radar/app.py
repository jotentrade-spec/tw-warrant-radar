from __future__ import annotations

from pathlib import Path

from flask import Flask, flash, redirect, render_template, send_from_directory, url_for

from .goodinfo import goodinfo_stock_url
from .models import init_db
from .scanner import api_catalog, latest_scan, refresh_api_catalog, scan_market


def create_app() -> Flask:
    project_root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config["SECRET_KEY"] = "tw-warrant-radar-dev"
    init_db()

    @app.context_processor
    def inject_reference_links():
        return {"goodinfo_stock_url": goodinfo_stock_url}

    @app.get("/")
    def index():
        rows = latest_scan(limit=10)
        apis = api_catalog()
        return render_template("index.html", rows=rows, apis=apis)

    @app.get("/radar")
    def radar():
        rows = latest_scan(limit=100)
        return render_template("radar.html", rows=rows)

    @app.post("/scan")
    def scan():
        frame = scan_market()
        flash(f"掃描完成：{len(frame)} 筆候選資料已儲存。")
        return redirect(url_for("radar"))

    @app.post("/apis/refresh")
    def refresh_apis():
        endpoints = refresh_api_catalog()
        flash(f"API 目錄更新完成：找到 {len(endpoints)} 個候選 endpoint。")
        return redirect(url_for("apis"))

    @app.get("/apis")
    def apis():
        endpoints = api_catalog()
        return render_template("apis.html", apis=endpoints)

    @app.get("/manifest.webmanifest")
    def manifest():
        return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")

    @app.get("/sw.js")
    def service_worker():
        return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")

    return app
