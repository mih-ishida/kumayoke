import csv
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
MASTER_CSV_PATH = ROOT / "phase3_internal_table" / "bifue-camp_bear_sightings_master.csv"
OUTPUT_CSV_PATH = ROOT / "phase4_map" / "bifue-camp_map_review_candidates.csv"
NOTES_PATH = ROOT / "phase4_map" / "bifue-camp_map_review_notes.md"
TARGET_SCOPE = "美笛近接"
EXPECTED_COUNT = 13

OUTPUT_COLUMNS = [
    "source_year",
    "record_no",
    "date_text",
    "location_text",
    "category_text",
    "body_text",
    "pin_label_draft",
    "matched_keywords",
    "map_search_query",
    "google_maps_search_url",
    "map_review_status",
    "map_review_note",
    "confirmed_location_memo",
]


def read_master_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def build_map_search_query(location_text: str) -> str:
    location_text = location_text.strip()
    if not location_text:
        return "北海道 千歳市 美笛"
    if "北海道" in location_text:
        return location_text
    if "千歳市" in location_text or "美笛" in location_text:
        return f"北海道 {location_text}"
    return f"北海道 千歳市 美笛 {location_text}"


def build_google_maps_search_url(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote(query, safe='')}"


def build_output_rows(master_rows):
    rows = []
    for row in master_rows:
        if row.get("relation_scope", "").strip() != TARGET_SCOPE:
            continue
        query = build_map_search_query(row.get("location_text", ""))
        rows.append(
            {
                "source_year": row.get("source_year", ""),
                "record_no": row.get("record_no", ""),
                "date_text": row.get("date_text", ""),
                "location_text": row.get("location_text", ""),
                "category_text": row.get("category_text", ""),
                "body_text": row.get("body_text", ""),
                "pin_label_draft": row.get("pin_label_draft", ""),
                "matched_keywords": row.get("matched_keywords", ""),
                "map_search_query": query,
                "google_maps_search_url": build_google_maps_search_url(query),
                "map_review_status": "未確認",
                "map_review_note": "",
                "confirmed_location_memo": "",
            }
        )
    return rows


def write_output_csv(rows):
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_notes(input_row_count: int, output_row_count: int):
    execution_date = date.today().isoformat()
    count_match = output_row_count == EXPECTED_COUNT
    warning = "" if count_match else f"- warning: expected {EXPECTED_COUNT} rows but got {output_row_count}\n"
    lines = [
        "# 美笛キャンプ場 地図確認候補メモ",
        "",
        f"- execution date: {execution_date}",
        f"- input CSV path: {MASTER_CSV_PATH}",
        f"- output CSV path: {OUTPUT_CSV_PATH}",
        f"- selected relation_scope: {TARGET_SCOPE}",
        f"- input row count: {input_row_count}",
        f"- output row count: {output_row_count}",
        f"- expected count 13 matched: {'yes' if count_match else 'no'}",
    ]
    if warning:
        lines.append(warning.rstrip())
    lines.extend(
        [
            "",
            "## 注意",
            "- Google Maps URL は検索リンクのみであり、確定座標ではない。",
            "- Phase 4 の地図画像作成前に人手レビューが必要。",
            "- このタスクでは公開地図 inclusion は最終確定していない。",
            "- Phase 4 の画像生成はまだ開始していない。",
        ]
    )
    NOTES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    master_rows = read_master_rows(MASTER_CSV_PATH)
    output_rows = build_output_rows(master_rows)
    write_output_csv(output_rows)
    write_notes(len(master_rows), len(output_rows))

    all_unconfirmed = all(row["map_review_status"] == "未確認" for row in output_rows)
    all_urls = all(row["google_maps_search_url"].startswith("https://www.google.com/maps/search/?api=1&query=") for row in output_rows)

    print(f"input_master_csv_row_count={len(master_rows)}")
    print(f"output_map_review_candidate_row_count={len(output_rows)}")
    print(f"expected_count_13={'yes' if len(output_rows) == EXPECTED_COUNT else 'no'}")
    print(f"all_map_review_status_unconfirmed={'yes' if all_unconfirmed else 'no'}")
    print(f"all_google_maps_search_url_generated={'yes' if all_urls else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
