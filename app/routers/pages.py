"""Page routes (landing page, generate page)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = request.state.session
    if session.get("plex_token") and session.get("server_url"):
        return RedirectResponse("/generate", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    session = request.state.session
    if not session.get("plex_token") or not session.get("server_url"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("generate.html", {"request": request})
