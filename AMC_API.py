import argparse
import copy
import glob
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_LOCATION = "Charlotte, North Carolina, United States"
RAW_PATTERN = "showtime_*.json"
OUTPUT_DIR = Path("data")
MONTH_DAYS = 35


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_theater_name(path: str) -> str:
    name = Path(path).stem
    if name.startswith("showtime_"):
        return name[len("showtime_"):]
    return name


def fetch_theater_showtimes(theater_name: str, location: str = DEFAULT_LOCATION):
    import serpapi

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY environment variable is not set.")

    params = {
        "q": theater_name,
        "location": location,
        "hl": "en",
        "gl": "us",
        "api_key": api_key,
    }

    results = serpapi.search(params).as_dict()
    if "showtimes" not in results:
        raise RuntimeError(f"No showtimes found for {theater_name}.")

    return results["showtimes"]


def save_raw_showtimes(theater_name: str, showtimes):
    output = Path(f"showtime_{theater_name}.json")
    with output.open("w", encoding="utf-8") as file:
        json.dump(showtimes, file, indent=2)


def normalize_day_entries(raw_days, anchor: date):
    normalized = []
    for offset, raw in enumerate(raw_days):
        current_date = anchor + timedelta(days=offset)
        item = copy.deepcopy(raw)
        item["iso_date"] = current_date.isoformat()
        item["display_date"] = current_date.strftime("%b %-d")
        item["weekday"] = current_date.strftime("%a")
        item["day"] = "Today" if offset == 0 else ("Tomorrow" if offset == 1 else item.get("weekday", current_date.strftime("%a")))
        item["is_projected"] = False
        normalized.append(item)

    return normalized


def expand_to_month(normalized_week, anchor: date, days: int = MONTH_DAYS):
    if not normalized_week:
        return []

    expanded = []
    for offset in range(days):
        current_date = anchor + timedelta(days=offset)
        template = copy.deepcopy(normalized_week[offset % len(normalized_week)])

        template["iso_date"] = current_date.isoformat()
        template["display_date"] = current_date.strftime("%b %-d")
        template["weekday"] = current_date.strftime("%a")
        template["day"] = "Today" if offset == 0 else ("Tomorrow" if offset == 1 else current_date.strftime("%a"))
        template["is_projected"] = offset >= len(normalized_week)

        expanded.append(template)

    return expanded


def compute_week_ranges(anchor: date, days: int = MONTH_DAYS):
    ranges = []
    offset = 0
    while offset < days:
        start = anchor + timedelta(days=offset)
        end = min(anchor + timedelta(days=days - 1), start + timedelta(days=6))
        ranges.append(
            {
                "index": len(ranges),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": f"{start.strftime('%b %-d')} - {end.strftime('%b %-d')}",
            }
        )
        offset += 7

    return ranges


def build_monthly_payload(theater_name: str, raw_days, anchor: date, days: int = MONTH_DAYS):
    normalized = normalize_day_entries(raw_days[:7], anchor)
    expanded_days = expand_to_month(normalized, anchor, days=days)

    return {
        "theater": theater_name,
        "slug": slugify(theater_name),
        "generated_at": datetime.now().isoformat(),
        "anchor_date": anchor.isoformat(),
        "horizon_days": days,
        "week_ranges": compute_week_ranges(anchor, days=days),
        "days": expanded_days,
    }


def build_monthly_files(anchor: date, days: int = MONTH_DAYS):
    OUTPUT_DIR.mkdir(exist_ok=True)

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "anchor_date": anchor.isoformat(),
        "horizon_days": days,
        "theaters": [],
    }

    for path in sorted(glob.glob(RAW_PATTERN)):
        theater_name = parse_theater_name(path)
        with open(path, "r", encoding="utf-8") as file:
            raw_days = json.load(file)

        payload = build_monthly_payload(theater_name, raw_days, anchor=anchor, days=days)
        output_path = OUTPUT_DIR / f"{payload['slug']}.json"

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        manifest["theaters"].append(
            {
                "name": theater_name,
                "slug": payload["slug"],
                "path": str(output_path),
            }
        )

    manifest_path = OUTPUT_DIR / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    return manifest


def refresh_raw_theaters(theaters, location: str):
    for theater in theaters:
        showtimes = fetch_theater_showtimes(theater, location=location)
        save_raw_showtimes(theater, showtimes)


def parse_args():
    parser = argparse.ArgumentParser(description="AMC showtimes data tool")
    parser.add_argument(
        "--refresh-raw",
        action="store_true",
        help="Fetch fresh 7-day snapshots from SerpApi before generating monthly files.",
    )
    parser.add_argument(
        "--theater",
        action="append",
        default=[],
        help="Theater name to refresh (can be used multiple times).",
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_LOCATION,
        help="Google location for SerpApi searches.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=MONTH_DAYS,
        help="Number of forward days to expand from the snapshot anchor date.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    anchor = date.today()

    if args.refresh_raw:
        if not args.theater:
            raise RuntimeError("--refresh-raw requires at least one --theater value.")
        refresh_raw_theaters(args.theater, location=args.location)

    manifest = build_monthly_files(anchor=anchor, days=args.days)
    print(
        f"Built monthly files for {len(manifest['theaters'])} theaters "
        f"into {OUTPUT_DIR}/ (anchor={manifest['anchor_date']}, days={args.days})."
    )


if __name__ == "__main__":
    main()
