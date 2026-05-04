"""CLI entry point for the ingestion pipeline.

Usage:
    python scripts/ingest.py
    python scripts/ingest.py --db data/processed/stations.db --raw data/raw
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
import sys

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.ingestion import fetch, parse, store

date_str = datetime.now().strftime("%Y%m%d")
logging.basicConfig(
    # filename=f"./scripts/logs/{date_str}_myapp.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest fuel station data")
    parser.add_argument("--db", type=Path, default=Path("data/processed/stations.db"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    xml_path = fetch(args.raw)
    df = parse(xml_path)
    store(df, args.db)


if __name__ == "__main__":
    main()
