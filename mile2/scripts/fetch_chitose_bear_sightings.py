import csv
import re
import sys
import time
import argparse
from dataclasses import dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CATALOG = ROOT / "phase2_source_research" / "bifue-camp_source_catalog.md"
RAW_HTML_DIR = ROOT / "phase2_source_research" / "raw_html"
RAW_TABLES_DIR = ROOT / "phase2_source_research" / "raw_tables"
PARSE_NOTES_DIR = ROOT / "phase2_source_research" / "parse_notes"
RAW_CSV_PATH = RAW_TABLES_DIR / "chitose-city_bear-sightings_raw.csv"
PARSE_NOTES_PATH = PARSE_NOTES_DIR / "chitose-city_parse_notes.md"
SLEEP_SECONDS = 1.5

CSV_COLUMNS = [
    "source_group",
    "source_name",
    "source_url",
    "source_year",
    "record_no",
    "date_text",
    "location_text",
    "category_text",
    "body_text",
    "confirmed_date",
    "raw_html_file",
    "parse_note",
]


@dataclass
class SourceRow:
    source_name: str
    source_url: str
    target_year: str
    source_type: str
    fetch_target: str
    memo: str


class TableExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: List[List[str]] = []
        self._current_row: List[str] = []
        self._current_cell: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"th", "td"}:
            self._in_cell = True
            self._current_cell = []
        elif self._in_cell and tag == "br":
            self._current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._in_cell:
            text = _clean_text("".join(self._current_cell))
            self._current_row.append(text)
            self._current_cell = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if any(cell for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = []
            self._in_row = False
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = []
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


def _clean_text(value: str) -> str:
    value = unescape(value)
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t\u3000]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip(" \n")


def _strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return _clean_text(value)


def read_source_catalog(path: Path) -> List[SourceRow]:
    lines = path.read_text(encoding="utf-8").splitlines()
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 3:
        raise ValueError("source catalog markdown table was not found")

    header = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: List[SourceRow] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            continue
        data = dict(zip(header, cells))
        rows.append(
            SourceRow(
                source_name=data["source_name"],
                source_url=data["source_url"],
                target_year=data["target_year"],
                source_type=data["source_type"],
                fetch_target=data["fetch_target"],
                memo=data["memo"],
            )
        )
    return rows


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "kumayoke-mile2-phase2/1.0 (+public-information-check)",
        },
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
    return raw.decode(encoding, errors="replace")


def save_html(source: SourceRow, html: str, fetched_date: str) -> str:
    file_name = f"chitose-city_{source.target_year}_{fetched_date}.html"
    path = RAW_HTML_DIR / file_name
    path.write_text(html, encoding="utf-8")
    return file_name


def header_key(header: str) -> str:
    text = _clean_text(header)
    if re.search(r"^(no|No|NO|番号)", text):
        return "record_no"
    if "日時" in text or "月日" in text or "日付" in text:
        return "date_text"
    if "場所" in text or "地区" in text or "地域" in text:
        return "location_text"
    if "分類" in text or "種別" in text or "区分" in text:
        return "category_text"
    if "内容" in text or "状況" in text or "詳細" in text or "備考" in text:
        return "body_text"
    return ""


def parse_page(source: SourceRow, html: str, raw_html_file: str, confirmed_date: str) -> Tuple[List[Dict[str, str]], List[str]]:
    parser = TableExtractor()
    parser.feed(html)

    output_rows: List[Dict[str, str]] = []
    page_notes: List[str] = []

    if not parser.tables:
        fallback_rows, fallback_notes = parse_page_by_headings(source, html, raw_html_file, confirmed_date)
        return fallback_rows, fallback_notes

    for table_index, table in enumerate(parser.tables, start=1):
        if len(table) < 2:
            continue

        headers = table[0]
        keys = [header_key(header) for header in headers]
        usable_keys = [key for key in keys if key]
        if not usable_keys:
            page_notes.append(f"{source.target_year}: table {table_index} headers were not recognized")
            continue

        for row_index, cells in enumerate(table[1:], start=1):
            record = {
                "source_group": "千歳市",
                "source_name": source.source_name,
                "source_url": source.source_url,
                "source_year": source.target_year,
                "record_no": "",
                "date_text": "",
                "location_text": "",
                "category_text": "",
                "body_text": "",
                "confirmed_date": confirmed_date,
                "raw_html_file": raw_html_file,
                "parse_note": "",
            }

            local_notes: List[str] = []
            for idx, cell in enumerate(cells):
                key = keys[idx] if idx < len(keys) else ""
                if not key:
                    continue
                if key == "body_text" and record[key]:
                    record[key] = f"{record[key]}\n{cell}".strip()
                else:
                    record[key] = cell.strip()

            if not record["record_no"]:
                record["record_no"] = str(row_index)
                local_notes.append("record_no was assigned from row order")

            if not record["date_text"]:
                local_notes.append("date_text could not be parsed reliably")
            if not record["location_text"]:
                local_notes.append("location_text could not be parsed reliably")

            if local_notes:
                record["parse_note"] = "; ".join(local_notes)
            output_rows.append(record)

    if not output_rows:
        fallback_rows, fallback_notes = parse_page_by_headings(source, html, raw_html_file, confirmed_date)
        return fallback_rows, fallback_notes
    return output_rows, page_notes


def infer_category_text(body_text: str) -> str:
    if "足跡" in body_text:
        return "足跡"
    if "フン" in body_text:
        return "フン"
    if "痕跡" in body_text:
        return "痕跡"
    if "食害" in body_text:
        return "食害"
    if "被害" in body_text:
        return "被害"
    if "目撃" in body_text:
        return "目撃"
    return ""


def extract_location_text(body_text: str) -> Tuple[str, str]:
    patterns = [
        (
            r"、((?:千歳市)?.+?)(?=で[東西南北].*?(?:横断する|移動する)(?:クマ|ヒグマ)の)",
            "directional movement before bear sighting phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=で.*?道路を横断する(?:クマ|ヒグマ)の)",
            "road crossing before bear sighting phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=で.*?道路脇にいる(?:クマ|ヒグマ)の)",
            "roadside sighting phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=を[東西南北].*?横断する(?:クマ|ヒグマ)の)",
            "location before directional crossing with を phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=で.*?へ移動する(?:クマ|ヒグマ)の)",
            "generic movement phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=にいる(?:クマ|ヒグマ)の)",
            "bear staying phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=において(?:クマ|ヒグマ)の)",
            "location with において phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=で.*?(?:クマ|ヒグマ)の(?:目撃情報|足跡|フン|痕跡|被害))",
            "direct location before bear phrase",
        ),
        (
            r"、((?:千歳市)?.+?)(?=でヒグマの(?:足跡|フン|痕跡))",
            "direct trace phrase",
        ),
    ]
    for pattern, note in patterns:
        match = re.search(pattern, body_text)
        if match:
            return _clean_text(match.group(1)), note
    return "", ""


def parse_page_by_headings(source: SourceRow, html: str, raw_html_file: str, confirmed_date: str) -> Tuple[List[Dict[str, str]], List[str]]:
    notes: List[str] = []
    rows: List[Dict[str, str]] = []

    matches = list(
        re.finditer(
            r"<h2>\s*目撃情報\s*([0-9０-９]+)\s*</h2>(.*?)(?=<h2>|<h4>|</main>|</body>)",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    if not matches:
        notes.append(f"{source.target_year}: heading-based entries were not found")
        return rows, notes

    for match in matches:
        record_no = _clean_text(match.group(1))
        block = match.group(2)
        paragraphs = re.findall(r"<p>(.*?)</p>", block, flags=re.IGNORECASE | re.DOTALL)
        body_text = _clean_text("\n".join(_strip_tags(p) for p in paragraphs if _strip_tags(p)))
        if not body_text:
            body_text = _strip_tags(block)

        date_match = re.search(r"^(.+?頃)", body_text)
        location_text, location_parse_note = extract_location_text(body_text)

        parse_note_parts: List[str] = ["parsed from heading/body pattern"]
        if not date_match:
            parse_note_parts.append("date_text could not be parsed reliably")
        if not location_text:
            parse_note_parts.append("location_text could not be parsed reliably")
        else:
            parse_note_parts.append(f"location extracted by {location_parse_note}")

        rows.append(
            {
                "source_group": "千歳市",
                "source_name": source.source_name,
                "source_url": source.source_url,
                "source_year": source.target_year,
                "record_no": record_no,
                "date_text": _clean_text(date_match.group(1)) if date_match else "",
                "location_text": location_text,
                "category_text": infer_category_text(body_text),
                "body_text": body_text,
                "confirmed_date": confirmed_date,
                "raw_html_file": raw_html_file,
                "parse_note": "; ".join(parse_note_parts),
            }
        )

    notes.append(f"{source.target_year}: parsed from heading/body pattern")
    return rows, notes


def write_raw_csv(rows: List[Dict[str, str]]) -> None:
    with RAW_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def count_blank_locations(rows: List[Dict[str, str]]) -> int:
    return sum(1 for row in rows if not row["location_text"].strip())


def read_existing_csv_stats() -> Tuple[Optional[int], Optional[int]]:
    if not RAW_CSV_PATH.exists():
        return None, None
    with RAW_CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return len(rows), count_blank_locations(rows)


def write_parse_notes(
    execution_date: str,
    fetched_years: List[str],
    fetched_pages_count: int,
    raw_csv_row_count: int,
    uncertain_pages: List[str],
    before_row_count: Optional[int],
    before_blank_location_count: Optional[int],
    after_blank_location_count: int,
    parse_only: bool,
) -> None:
    note_lines = [
        "# 千歳市ヒグマ目撃情報 解析メモ",
        "",
        f"- execution date: {execution_date}",
        f"- fetched target years: {', '.join(fetched_years) if fetched_years else '(none)'}",
        f"- number of source pages fetched: {fetched_pages_count}",
        f"- raw CSV row count: {raw_csv_row_count}",
        f"- mode: {'parse-only' if parse_only else 'fetch-and-parse'}",
        "",
        "## parsing uncertainties",
    ]

    if uncertain_pages:
        note_lines.extend([f"- {item}" for item in uncertain_pages])
    else:
        note_lines.append("- none")

    note_lines.extend(
        [
            "",
            "## parser improvement",
            f"- parser improvement date: {execution_date}",
            "- added location extraction patterns for directional movement, road crossing, roadside sighting, direct sighting, and trace phrases",
            f"- before/after location_text blank count: {before_blank_location_count if before_blank_location_count is not None else '(none)'} -> {after_blank_location_count}",
            f"- before/after raw CSV row count: {before_row_count if before_row_count is not None else '(none)'} -> {raw_csv_row_count}",
            "- remaining limitations: 年ごとの差分や本文の表現揺れにより、一部の location_text は引き続き空欄の可能性がある",
            "",
            "## manual checks needed",
            "- 年ごとの表構造差分がないか確認すること",
            "- date_text / location_text / category_text / body_text の対応が自然か確認すること",
            "- Bifue relevance と public map inclusion judgment は Phase 3 で行うこと",
        ]
    )

    PARSE_NOTES_PATH.write_text("\n".join(note_lines) + "\n", encoding="utf-8")


def ensure_directories() -> None:
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    RAW_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    PARSE_NOTES_DIR.mkdir(parents=True, exist_ok=True)


def read_saved_html(target_year: str, fetched_date: str) -> Optional[Tuple[str, str]]:
    path = RAW_HTML_DIR / f"chitose-city_{target_year}_{fetched_date}.html"
    if path.exists():
        return path.read_text(encoding="utf-8"), path.name

    matches = sorted(RAW_HTML_DIR.glob(f"chitose-city_{target_year}_*.html"))
    if not matches:
        return None
    latest = matches[-1]
    return latest.read_text(encoding="utf-8"), latest.name


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch or parse Chitose City bear sighting pages for Mile2 Phase 2.")
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Regenerate raw CSV and parse notes from saved raw_html files without refetching public pages.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    ensure_directories()
    today = date.today().isoformat()
    sources = [row for row in read_source_catalog(SOURCE_CATALOG) if row.fetch_target.lower() == "yes"]
    before_row_count, before_blank_location_count = read_existing_csv_stats()

    all_rows: List[Dict[str, str]] = []
    fetched_years: List[str] = []
    uncertain_pages: List[str] = []
    fetched_pages_count = 0

    for index, source in enumerate(sources):
        if args.parse_only:
            saved = read_saved_html(source.target_year, today)
            if not saved:
                uncertain_pages.append(f"{source.target_year}: saved raw_html file was not found")
                continue
            html, raw_html_file = saved
        else:
            try:
                html = fetch_html(source.source_url)
            except HTTPError as exc:
                uncertain_pages.append(f"{source.target_year}: HTTP error {exc.code}")
                continue
            except URLError as exc:
                uncertain_pages.append(f"{source.target_year}: URL error {exc.reason}")
                continue
            except Exception as exc:  # pragma: no cover
                uncertain_pages.append(f"{source.target_year}: unexpected error {exc}")
                continue

            raw_html_file = save_html(source, html, today)

        rows, notes = parse_page(source, html, raw_html_file, today)
        all_rows.extend(rows)
        uncertain_pages.extend(notes)
        fetched_pages_count += 1
        fetched_years.append(source.target_year)

        if not args.parse_only and index < len(sources) - 1:
            time.sleep(SLEEP_SECONDS)

    if fetched_pages_count > 0:
        write_raw_csv(all_rows)
    after_blank_location_count = count_blank_locations(all_rows)
    write_parse_notes(
        execution_date=today,
        fetched_years=fetched_years,
        fetched_pages_count=fetched_pages_count,
        raw_csv_row_count=len(all_rows),
        uncertain_pages=uncertain_pages,
        before_row_count=before_row_count,
        before_blank_location_count=before_blank_location_count,
        after_blank_location_count=after_blank_location_count,
        parse_only=args.parse_only,
    )

    print(f"fetched_pages_count={fetched_pages_count}")
    print(f"raw_csv_created={'yes' if fetched_pages_count > 0 else 'no'}")
    print(f"raw_csv_row_count={len(all_rows)}")
    print(f"blank_location_count={after_blank_location_count}")
    print(f"mode={'parse-only' if args.parse_only else 'fetch-and-parse'}")
    print(f"parse_notes_path={PARSE_NOTES_PATH}")
    if fetched_pages_count > 0:
        print(f"raw_csv_path={RAW_CSV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
