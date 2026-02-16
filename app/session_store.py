"""Cookie-based session middleware. Session data is stored in a signed cookie
so it survives server restarts (important for --reload during development)."""

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

COOKIE_NAME = "mn_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days

# Keys that are safe to persist in the cookie (no large objects)
_PERSIST_KEYS = {"plex_token", "server_url", "server_name", "pin_id", "pin_code"}

_signer = URLSafeSerializer(settings.secret_key, salt="session")


def _load_session(request: Request) -> dict:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return {}
    try:
        data = _signer.loads(raw)
        if isinstance(data, dict):
            return data
    except BadSignature:
        pass
    return {}


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        session = _load_session(request)
        request.state.session = session

        response = await call_next(request)

        # Only persist safe keys into the cookie
        to_persist = {k: v for k, v in session.items() if k in _PERSIST_KEYS}
        signed = _signer.dumps(to_persist)
        response.set_cookie(
            COOKIE_NAME,
            signed,
            max_age=MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        return response


def clear_session(request: Request) -> None:
    request.state.session.clear()
