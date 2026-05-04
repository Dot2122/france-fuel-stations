import logging
import sqlite3
import zipfile
import httpx
import io
import pandas as pd
from pathlib import Path
from lxml import etree

logger = logging.getLogger(__name__)

FEED_URL = "https://donnees.roulez-eco.fr/opendata/instantane"

FUEL_TYPES = ["Gazole", "SP95", "SP98", "E10", "E85", "GPLc"]

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS stations (
        id              TEXT PRIMARY KEY,
        postcode        TEXT,
        address         TEXT,
        city            TEXT,
        latitude        REAL NOT NULL,
        longitude       REAL NOT NULL,
        price_gazole    REAL,
        price_sp95      REAL,
        price_sp98      REAL,
        price_e10       REAL,
        price_e85       REAL,
        price_gplc      REAL,
        ingested        TEXT DEFAULT (datetime('now'))
    );
"""


def fetch(raw_dir: Path) -> Path:
    """Download the ZIP feed and extract the XML file into raw_dir.


    Args:
        raw_dir (Path): _description_

    Returns:
        Path: _description_
    """
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading feed from {FEED_URL}")
    response = httpx.get(FEED_URL, follow_redirects=True, timeout=30)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        # The ZIP contains a single XML file
        xml_filename = next(n for n in zf.namelist() if n.endswith(".xml"))
        zf.extract(xml_filename, raw_dir)
        xml_path = raw_dir / xml_filename

    logger.info(f"Extract XML to {xml_path}")
    return xml_path


def parse(xml_path: Path) -> pd.DataFrame:
    """Parse the XML feed into a clean DataFrame (one row per station)
    Coordinates are stored as integers in 1/100 000th of a degree
    (e.g. 4823451 → 48.23451°). We divide by 100_000 to get WGS84.
    Encoding is ISO-8859-1 — lxml handles it via the XML declaration.

    Args:
        xml_path (Path): _description_

    Returns:
        DataFrame: _description_
    """
    logger.info(f"Parsing {xml_path}")

    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    rows: list = []
    skipped: int = 0

    for pdv in root.findall("pdv"):  # pdv = "point de vente"
        lat_raw = pdv.get("latitude")
        lon_raw = pdv.get("longitude")

        # Skip stations with missing or zero coordinates
        if not lat_raw or not lon_raw:
            skipped += 1
            continue

        lat = int(float(lat_raw)) / 100_000
        lon = int(float(lon_raw)) / 100_000
        if lat == 0.0 or lon == 0.0:
            skipped += 1
            continue

        # Collect available fuel prices (missing prices stay as None)
        prices: dict[str, float] = {}
        for prix in pdv.findall("prix"):
            fuel = prix.get("nom")
            val = prix.get("valeur")
            if fuel in FUEL_TYPES and val:
                prices[f"price_{fuel.lower()}"] = float(val)

        address_el = pdv.find("adresse")
        ville_el = pdv.find("ville")

        row = {
            "id": pdv.get("id"),
            "postcode": pdv.get("cp"),
            "latitude": lat,
            "longitude": lon,
            "address": address_el.text.strip() if address_el is not None and address_el.text is not None else None,
            "city": ville_el.text.strip() if ville_el is not None and ville_el.text is not None else None,
            **{f"price_{ft.lower()}": prices.get(f"price_{ft.lower()}") for ft in FUEL_TYPES},
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"Parse {len(df)} stations ({skipped} skipped - missing/zero coords)")
    return df


def store(df: pd.DataFrame, db_path: Path) -> None:
    """Persist the stations DataFrame into SQLite (full refresh on each run)

    Args:
        df (pd.DataFrame): _description_
        db_path (Path): _description_
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS stations")
        conn.execute(CREATE_TABLE_SQL)

        df.to_sql(name="stations", con=conn, if_exists="append", index=False)

        count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        logger.info(f"Saved {count} stations to {db_path}")
