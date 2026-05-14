import sqlite3
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from scipy.spatial import KDTree

# Earth radius in km - used to convert degree distances to km (approximation)
EARTH_RADIUS_KM = 6371.0


@dataclass
class Station:
    """Lightweight station record returned by spatial queries."""

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


@dataclass
class SpatialIndex:
    """In-memory spatial index built from the stations database.
    Holds the KD-tree and the parallel list of Station objects.
    """

    tree: KDTree
    stations: list[Station]

    def find_nearest(self, lat: float, lon: float, n: int = 5) -> list[tuple[float, Station]]:
        """Return the n nearest stations to (lat, lon).
        Results are sorted by Haversine distance (ascending).

        Args:
            lat (float): _Query latitude in decimal degrees._
            lon (float): _Query longitude in decimal degrees._
            n (int, optional): _Number of results to return. Defaults to 5._

        Returns:
            list[tuple[float, Station]]: _List of (distance_km, Station) tuples._
        """
        # Query the KD-tree - distances are in degrees here, not km
        n_clamped = min(n, len(self.stations))
        _, indices = self.tree.query([lat, lon], k=n_clamped)

        # Scalar case: scipy returns a plain int when k=1
        if isinstance(indices, (int, np.integer)):
            indices = [indices]

        # Re-rank by true Haversine distance
        results: list[tuple[float, Station]] = []
        for idx in indices:
            station = self.stations[idx]
            dist_km = _haversine(lat, lon, station.latitude, station.longitude)
            results.append((dist_km, station))

        results.sort(key=lambda x: x[0])
        return results


def build_spatial_index(db_path: Path) -> SpatialIndex:
    """Load stations from SQLite and build the KD-tree.
    Called once at server startup.

    Args:
        db_path (Path): _Path to the SQLite database file._

    Returns:
        A ready-to-use SpatialIndex instance.
    Raises:
        FileNotFoundError: _If the database file does not exist._
        ValueError: _If the database contains no stations with coordinates._
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # access columns by name

    # Only load stations that have valid coordinates
    # (stations without lat/lon cannot be indexed)
    rows = conn.execute("""
        SELECT 
            id, latitude, longitude, 
            postcode, address, city, 
            price_gazole, price_sp95, price_sp98, 
            price_e10, price_e85, price_gplc 
        FROM stations 
        WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL                  
    """).fetchall()
    conn.close()

    if not rows:
        raise ValueError("No stations with valid coordinates found in database.")

    # Build parallel arrays: coordinates matrix + station list
    stations: list[Station] = []
    coords: list[tuple[float, float]] = []

    for row in rows:
        stations.append(
            Station(
                id=row["id"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                postcode=row["postcode"],
                city=row["city"],
                address=row["address"],
                price_gazole=row["price_gazole"],
                price_sp95=row["price_sp95"],
                price_sp98=row["price_sp98"],
                price_e10=row["price_e10"],
                price_e85=row["price_e85"],
                price_gplc=row["price_gplc"],
            )
        )
        coords.append((row["latitude"], row["longitude"]))

    # scipy KDTree expects a 2D array of shape (n_points, n_dims)
    coord_array = np.array(coords, dtype=np.float64())
    tree = KDTree(coord_array)

    return SpatialIndex(tree=tree, stations=stations)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two points (decimal degrees).
    Return distance in km.

    Args:
        lat1 (float): _description_
        lon1 (float): _description_
        lat2 (float): _description_
        lon2 (float): _description_

    Returns:
        float: _description_
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))
