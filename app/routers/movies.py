"""Movie generation, filters, and poster proxy."""

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from plexapi.server import PlexServer

from app.dependencies import require_auth
from app.services import plex_service

router = APIRouter(prefix="/api", tags=["movies"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/filters", response_class=HTMLResponse)
async def filters(request: Request, plex: PlexServer = Depends(require_auth)):
    data = plex_service.get_filters(plex)
    return templates.TemplateResponse(
        "partials/filter_form.html", {"request": request, **data}
    )


@router.post("/generate", response_class=HTMLResponse)
async def generate(request: Request, plex: PlexServer = Depends(require_auth)):
    form = await request.form()
    movies = plex_service.get_random_movies(
        plex,
        count=int(form.get("count", 3)),
        genre=form.get("genre", ""),
        content_rating=form.get("content_rating", ""),
        decade=form.get("decade", ""),
        min_rating=float(form.get("min_rating", 0)),
        playlist_key=form.get("playlist_key", ""),
    )
    return templates.TemplateResponse(
        "partials/movie_cards.html", {"request": request, "movies": movies}
    )


@router.get("/poster/{rating_key}")
async def poster_proxy(rating_key: str, request: Request, plex: PlexServer = Depends(require_auth)):
    """Proxy poster images so the Plex token stays server-side."""
    thumb_url = f"/library/metadata/{rating_key}/thumb"
    plex_url = plex._baseurl + thumb_url
    token = plex._token

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            plex_url,
            params={"X-Plex-Token": token},
            follow_redirects=True,
            timeout=10,
        )

    if resp.status_code != 200:
        return Response(status_code=404)

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )
