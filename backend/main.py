import hashlib
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from backend.puzzle.generator import generate_puzzle
from backend.puzzle.validator import validate
from backend.puzzle.hint import find_hint

app = FastAPI(title="Tango Puzzle API")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Empreinte du contenu des assets, calculée au démarrage. Elle sert de
# numéro de version dans leur URL : à chaque déploiement qui les modifie,
# l'URL change et le navigateur est obligé de retélécharger. Sans ça, un
# navigateur sans en-tête Cache-Control applique une durée de fraîcheur
# heuristique et peut servir l'ancienne version pendant des jours.
VERSIONED_ASSETS = ("style.css", "app.js")


def _asset_version() -> str:
    digest = hashlib.sha256()
    for name in VERSIONED_ASSETS:
        digest.update((FRONTEND_DIR / name).read_bytes())
    return digest.hexdigest()[:8]


ASSET_VERSION = _asset_version()


class VersionedStaticFiles(StaticFiles):
    """Sert les assets avec une politique de cache explicite.

    Une URL portant un ?v=... désigne un contenu figé : elle peut être
    gardée indéfiniment. Sans version (le favicon), on revalide à chaque
    fois — c'est peu coûteux grâce à l'ETag, et jamais périmé.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        if query.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", VersionedStaticFiles(directory=str(FRONTEND_DIR)), name="static")


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
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    for name in VERSIONED_ASSETS:
        html = html.replace(f"/static/{name}", f"/static/{name}?v={ASSET_VERSION}")
    # La page elle-même porte les URLs versionnées : elle ne doit jamais
    # être servie depuis le cache sans être revalidée.
    return HTMLResponse(content=html, headers={"Cache-Control": "no-cache"})


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
