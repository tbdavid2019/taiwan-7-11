import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STORES_PATH = DATA_DIR / "seven_eleven_stores.json"
METADATA_PATH = DATA_DIR / "seven_eleven_stores_metadata.json"

PRIMARY_SOURCE = {
    "name": "7-11 store JSON",
    "url": "https://raw.githubusercontent.com/Minato1123/taiwan-cvs-map/main/src/assets/json/s_data.json",
    "reference_repo": "https://github.com/Minato1123/taiwan-cvs-map",
    "reference_script": "https://raw.githubusercontent.com/Minato1123/taiwan-cvs-map/main/scripts/fetch-711-mart-list.ts",
}
SUPPLEMENTAL_SOURCE = {
    "name": "7-11 stores.yaml",
    "url": "https://raw.githubusercontent.com/Cojad/taiwan-7Eleven-store/refs/heads/master/stores.yaml",
}

CITY_AREA_RE = re.compile(r"^(..[市縣])(..?[鄉鎮市區])")
YAML_KEY_RE = re.compile(r"^'(?P<store_id>\d+)':\s*$")


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def fetch_json(url: str):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_simple_yaml(text: str):
    stores = {}
    current_id = None
    current_record = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = YAML_KEY_RE.match(line)
        if match:
            current_id = match.group("store_id")
            current_record = {}
            stores[current_id] = current_record
            continue

        if current_record is None or not line.startswith("  "):
            continue

        stripped = line.strip()
        if ": " not in stripped:
            continue

        key, value = stripped.split(": ", 1)
        current_record[key] = value.strip()

    return stores


def split_city_area(address: str):
    if not address:
        return "", ""
    match = CITY_AREA_RE.match(address)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def normalize_primary_store(item, supplemental_map):
    store_id = str(item.get("id", "")).strip()
    supplemental = supplemental_map.get(store_id, {})

    name = (item.get("name") or "").strip()
    if name.endswith("門市"):
        name = name[:-2]
    name = supplemental.get("store") or name

    address = (item.get("address") or "").strip()
    address = supplemental.get("address") or address
    city, area = split_city_area(address)

    return {
        "id": store_id,
        "name": name,
        "address": address,
        "lat": float(item.get("lat", 0) or 0),
        "lng": float(item.get("lng", 0) or 0),
        "city": city or (item.get("city") or "").strip(),
        "area": area or (item.get("area") or "").strip(),
        "tel": (item.get("tel") or "").strip(),
        "service": sorted(item.get("service") or []),
        "source_flags": {
            "primary_json": True,
            "supplemental_yaml": bool(supplemental),
        },
    }


def build_output(primary_json, supplemental_map):
    stores = []
    for item in primary_json:
        normalized = normalize_primary_store(item, supplemental_map)
        if not normalized["id"] or not normalized["lat"] or not normalized["lng"]:
            continue
        stores.append(normalized)

    stores.sort(key=lambda item: item["id"])

    source_urls = [
        PRIMARY_SOURCE["url"],
        PRIMARY_SOURCE["reference_repo"],
        PRIMARY_SOURCE["reference_script"],
        SUPPLEMENTAL_SOURCE["url"],
    ]
    refreshed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    metadata = {
        "generated_at": refreshed_at,
        "counts": {
            "normalized_stores": len(stores),
            "primary_records": len(primary_json),
            "supplemental_records": len(supplemental_map),
        },
        "sources": [
            PRIMARY_SOURCE,
            SUPPLEMENTAL_SOURCE,
        ],
    }
    payload = {
        "generated_at": refreshed_at,
        "source_urls": source_urls,
        "stores": stores,
    }
    return payload, metadata


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    primary_json = fetch_json(PRIMARY_SOURCE["url"])
    supplemental_text = fetch_text(SUPPLEMENTAL_SOURCE["url"])
    supplemental_map = parse_simple_yaml(supplemental_text)

    payload, metadata = build_output(primary_json, supplemental_map)

    STORES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "stores_path": str(STORES_PATH),
                "metadata_path": str(METADATA_PATH),
                "generated_at": metadata["generated_at"],
                "counts": metadata["counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
