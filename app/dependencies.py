"""FastAPI dependencies for authentication."""

import logging
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from plexapi.server import PlexServer
from requests import Session as RequestsSession

log = logging.getLogger("movienight")


def get_session(request: Request) -> dict:
    return request.state.session


def require_auth(request: Request) -> PlexServer:
    """Return a connected PlexServer or raise 401."""
    session = request.state.session
    token = session.get("plex_token")
    server_url = session.get("server_url")

    if not token or not server_url:
        log.warning("require_auth: no token/server_url in session")
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Cache the PlexServer instance in the session to avoid reconnecting
    cached: PlexServer | None = session.get("_plex_server")
    if cached is not None:
        return cached

    log.info("require_auth: connecting to %s", server_url)
    try:
        # Plex servers often have certs issued for *.plex.direct, not custom domains.
        # Disable SSL verification for non-plex.direct hosts to avoid cert mismatch.
        http_session = RequestsSession()
        hostname = urlparse(server_url).hostname or ""
        if not hostname.endswith("plex.direct"):
            http_session.verify = False
        plex = PlexServer(server_url, token, session=http_session)
    except Exception as exc:
        # Don't clear credentials — could be a transient failure.
        # Return a 502 so the user can retry without losing their session.
        log.error("require_auth: Plex connection failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Plex server unreachable: {exc}")

    session["_plex_server"] = plex
    return plex
