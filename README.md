# Movie Night

Can't decide what to watch? Movie Night randomly picks movies from your Plex library with optional filters for genre, rating, decade, and playlists.

## Features

- **Plex OAuth** — Sign in with your Plex account, no API keys to configure
- **Smart filters** — Narrow by genre, content rating, decade, minimum audience score, or playlist
- **Playlist support** — Pick random movies from any of your Plex video playlists
- **Poster cards** — Movie posters with details on hover (title, year, rating, genres, summary)
- **Secure** — Plex tokens stay server-side; poster images are proxied so tokens never reach the browser

## Quick Start

```bash
git clone https://github.com/RustyBower/MovieNight.git
cd MovieNight
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env and set a random SECRET_KEY
uvicorn app.main:app --reload
```

Visit `http://localhost:8000`, sign in with Plex, and roll the dice.

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) + [Jinja2](https://jinja.palletsprojects.com/) + [HTMX](https://htmx.org/)
- [Tailwind CSS](https://tailwindcss.com/) (CDN)
- [PlexAPI](https://github.com/pkkid/python-plexapi) for Plex integration
- [itsdangerous](https://itsdangerous.palletsprojects.com/) for signed session cookies

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret for signing session cookies | `change-me` |
| `PLEX_APP_CLIENT_ID` | Plex app client identifier | `movienight-web-app` |
| `BASE_URL` | Override base URL for OAuth redirect | Auto-detected |

## License

MIT
