import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
RAW_CSV_PATH = ROOT / "phase2_source_research" / "raw_tables" / "chitose-city_bear-sightings_raw.csv"
MASTER_CSV_PATH = ROOT / "phase3_internal_table" / "bifue-camp_bear_sightings_master.csv"
INCLUSION_NOTES_PATH = ROOT / "phase3_internal_table" / "bifue-camp_inclusion_notes.md"

MASTER_COLUMNS = [
    "source_year",
    "record_no",
    "date_text",
    "location_text",
    "category_text",
    "body_text",
    "source_url",
    "raw_html_file",
    "relation_scope",
    "matched_keywords",
    "initial_inclusion_suggestion",
    "suggestion_reason",
    "pin_label_draft",
    "review_status",
    "reviewer_note",
]

HIGH_RELEVANCE_KEYWORDS = [
    "美笛キャンプ場",
    "美笛トンネル",
    "美笛橋",
    "美笛",
]

LAKE_AREA_KEYWORDS = [
    "支笏湖温泉",
    "支笏湖",
    "幌美内",
    "支寒内",
    "モラップ",
    "奥潭",
    "ポロピナイ",
    "丸駒",
    "風不死岳",
    "恵庭岳",
    "紋別岳",
    "支笏小橋",
]

ROUTE_GUIDE_KEYWORDS = [
    "水明郷",
    "西森",
    "道道支笏湖公園線",
    "道道支笏湖線",
]

BROAD_ROAD_KEYWORDS = [
    "国道276号線",
    "国道276号",
    "国道453号線",
    "国道453号",
    "千歳橋",
]

ALL_KEYWORDS = HIGH_RELEVANCE_KEYWORDS + LAKE_AREA_KEYWORDS + ROUTE_GUIDE_KEYWORDS + BROAD_ROAD_KEYWORDS


def normalize_digits(value: str) -> str:
    return value.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def read_raw_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def find_matched_keywords(row: Dict[str, str]) -> List[str]:
    haystack = f"{row.get('location_text', '')}\n{row.get('body_text', '')}"
    matched: List[str] = []
    for keyword in ALL_KEYWORDS:
        if keyword in haystack and keyword not in matched:
            matched.append(keyword)
    return matched


def classify_relation(matched_keywords: List[str]) -> Tuple[str, str, str]:
    high = [kw for kw in matched_keywords if kw in HIGH_RELEVANCE_KEYWORDS]
    lake = [kw for kw in matched_keywords if kw in LAKE_AREA_KEYWORDS]
    route = [kw for kw in matched_keywords if kw in ROUTE_GUIDE_KEYWORDS]
    broad = [kw for kw in matched_keywords if kw in BROAD_ROAD_KEYWORDS]

    if high:
        return (
            "美笛近接",
            "公開候補",
            f"美笛関連キーワード一致: {', '.join(high)}",
        )
    if lake:
        return (
            "支笏湖周辺",
            "周辺参考候補",
            f"支笏湖周辺キーワード一致: {', '.join(lake)}",
        )
    if route:
        return (
            "支笏湖導線",
            "周辺参考候補",
            f"支笏湖導線キーワード一致: {', '.join(route)}",
        )
    if broad:
        return (
            "要確認",
            "要確認",
            f"広域道路・橋梁キーワード一致: {', '.join(broad)}",
        )
    return ("要確認", "要確認", "分類ルールに十分一致しないため要確認")


def build_pin_label_draft(source_year: str, date_text: str, category_text: str) -> Tuple[str, str]:
    normalized = normalize_digits(date_text)
    month_match = re.search(r"([0-9]{1,2})月", normalized)
    if not month_match:
        return "", "month could not be parsed from date_text"
    month = month_match.group(1).zfill(2)
    category = category_text.strip()
    if not category:
        return "", "category_text is blank"
    return f"{source_year}.{month} {category}", ""


def build_master_rows(raw_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    master_rows: List[Dict[str, str]] = []
    for row in raw_rows:
        matched_keywords = find_matched_keywords(row)
        if not matched_keywords:
            continue

        relation_scope, suggestion, reason = classify_relation(matched_keywords)
        pin_label_draft, note = build_pin_label_draft(
            source_year=row["source_year"],
            date_text=row["date_text"],
            category_text=row["category_text"],
        )

        master_rows.append(
            {
                "source_year": row["source_year"],
                "record_no": row["record_no"],
                "date_text": row["date_text"],
                "location_text": row["location_text"],
                "category_text": row["category_text"],
                "body_text": row["body_text"],
                "source_url": row["source_url"],
                "raw_html_file": row["raw_html_file"],
                "relation_scope": relation_scope,
                "matched_keywords": ", ".join(matched_keywords),
                "initial_inclusion_suggestion": suggestion,
                "suggestion_reason": reason,
                "pin_label_draft": pin_label_draft,
                "review_status": "未確認",
                "reviewer_note": note,
            }
        )
    return master_rows


def write_master_csv(rows: List[Dict[str, str]]) -> None:
    with MASTER_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MASTER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def top_keywords_summary(rows: List[Dict[str, str]], limit: int = 10) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in rows:
        for keyword in [item.strip() for item in row["matched_keywords"].split(",") if item.strip()]:
            counter[keyword] += 1
    return counter.most_common(limit)


def write_inclusion_notes(raw_row_count: int, master_rows: List[Dict[str, str]]) -> None:
    execution_date = date.today().isoformat()
    scope_counter = Counter(row["relation_scope"] for row in master_rows)
    suggestion_counter = Counter(row["initial_inclusion_suggestion"] for row in master_rows)
    keyword_summary = top_keywords_summary(master_rows)

    lines = [
        "# 美笛キャンプ場 掲載可否メモ",
        "",
        "## 使い方",
        "",
        "- Phase 2 で集めた raw テーブルをもとに判断する",
        "- Bifue / 支笏湖周辺との関係を判断する",
        "- 公開地図に載せるかどうか",
        "- 載せない場合の理由",
        "- 表示簡素化の判断",
        "",
        "このメモでは、公開地図に載せるかどうかと、その理由を人手で整理する。",
        "",
        "## 実行メモ",
        "",
        f"- execution date: {execution_date}",
        f"- input CSV path: {RAW_CSV_PATH}",
        f"- input row count: {raw_row_count}",
        f"- candidate row count: {len(master_rows)}",
        "",
        "## count by relation_scope",
    ]

    for key in ["美笛近接", "支笏湖周辺", "支笏湖導線", "要確認"]:
        lines.append(f"- {key}: {scope_counter.get(key, 0)}")

    lines.extend(["", "## count by initial_inclusion_suggestion"])
    for key in ["公開候補", "周辺参考候補", "要確認"]:
        lines.append(f"- {key}: {suggestion_counter.get(key, 0)}")

    lines.extend(["", "## top matched keywords summary"])
    if keyword_summary:
        for keyword, count in keyword_summary:
            lines.append(f"- {keyword}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## 注意",
            "- すべての suggestion は初期提案であり、review_status は未確認のまま扱う。",
            "- このタスクでは公開地図 inclusion は最終確定していない。",
            "- Phase 4 の地図生成は開始していない。",
            "",
            "## メモ",
            "",
            "未記入",
        ]
    )

    INCLUSION_NOTES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    raw_rows = read_raw_rows(RAW_CSV_PATH)
    master_rows = build_master_rows(raw_rows)
    write_master_csv(master_rows)
    write_inclusion_notes(raw_row_count=len(raw_rows), master_rows=master_rows)

    scope_counter = Counter(row["relation_scope"] for row in master_rows)
    suggestion_counter = Counter(row["initial_inclusion_suggestion"] for row in master_rows)
    unique_pairs = len({(row["source_year"], row["record_no"]) for row in master_rows}) == len(master_rows)
    all_unconfirmed = all(row["review_status"] == "未確認" for row in master_rows)
    pin_label_filled = sum(1 for row in master_rows if row["pin_label_draft"].strip())
    manual_check_rows = sum(1 for row in master_rows if row["reviewer_note"].strip())

    print(f"input_raw_csv_row_count={len(raw_rows)}")
    print(f"output_master_csv_row_count={len(master_rows)}")
    print(f"all_review_status_unconfirmed={'yes' if all_unconfirmed else 'no'}")
    print(f"source_year_record_no_unique={'yes' if unique_pairs else 'no'}")
    print(f"pin_label_draft_filled_count={pin_label_filled}")
    print(f"manual_check_rows={manual_check_rows}")
    for key in ["美笛近接", "支笏湖周辺", "支笏湖導線", "要確認"]:
        print(f"relation_scope_{key}={scope_counter.get(key, 0)}")
    for key in ["公開候補", "周辺参考候補", "要確認"]:
        print(f"inclusion_{key}={suggestion_counter.get(key, 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
