"""All Plex library interactions."""

import random
import time

from plexapi.server import PlexServer
from plexapi.video import Movie

_filter_cache: dict[str, tuple[float, dict]] = {}  # keyed by server URL
FILTER_CACHE_TTL = 300  # 5 minutes


def get_movie_library(plex: PlexServer):
    """Return the first movie library section."""
    for section in plex.library.sections():
        if section.type == "movie":
            return section
    return None


def get_filters(plex: PlexServer) -> dict:
    """Return available filter values for the UI (cached 5 min per server)."""
    cache_key = plex._baseurl
    now = time.monotonic()
    cached = _filter_cache.get(cache_key)
    if cached and (now - cached[0]) < FILTER_CACHE_TTL:
        return cached[1]

    lib = get_movie_library(plex)
    if not lib:
        return {"genres": [], "content_ratings": [], "decades": [], "playlists": []}

    genres = sorted(g.title for g in lib.listFilterChoices("genre"))
    content_ratings = sorted(r.title for r in lib.listFilterChoices("contentRating"))

    # Build decade list from the library's year range
    years = lib.listFilterChoices("decade")
    decades = sorted(y.title for y in years)

    # Playlists
    playlists = []
    for pl in plex.playlists():
        if pl.playlistType == "video":
            playlists.append({"title": pl.title, "ratingKey": pl.ratingKey})

    result = {
        "genres": genres,
        "content_ratings": content_ratings,
        "decades": decades,
        "playlists": playlists,
    }
    _filter_cache[cache_key] = (now, result)
    return result


def get_random_movies(
    plex: PlexServer,
    *,
    count: int = 3,
    genre: str = "",
    content_rating: str = "",
    decade: str = "",
    min_rating: float = 0,
    playlist_key: str = "",
) -> list[dict]:
    """Pick random movies matching filters."""
    if playlist_key:
        movies = _get_playlist_movies(plex, playlist_key)
    else:
        lib = get_movie_library(plex)
        if not lib:
            return []
        movies = lib.all()

    # Apply filters
    filtered: list[Movie] = []
    for m in movies:
        if not isinstance(m, Movie):
            continue
        if genre and genre not in [g.tag for g in m.genres]:
            continue
        if content_rating and m.contentRating != content_rating:
            continue
        if decade:
            decade_start = int(decade)
            if not m.year or not (decade_start <= m.year < decade_start + 10):
                continue
        if min_rating and (m.audienceRating or 0) < min_rating:
            continue
        filtered.append(m)

    count = min(count, len(filtered))
    if count == 0:
        return []

    chosen = random.sample(filtered, count)
    return [_movie_to_dict(m) for m in chosen]


def _get_playlist_movies(plex: PlexServer, rating_key: str) -> list:
    for pl in plex.playlists():
        if str(pl.ratingKey) == str(rating_key):
            return pl.items()
    return []


def _movie_to_dict(m: Movie) -> dict:
    return {
        "title": m.title,
        "year": m.year,
        "rating_key": m.ratingKey,
        "summary": m.summary or "",
        "audience_rating": m.audienceRating,
        "content_rating": m.contentRating or "",
        "duration_minutes": round(m.duration / 60000) if m.duration else None,
        "genres": [g.tag for g in m.genres],
        "has_thumb": bool(m.thumb),
    }
