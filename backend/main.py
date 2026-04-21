from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from backend.puzzle.generator import generate_puzzle
from backend.puzzle.validator import validate
from backend.puzzle.hint import find_hint

app = FastAPI(title="Tango Puzzle API")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    content += "  <url>\n    <loc>/</loc>\n    <changefreq>monthly</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
    content += "</urlset>\n"
    return PlainTextResponse(content, media_type="application/xml")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return HTMLResponse(content=(FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


DIFFICULTY = {
    "facile":    {"min_visible": 18, "max_clues": 12},
    "moyen":     {"min_visible": 12, "max_clues": 8},
    "difficile": {"min_visible": 6,  "max_clues": 5},
    "extreme":   {"min_visible": 0,  "max_clues": 8},
}


@app.get("/puzzle")
def get_puzzle(
    size: int = Query(default=6, ge=4, le=6),
    difficulty: str = Query(default="moyen"),
):
    if size % 2 != 0:
        raise HTTPException(status_code=400, detail="size must be even")
    if difficulty not in DIFFICULTY:
        raise HTTPException(status_code=400, detail=f"difficulty must be one of {list(DIFFICULTY)}")
    return generate_puzzle(size, **DIFFICULTY[difficulty])


class ValidateRequest(BaseModel):
    grid: list[list[str | None]]
    clues: list[dict]
    partial: bool = True


@app.post("/validate")
def post_validate(body: ValidateRequest):
    size = len(body.grid)
    if size == 0 or any(len(row) != size for row in body.grid):
        raise HTTPException(status_code=400, detail="grid must be square")
    return validate(body.grid, body.clues, size, body.partial)


class HintRequest(BaseModel):
    grid: list[list[str | None]]
    clues: list[dict]


@app.post("/hint")
def post_hint(body: HintRequest):
    size = len(body.grid)
    if size == 0 or any(len(row) != size for row in body.grid):
        raise HTTPException(status_code=400, detail="grid must be square")
    hint = find_hint(body.grid, body.clues, size)
    if hint is None:
        return {"hint": None}
    return {"hint": hint}
