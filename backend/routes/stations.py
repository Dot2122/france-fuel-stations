"""HTTP routes for station queries."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.services.spatial import SpatialIndex
from backend.services.geocoding import GeocodingError, geocode_address

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
    query_lat: Optional[float]
    query_lon: Optional[float]
    query_label: Optional[str]
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
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    address: Optional[str] = Query(None, description="French address (alternative to lat/lon)"),
    n: int = Query(5, ge=1, le=50, description="Number of results"),
    index: SpatialIndex = Depends(get_spatial_index),
) -> NearestStationsResponse:
    # """
    # Find the nearest fuel stations to a given location.

    # Provide **either** coordinates (`lat` + `lon`) **or** a French `address` — not both, not neither.

    # - `lat` / `lon`: decimal degrees (WGS84)
    # - `address`: geocoded via the French BAN API (api-adresse.data.gouv.fr)
    # """
    """Return the n nearest fuel stations.
    Provide either (`lat` + `lon`) or `address` — not both, not neither.

    Examples:
    -   GET /stations/nearest?lat=48.8566&lon=2.3522&n=5
    -   GET /stations/nearest?address=10 rue de Rivoli Paris&n=5

    Args:
    -   lat (float, optional): _description_. Defaults to Query(..., ge=-90, le=90, description="Latitude").
    -   lon (float, optional): _description_. Defaults to Query(..., ge=-180, le=180, description="Longitude").
    -   n (int, optional): _description_. Defaults to Query(5, ge=1, le=50, description="Number of results").
    -   index (SpatialIndex, optional): _description_. Defaults to Depends(get_spatial_index).

    Raises:
        HTTPException: _description_

    Returns:
        NearestStationsResponse: _description_
    """
    coords_provided = lat is not None and lon is not None
    address_provided = address is not None

    if coords_provided and address_provided:
        raise HTTPException(status_code=422, detail="Provide either (lat, lon) or address - not both")

    if not coords_provided and not address_provided:
        raise HTTPException(status_code=422, detail="Provide either (lat, lon) or address.")

    # --- Resolve address to coordinates if needed ---
    query_label: Optional[str] = None

    if address_provided:
        try:
            result = geocode_address(address)
            lat = result.latitude
            lon = result.longitude
            query_label = result.label
        except GeocodingError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # --- Spatial query ---
    # At this point, lat and lon are guaranteed to be set
    # (either provided directly or resolved from address above)
    assert lat is not None and lon is not None  # narrows type for static analysis
    results = index.find_nearest(lat, lon, n)

    return NearestStationsResponse(
        query_lat=lat,
        query_lon=lon,
        query_label=query_label,
        count=len(results),
        results=[
            NearestStationResult(
                distance_km=round(dist, 3),
                station=StationResponse(**vars(station)),
            )
            for dist, station in results
        ],
    )
