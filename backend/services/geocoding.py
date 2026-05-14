from dataclasses import dataclass

import httpx

# Base URL for the BAN (Base Adresse Nationale) geocoding API
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/"


@dataclass
class GeocodingResult:
    """Result of a geocoding query."""

    latitude: float
    longitude: float
    label: str  # Full address as understood by the API (e.g. "10 Rue de Rivoli 75001 Paris")
    score: float


class GeocodingError(Exception):
    """Raised when the address cannot be geocoded."""

    pass


def geocode_address(address: str):
    """Convert a French address string to coordinates using BAN API.

    Args:
        address (str): _Free-form French address (e.g. "10 rue de Rivoli Paris")._

    Returns:
        GeocodingResult: _GeocodingResult with lat/lon and metadata._

    Raises:
        GeocodingError: _If the address cannot be found or the API is unavailable._
    """
    try:
        response = httpx.get(
            BAN_API_URL,
            params={"q": address, "limit": 1, "autocomplete": 0},  # We only need the best match  # Disable autocomplete for exact queries
            timeout=5.0,  # Fail fast - don't block the request too long
        )
        response.raise_for_status()  # Raise if HTTP error (4xx, 5xx)
    except httpx.TimeoutException:
        raise GeocodingError("Geocoding API time out.")
    except httpx.HTTPError as e:
        raise GeocodingError(f"Geocoding API error : {e}")

    data = response.json()

    # The API returns a GeoJSON FeatureCollection
    # "features" is empty if no address matched
    features = data.get("features", [])
    if not features:
        raise GeocodingError(f"No results found for address : '{address}'")

    # Best match is always the first feature
    best = features[0]
    props = best["properties"]
    lon, lat = best["geometry"]["coordinates"]

    # Warn if confidence is low (threshold is arbitrary but reasonable)
    score = props.get("score", 0.0)
    if score < 0.5:
        raise GeocodingError(f"Low confidence geocoding result (score={score:.2f}) for: '{address}'")

    return GeocodingResult(
        latitude=lat,
        longitude=lon,
        label=props.get("label", address),
        score=score,
    )
