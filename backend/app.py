import json
import os
import mimetypes
import asyncio
import base64
import secrets
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .storage import Store
from .geography import matches_region
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
class Preferences(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1] = 1
    default_city: str = Field(default="全球", max_length=80)
    reading_timezone: str = Field(default="UTC", max_length=100)
    news_scope: Literal["global", "follow_city"] = "global"
    daily_selection_limit: int = Field(default=10, ge=1, le=50)
    interests: list[str] = Field(default_factory=list, max_length=30)
    followed_entities: list[str] = Field(default_factory=list, max_length=100)
    disabled_sources: list[str] = Field(default_factory=list, max_length=100)
    industry_buzz: dict = Field(default_factory=lambda: {"enabled": True, "max_share": 0.1, "include_unverified_in_today": False})

    def safe_dict(self):
        data = self.model_dump()
        try:
            ZoneInfo(self.reading_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("时区无效")
        data["excluded_topics"] = ["equipment_review", "equipment_comparison", "buying_guide", "equipment_rumor"]
        buzz = data["industry_buzz"]
        if not isinstance(buzz.get("enabled", True), bool):
            raise ValueError("圈内动态开关必须为布尔值")
        share = buzz.get("max_share", 0.1)
        if not isinstance(share, (int, float)) or not 0 <= share <= 1:
            raise ValueError("圈内动态比例无效")
        data["industry_buzz"] = {"enabled": buzz.get("enabled", True), "max_share": share, "include_unverified_in_today": False}
        return data


class BookmarkInput(BaseModel):
    target_type: Literal["content", "event"]
    target_id: str = Field(min_length=1, max_length=200)
    status: Literal["want_to_see", "planning", "seen"] = "want_to_see"
    note: str = Field(default="", max_length=2000)


class ImportedBookmark(BaseModel):
    content_id: str | None = Field(default=None, max_length=200)
    event_id: str | None = Field(default=None, max_length=200)
    status: Literal["want_to_see", "planning", "seen"]
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def one_target(self):
        if bool(self.content_id) == bool(self.event_id):
            raise ValueError("收藏必须且只能引用一条资讯或一个活动")
        return self


class ImportInput(BaseModel):
    schema_version: Literal[1]
    preferences: Preferences
    bookmarks: list[ImportedBookmark] = Field(max_length=5000)


def create_app(db_path=None):
    store = Store(db_path or os.getenv("CULTURE_DESK_DB", str(ROOT / "runtime/culture-desk.db")))
    if db_path is None:
        store.restore_public_snapshot(ROOT / "data/live.json")
    app = FastAPI(title="幕间休息 · Intermission", version="0.10.0")
    app.state.store = store
    password = os.getenv("CULTURE_DESK_PASSWORD", "")

    @app.middleware("http")
    async def personal_access(request, call_next):
        if password:
            authorization = request.headers.get("authorization", "")
            try:
                scheme, value = authorization.split(" ", 1)
                username, supplied = base64.b64decode(value, validate=True).decode().split(":", 1)
                valid = scheme.lower() == "basic" and secrets.compare_digest(username.encode(), b"owner") and secrets.compare_digest(supplied.encode(), password.encode())
            except (ValueError, UnicodeError):
                valid = False
            if not valid:
                return Response("请输入个人访问密码", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Culture Desk", charset="UTF-8"'})
        return await call_next(request)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "storage": "sqlite", "version": "0.7.0"}

    @app.get("/api/dataset")
    async def dataset(mode: Literal["demo", "live"] = "live"):
        result = store.dataset(mode)
        result["source_status"] = store.source_status()
        return result

    @app.get("/api/content")
    async def content(mode: Literal["demo", "live"] = "live", channel: str | None = None, country: str | None = None, city: str | None = None, kind: str | None = None, language: str | None = None, q: str = ""):
        rows = store.dataset(mode)["content"]
        return [r for r in rows if (not channel or r["channel"] == channel) and matches_region(r, country, city) and (not kind or r["kind"] == kind) and (not language or r["language"] == language) and (not q or q.lower() in " ".join(str(r.get(k) or "") for k in ("title_original", "title_zh", "summary_zh")).lower())]

    @app.get('/api/editorial-regions')
    @app.get('/reports/regional-coverage.json')
    async def editorial_region_report():
        from .editorial_regions import regional_coverage
        config = json.loads((ROOT / 'config/sources.json').read_text())
        path = ROOT / 'data/coverage-audit.json'
        audit = json.loads(path.read_text()) if path.exists() else None
        return regional_coverage(store.dataset('live'), config, audit)

    @app.get('/api/attention-units')
    @app.get('/reports/attention-units.json')
    async def attention_units():
        from .attention_units import attention_report
        config = json.loads((ROOT / 'config/sources.json').read_text())
        path = ROOT / 'data/coverage-audit.json'
        audit = json.loads(path.read_text()) if path.exists() else None
        return attention_report(store.dataset('live'), config, audit)

    @app.get('/api/attention-units/{unit_id}')
    @app.get('/reports/attention-units/{unit_id}.json')
    async def attention_unit(unit_id: str):
        report = await attention_units()
        unit = next((u for u in report['units'] if u['id'] == unit_id), None)
        if not unit:
            raise HTTPException(404, '关注单元不存在')
        return unit

    @app.get("/api/integrations/babel/{content_id}")
    @app.get("/integrations/babel/{content_id}.json")
    async def babel_article(content_id: str):
        from .babel_export import CONTENT_ID, article_payload
        if not CONTENT_ID.fullmatch(content_id):
            raise HTTPException(404, "正文不存在")
        with store.connect() as db:
            row = db.execute("SELECT * FROM content WHERE id=? AND is_demo=0", (content_id,)).fetchone()
        catalog = {source['id']: source for source in json.loads((ROOT / 'config/sources.json').read_text())['sources']}
        payload = article_payload(dict(row), catalog) if row else None
        if not payload:
            raise HTTPException(404, "正文尚未取得")
        return payload

    @app.get("/api/events")
    async def events(mode: Literal["demo", "live"] = "live", country: str | None = None, city: str | None = None, start: str | None = None, end: str | None = None):
        return [r for r in store.dataset(mode)["events"] if matches_region(r, country, city) and (not start or (r["date_precision"] == "day" and (r["end_date"] or r["start_date"]) >= start)) and (not end or (r["date_precision"] == "day" and r["start_date"] <= end))]

    @app.get("/api/preferences")
    async def preferences():
        return store.preferences()

    @app.put("/api/preferences")
    async def save_preferences(body: Preferences):
        try:
            return store.save_preferences(body.safe_dict())
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/bookmarks")
    async def bookmarks():
        return store.bookmarks()

    @app.post("/api/bookmarks")
    async def save_bookmark(body: BookmarkInput):
        try:
            result = store.save_bookmark(body.target_type, body.target_id, body.status, body.note)
            from .jobs import notify
            notify(store)
            return result
        except KeyError as exc:
            raise HTTPException(404, "内容不存在") from exc

    @app.delete("/api/bookmarks/{bookmark_id}")
    async def delete_bookmark(bookmark_id: str):
        if not store.delete_bookmark(bookmark_id):
            raise HTTPException(404, "收藏不存在")
        return {"deleted": True}

    @app.get("/api/export")
    async def export():
        return {"schema_version": 1, "preferences": store.preferences(), "bookmarks": store.bookmarks()}

    @app.post("/api/import")
    async def import_data(body: ImportInput):
        try:
            count = store.import_data(body.preferences.safe_dict(), [row.model_dump() for row in body.bookmarks])
            return {"imported": count}
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/sources")
    async def sources():
        return store.source_status()

    @app.get("/api/notifications")
    async def notifications():
        from .jobs import notify
        notify(store)
        with store.connect() as db:
            return [dict(row) for row in db.execute("SELECT notifications.* FROM notifications JOIN bookmarks ON bookmarks.event_id=notifications.event_id WHERE bookmarks.status!='seen' ORDER BY notifications.created_at DESC LIMIT 50")]

    @app.patch("/api/notifications/{notification_id}")
    async def read_notification(notification_id: str):
        with store.connect() as db:
            changed = db.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,)).rowcount
        if not changed:
            raise HTTPException(404, "提醒不存在")
        return {"read": True}

    refresh_task = None

    @app.post("/api/refresh")
    async def refresh():
        nonlocal refresh_task
        if refresh_task is not None and not refresh_task.done():
            return {"status": "busy"}
        from .jobs import refresh as run_refresh
        refresh_task = asyncio.create_task(asyncio.to_thread(run_refresh, store))
        return {"status": "started"}

    @app.get("/api/jobs/status")
    async def job_status():
        with store.connect() as db:
            row = db.execute("SELECT value FROM job_state WHERE id='last-refresh'").fetchone()
            lock = db.execute("SELECT value FROM job_state WHERE id='refresh-lock'").fetchone()
        from datetime import datetime, timezone
        locked = bool(lock and datetime.fromisoformat(lock[0]) > datetime.now(timezone.utc))
        return {"running": locked or (refresh_task is not None and not refresh_task.done()), "last_refresh": json.loads(row[0]) if row else None}

    # A bounded asset allowlist keeps the small local edition independent of
    # background file-worker threads and never exposes project/runtime files.
    assets = {"index.html", "styles.css", "theme.css", "favicon.svg", "data.js", "core.js", "ui.js", "app.js"}
    assets.update({'fonts/intermission-masthead-v1.woff2', 'fonts/intermission-sans-v1.woff2', 'fonts/intermission-title-v1.woff2', 'fonts/notoseriftc-OFL.txt',
                   'fonts/intermission-news-v1.woff2', 'fonts/mashanzheng-OFL.txt',
                   'fonts/notosanssc-OFL.txt', 'fonts/newsreader-OFL.txt'})

    @app.get("/")
    async def index():
        return Response((ROOT / "frontend/index.html").read_bytes(), media_type="text/html")

    @app.get("/{asset:path}")
    async def static_asset(asset: str):
        if asset not in assets:
            raise HTTPException(404, "页面不存在")
        return Response((ROOT / "frontend" / asset).read_bytes(), media_type=mimetypes.guess_type(asset)[0] or "application/octet-stream")

    return app


app = create_app()
