"""FastAPI application entry point.
Handles server lifespan (startup/shutdown) and route registration.
"""

from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles

from backend.routes.stations import set_spatial_index, router as stations_router
from backend.services.spatial import build_spatial_index

DB_PATH = Path("data/processed/stations.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Code here runs ONCE at server startup (before any request is handled).
    The 'yield' separates startup (before) from shutdown (after).
    This is where we build the KD-tree so it's ready in memory.

    Args:
        app (FastAPI): _description_

    Yields:
        _type_: _description_
    """
    print("Building spacial index...")
    index = build_spatial_index(DB_PATH)
    set_spatial_index(index)
    print(f"Spatial index ready - {len(index.stations)} stations loaded.")

    yield  # <- server is running, handling requests

    # Shutdown: nothing to clean up here (in-memory index is GC'd)
    print("Shutting down.")


app = FastAPI(title="France Fuel Stations API", version="0.1.0", lifespan=lifespan)
# Serve static files (favicon, future frontend assets)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register route group
app.include_router(stations_router)


# Health check - useful to verify the server is alive
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
