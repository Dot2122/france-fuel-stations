"""HTTP routes for station queries."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.services.spatial import SpatialIndex

# API Router is like a mini-app: groupe related routes.
# It will be registered on the main FastAPI app in main.py
router = APIRouter(prefix="/stations", tags=["stations"])


# ---------------------------------------------------------------------------
# Response schemas (Pydantic)
# Pydantic models define the shape of JSON responses.
# FastAPI uses them to serialize Python objects → JSON automatically.
# ---------------------------------------------------------------------------
class StationResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    postcode: Optional[str]
    city: Optional[str]
    address: Optional[str]
    price_gazole: Optional[float]
    price_sp95: Optional[float]
    price_sp98: Optional[float]
    price_e10: Optional[float]
    price_e85: Optional[float]
    price_gplc: Optional[float]


class NearestStationResult(BaseModel):
    distance_km: float
    station: StationResponse


class NearestStationsResponse(BaseModel):
    query_lat: float
    query_lon: float
    count: int
    results: list[NearestStationResult]


# ---------------------------------------------------------------------------
# Dependency: provides the SpatialIndex to routes
# The actual index object is injected by main.py at startup (see below).
# ---------------------------------------------------------------------------

# Module-level reference - set by main.py after building the index
_spatial_index: Optional[SpatialIndex] = None


def get_spatial_index() -> SpatialIndex:
    """FastAPI dependency: returns the shared SpatialIndex instance.

    Raises:
        HTTPException: _description_

    Returns:
        SpatialIndex: _description_
    """
    if _spatial_index is None:
        raise HTTPException(status_code=503, detail="Spatial index not ready.")
    return _spatial_index


def set_spatial_index(index: SpatialIndex) -> None:
    """Called by main.py at startup to inject the index.

    Args:
        index (SpatialIndex): _description_
    """
    global _spatial_index
    _spatial_index = index


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/nearest", response_model=NearestStationsResponse)
def nearest_stations(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    n: int = Query(5, ge=1, le=50, description="Number of results"),
    index: SpatialIndex = Depends(get_spatial_index),
) -> NearestStationsResponse:
    """Return the n nearest fuel stations to the given coordinates.
    Example: GET /stations/nearest?lat=48.8566&lon=2.3522&n=5

    Args:
        lat (float, optional): _description_. Defaults to Query(..., ge=-90, le=90, description="Latitude").
        lon (float, optional): _description_. Defaults to Query(..., ge=-180, le=180, description="Longitude").
        n (int, optional): _description_. Defaults to Query(5, ge=1, le=50, description="Number of results").
        index (SpatialIndex, optional): _description_. Defaults to Depends(get_spatial_index).

    Returns:
        NearestStationsResponse: _description_
    """
    results = index.find_nearest(lat, lon, n)
    return NearestStationsResponse(
        query_lat=lat,
        query_lon=lon,
        count=len(results),
        results=[
            NearestStationResult(
                distance_km=round(dist, 3),
                station=StationResponse(**vars(station)),
            )
            for dist, station in results
        ],
    )
