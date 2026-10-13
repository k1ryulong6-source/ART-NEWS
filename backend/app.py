import json
import os
import mimetypes
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .storage import Store

ROOT = Path(__file__).resolve().parents[1]
CITY_COUNTRIES = {"东京": "JP", "京都": "JP", "大阪": "JP", "上海": "CN", "北京": "CN"}


def city_matches(record, city):
    return not city or (record["country"] == CITY_COUNTRIES.get(city, record["country"]) and record["city"] in (None, city))


class Preferences(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1] = 1
    default_city: str = Field(default="东京", max_length=80)
    reading_timezone: Literal["Asia/Tokyo", "Asia/Shanghai", "UTC"] = "Asia/Tokyo"
    daily_selection_limit: int = Field(default=10, ge=1, le=50)
    interests: list[str] = Field(default_factory=list, max_length=30)
    followed_entities: list[str] = Field(default_factory=list, max_length=100)
    industry_buzz: dict = Field(default_factory=lambda: {"enabled": True, "max_share": 0.1, "include_unverified_in_today": False})

    def safe_dict(self):
        data = self.model_dump()
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
    app = FastAPI(title="映间 · Culture Desk", version="0.1.0")
    app.state.store = store

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "storage": "sqlite", "version": "0.1.0"}

    @app.get("/api/dataset")
    async def dataset(mode: Literal["demo", "live"] = "demo"):
        return store.dataset(mode)

    @app.get("/api/content")
    async def content(mode: Literal["demo", "live"] = "demo", channel: str | None = None, country: str | None = None, city: str | None = None, kind: str | None = None, q: str = ""):
        rows = store.dataset(mode)["content"]
        return [r for r in rows if (not channel or r["channel"] == channel) and (not country or r["country"] == country) and city_matches(r, city) and (not kind or r["kind"] == kind) and (not q or q.lower() in " ".join(str(r.get(k) or "") for k in ("title_original", "title_zh", "summary_zh")).lower())]

    @app.get("/api/events")
    async def events(mode: Literal["demo", "live"] = "demo", country: str | None = None, city: str | None = None, start: str | None = None, end: str | None = None):
        return [r for r in store.dataset(mode)["events"] if (not country or r["country"] == country) and city_matches(r, city) and (not start or (r["date_precision"] == "day" and (r["end_date"] or r["start_date"]) >= start)) and (not end or (r["date_precision"] == "day" and r["start_date"] <= end))]

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
            return store.save_bookmark(body.target_type, body.target_id, body.status, body.note)
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

    # A bounded asset allowlist keeps the small local edition independent of
    # background file-worker threads and never exposes project/runtime files.
    assets = {"index.html", "styles.css", "favicon.svg", "data.js", "core.js", "app.js"}

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
