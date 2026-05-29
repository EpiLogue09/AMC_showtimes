import argparse
import copy
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

DEFAULT_LOCATION = "Charlotte, North Carolina, United States"
OUTPUT_DIR = Path("data")
MONTH_DAYS = 35
QUERY_WEEK_STEP = 7
DEFAULT_THEATERS = [
    "AMC Carolina Pavilion 22",
    "AMC Concord Mills 24",
    "AMC North Lake 14",
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def raw_filename_for_theater(theater_name: str) -> Path:
    return Path(f"showtime_{theater_name}.json")


def parse_month_day(value: str, reference: date):
    if not value:
        return None

    normalized = value.replace(",", "").strip()
    for fmt in ("%b %d", "%B %d"):
        try:
            parsed = datetime.strptime(normalized, fmt).date().replace(year=reference.year)
            if parsed < reference - timedelta(days=31):
                parsed = parsed.replace(year=reference.year + 1)
            return parsed
        except ValueError:
            continue

    return None


def infer_iso_date(day_entry, *, anchor: date, index: Optional[int], allow_relative: bool):
    iso_text = day_entry.get("iso_date")
    if iso_text:
        try:
            return datetime.strptime(iso_text, "%Y-%m-%d").date()
        except ValueError:
            pass

    parsed_from_date = parse_month_day(day_entry.get("date"), reference=anchor)
    if parsed_from_date:
        return parsed_from_date

    if not allow_relative:
        return None

    day_label = (day_entry.get("day") or "").strip().lower()
    if day_label == "today":
        return anchor
    if day_label == "tomorrow":
        return anchor + timedelta(days=1)

    if index is not None:
        return anchor + timedelta(days=index)

    return None


def movie_count(day_entry):
    movies = day_entry.get("movies") or day_entry.get("theaters") or []
    return len(movies)


def normalize_day_entry(day_entry, iso: date):
    item = copy.deepcopy(day_entry)
    item["iso_date"] = iso.isoformat()
    item["weekday"] = iso.strftime("%a")
    item["date"] = item.get("date") or iso.strftime("%b %-d")
    return item


def fetch_showtimes_for_query(query: str, location: str = DEFAULT_LOCATION):
    import serpapi

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY environment variable is not set.")

    params = {
        "q": query,
        "location": location,
        "hl": "en",
        "gl": "us",
        "no_cache": "true",
        "api_key": api_key,
    }

    results = serpapi.search(params).as_dict()
    return results.get("showtimes", [])


def collect_extended_showtimes(theater_name: str, *, location: str, anchor: date, days: int):
    day_map = {}

    queries = [(theater_name, anchor, True)]
    for offset in range(QUERY_WEEK_STEP, days, QUERY_WEEK_STEP):
        target = anchor + timedelta(days=offset)
        hint_query = f"{theater_name} showtimes {target.strftime('%B %-d %Y')}"
        queries.append((hint_query, target, False))

    for query, query_anchor, allow_relative in queries:
        raw_days = fetch_showtimes_for_query(query=query, location=location)
        for index, entry in enumerate(raw_days):
            inferred = infer_iso_date(
                entry,
                anchor=query_anchor,
                index=index if allow_relative else None,
                allow_relative=allow_relative,
            )
            if not inferred:
                continue
            if inferred < anchor or inferred > anchor + timedelta(days=days - 1):
                continue

            normalized = normalize_day_entry(entry, inferred)
            key = inferred.isoformat()
            if key not in day_map or movie_count(normalized) > movie_count(day_map[key]):
                day_map[key] = normalized

    return [day_map[key] for key in sorted(day_map.keys())]


def save_raw_showtimes(theater_name: str, showtimes):
    output = Path(f"showtime_{theater_name}.json")
    with output.open("w", encoding="utf-8") as file:
        json.dump(showtimes, file, indent=2)


def normalize_days_from_raw(raw_days, anchor: date, days: int):
    normalized = []
    for index, raw in enumerate(raw_days):
        inferred = infer_iso_date(raw, anchor=anchor, index=index, allow_relative=True)
        if not inferred:
            continue
        if inferred < anchor or inferred > anchor + timedelta(days=days - 1):
            continue

        normalized.append(normalize_day_entry(raw, inferred))

    normalized.sort(key=lambda item: item["iso_date"])

    unique = {}
    for item in normalized:
        key = item["iso_date"]
        if key not in unique or movie_count(item) > movie_count(unique[key]):
            unique[key] = item

    return [unique[key] for key in sorted(unique.keys())]


def compute_week_ranges(days_data):
    ranges = []
    if not days_data:
        return ranges

    sorted_dates = [
        datetime.strptime(day_item["iso_date"], "%Y-%m-%d").date()
        for day_item in sorted(days_data, key=lambda item: item["iso_date"])
    ]

    for index, start_idx in enumerate(range(0, len(sorted_dates), 7)):
        chunk = sorted_dates[start_idx : start_idx + 7]
        start = chunk[0]
        end = chunk[-1]
        ranges.append(
            {
                "index": index,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": f"{start.strftime('%b %-d')} - {end.strftime('%b %-d')}",
            }
        )

    return ranges


def build_monthly_payload(theater_name: str, raw_days, anchor: date, days: int = MONTH_DAYS):
    normalized_days = normalize_days_from_raw(raw_days, anchor=anchor, days=days)

    return {
        "theater": theater_name,
        "slug": slugify(theater_name),
        "generated_at": datetime.now().isoformat(),
        "anchor_date": anchor.isoformat(),
        "horizon_days": days,
        "week_ranges": compute_week_ranges(normalized_days),
        "days": normalized_days,
    }


def build_monthly_files(theaters, anchor: date, days: int = MONTH_DAYS):
    OUTPUT_DIR.mkdir(exist_ok=True)
    built = []

    for theater_name in theaters:
        path = raw_filename_for_theater(theater_name)
        if not path.exists():
            print(f"Skipping missing raw file: {path}")
            continue

        with open(path, "r", encoding="utf-8") as file:
            raw_days = json.load(file)

        payload = build_monthly_payload(theater_name, raw_days, anchor=anchor, days=days)
        output_path = OUTPUT_DIR / f"{payload['slug']}.json"

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        built.append(
            {
                "name": theater_name,
                "slug": payload["slug"],
                "path": str(output_path),
                "days_loaded": len(payload["days"]),
            }
        )

    return built


def refresh_raw_theaters(theaters, *, location: str, anchor: date, days: int):
    for theater in theaters:
        showtimes = collect_extended_showtimes(
            theater,
            location=location,
            anchor=anchor,
            days=days,
        )
        save_raw_showtimes(theater, showtimes)


def parse_args():
    parser = argparse.ArgumentParser(description="AMC showtimes data tool")
    parser.add_argument(
        "--refresh-raw",
        action="store_true",
        help="Fetch fresh showtimes from SerpApi before generating UI data.",
    )
    parser.add_argument(
        "--theater",
        action="append",
        default=[],
        help="Theater name to include (can be used multiple times).",
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
        help="Maximum number of forward days to collect.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    anchor = date.today()
    target_theaters = args.theater or DEFAULT_THEATERS

    if args.refresh_raw:
        refresh_raw_theaters(
            target_theaters,
            location=args.location,
            anchor=anchor,
            days=args.days,
        )

    built = build_monthly_files(target_theaters, anchor=anchor, days=args.days)
    print(
        f"Built UI files for {len(built)} theaters into {OUTPUT_DIR}/ "
        f"(anchor={anchor.isoformat()}, days={args.days})."
    )


if __name__ == "__main__":
    main()
