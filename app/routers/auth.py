"""Plex OAuth login/poll/logout and server selection."""

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.session_store import clear_session

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

PLEX_PINS_URL = "https://plex.tv/api/v2/pins"
PLEX_AUTH_URL = "https://app.plex.tv/auth#"
PLEX_RESOURCES_URL = "https://plex.tv/api/v2/resources"

PLEX_HEADERS = {
    "Accept": "application/json",
    "X-Plex-Product": settings.plex_app_name,
    "X-Plex-Client-Identifier": settings.plex_app_client_id,
}


def _pick_best_url(urls: list[dict]) -> str:
    """Pick the best connection URL: prefer remote on standard port (443), then any remote, then local."""
    remote = [u for u in urls if u["label"] == "remote"]
    local = [u for u in urls if u["label"] == "local"]
    # Prefer remote URLs on standard HTTPS port (reverse proxy, proper cert)
    for u in remote:
        parsed = urlparse(u["uri"])
        if parsed.port is None or parsed.port == 443:
            return u["uri"]
    # Then any remote
    if remote:
        return remote[0]["uri"]
    # Fallback to local
    return (local or urls)[0]["uri"]


def _base_url(request: Request) -> str:
    if settings.base_url:
        return settings.base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/login")
async def login(request: Request):
    """Create a Plex PIN, then redirect to Plex OAuth."""
    base = _base_url(request)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            PLEX_PINS_URL,
            headers=PLEX_HEADERS,
            data={"strong": "true", "X-Plex-Product": settings.plex_app_name},
        )
        resp.raise_for_status()
        pin_data = resp.json()

    pin_id = pin_data["id"]
    pin_code = pin_data["code"]

    # Store pin in session for polling
    session = request.state.session
    session["pin_id"] = pin_id
    session["pin_code"] = pin_code

    forward_url = f"{base}/auth/callback"
    auth_url = (
        f"{PLEX_AUTH_URL}?"
        f"clientID={settings.plex_app_client_id}"
        f"&code={pin_code}"
        f"&forwardUrl={forward_url}"
        f"&context%5Bdevice%5D%5Bproduct%5D={settings.plex_app_name}"
    )
    return RedirectResponse(auth_url, status_code=302)


@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request):
    """Plex redirects here after user approves; render polling page."""
    return templates.TemplateResponse("login_waiting.html", {"request": request})


@router.get("/poll")
async def poll(request: Request):
    """HTMX polls this to check if PIN has been claimed."""
    session = request.state.session
    pin_id = session.get("pin_id")
    if not pin_id:
        return HTMLResponse('<p class="text-red-400">No pending login.</p>', status_code=400)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PLEX_PINS_URL}/{pin_id}",
            headers=PLEX_HEADERS,
        )
        resp.raise_for_status()
        pin_data = resp.json()

    auth_token = pin_data.get("authToken")
    if not auth_token:
        # Still waiting — HTMX will re-poll
        return HTMLResponse('<p class="text-zinc-400">Waiting for Plex approval...</p>')

    # Success — store token, clean up pin
    session["plex_token"] = auth_token
    session.pop("pin_id", None)
    session.pop("pin_code", None)

    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/auth/servers"
    return response


@router.get("/servers", response_class=HTMLResponse)
async def servers(request: Request):
    """List Plex servers the user owns."""
    session = request.state.session
    token = session.get("plex_token")
    if not token:
        return RedirectResponse("/", status_code=302)

    headers = {**PLEX_HEADERS, "X-Plex-Token": token}
    async with httpx.AsyncClient() as client:
        resp = await client.get(PLEX_RESOURCES_URL, headers=headers, params={"includeHttps": "1"})
        resp.raise_for_status()
        resources = resp.json()

    servers = []
    for r in resources:
        if r.get("provides") and "server" in r["provides"]:
            connections = r.get("connections", [])
            urls = []
            for c in connections:
                uri = c.get("uri")
                if not uri:
                    continue
                local = c.get("local", False)
                urls.append({"uri": uri, "label": "local" if local else "remote"})
            if urls:
                servers.append({"name": r["name"], "urls": urls})

    # Auto-select: prefer remote URL on standard port (443) → any remote → first local
    force_pick = request.query_params.get("pick")
    if servers and not force_pick:
        best = _pick_best_url(servers[0]["urls"])
        session["server_url"] = best
        session["server_name"] = servers[0]["name"]
        return RedirectResponse("/generate", status_code=302)

    return templates.TemplateResponse(
        "partials/server_select.html",
        {"request": request, "servers": servers},
    )


@router.post("/select-server")
async def select_server(request: Request):
    form = await request.form()
    server_url = form.get("server_url")
    if not server_url:
        return RedirectResponse("/auth/servers", status_code=302)

    request.state.session["server_url"] = server_url
    request.state.session["server_name"] = form.get("server_name", "")
    # Clear cached PlexServer so it reconnects to the new one
    request.state.session.pop("_plex_server", None)
    return RedirectResponse("/generate", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    clear_session(request)
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("mn_session")
    return response
