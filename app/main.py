"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.routers import auth, movies, pages
from app.session_store import SessionMiddleware

app = FastAPI(title="Movie Night")

# Middleware
app.add_middleware(SessionMiddleware)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(movies.router)


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """On 401, redirect to login — via HX-Redirect for HTMX requests."""
    if request.headers.get("HX-Request"):
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/"
        return response
    return RedirectResponse("/", status_code=302)


@app.exception_handler(502)
async def plex_unreachable_handler(request: Request, exc: HTTPException):
    """Plex connection failed — show retry message instead of logging out."""
    detail = getattr(exc, "detail", "Plex server unreachable")
    if request.headers.get("HX-Request"):
        return Response(
            f'<div class="text-center py-8">'
            f'<p class="text-red-400 mb-4">{detail}</p>'
            f'<div class="flex items-center justify-center gap-4">'
            f'<button hx-get="{request.url.path}" hx-target="#filter-section" hx-swap="innerHTML"'
            f' class="bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold py-2 px-6 rounded-lg">'
            f"Retry</button>"
            f'<a href="/auth/servers?pick=1" class="text-zinc-400 hover:text-zinc-200 underline text-sm">'
            f"Change server</a></div></div>",
            status_code=200,
            media_type="text/html",
        )
    return Response(f"<h1>{detail}</h1><p><a href='/generate'>Retry</a></p>", status_code=502, media_type="text/html")
