from __future__ import annotations

import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "hotel-agent-backend"
FRONTEND = ROOT / "frontend"

sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

# Keep the existing API and docs routes, but make the product root the frontend.
app.router.routes[:] = [
    route
    for route in app.router.routes
    if not (getattr(route, "path", None) == "/" and getattr(route, "name", None) == "root")
]

app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
