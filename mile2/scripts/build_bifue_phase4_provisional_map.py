import csv
import html
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV_PATH = ROOT / "phase4_map" / "bifue-camp_map_review_candidates.csv"
LANDMARK_CSV_PATH = ROOT / "phase4_map" / "bifue-camp_landmark_reference.csv"
OUTPUT_CSV_PATH = ROOT / "phase4_map" / "bifue-camp_provisional_coordinates.csv"
OUTPUT_HTML_PATH = ROOT / "phase4_map" / "bifue-camp_auto_pin_review.html"
OUTPUT_PLAN_PATH = ROOT / "phase4_map" / "bifue-camp_phase4_2_plan.md"

OUTPUT_COLUMNS = [
    "source_year",
    "record_no",
    "date_text",
    "location_text",
    "category_text",
    "body_text",
    "pin_label_draft",
    "matched_keywords",
    "landmark_key",
    "landmark_name",
    "auto_lat",
    "auto_lng",
    "coordinate_source",
    "coordinate_status",
    "confirmed_lat",
    "confirmed_lng",
    "confirmed_location_memo",
    "map_review_status",
    "map_review_note",
    "public_map_candidate",
]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_landmarks(path: Path) -> Dict[str, Dict[str, str]]:
    return {row["landmark_key"]: row for row in read_csv_rows(path)}


def choose_landmark_key(row: Dict[str, str]) -> str:
    location_text = row.get("location_text", "")
    matched_keywords = row.get("matched_keywords", "")
    haystack = f"{location_text}\n{matched_keywords}"

    if "美笛キャンプ場" in haystack:
        return "bifue_camp_gate"
    if "美笛橋" in haystack:
        return "bifue_bridge"
    if "美笛トンネル" in haystack:
        return "bifue_tunnel"
    if "千歳橋" in haystack:
        return "chitose_bridge"
    if "春笛橋" in haystack:
        return "harubue_bridge"
    if "道道支笏湖線" in haystack:
        return "route_78_bifue_area"
    if "国道276号線" in haystack or "国道276号" in haystack:
        return "route_276_bifue_area"
    return "unknown"


def build_output_rows(review_rows: List[Dict[str, str]], landmarks: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    output_rows: List[Dict[str, str]] = []
    for row in review_rows:
        landmark_key = choose_landmark_key(row)
        landmark = landmarks.get(landmark_key)

        if landmark:
            auto_lat = landmark["auto_lat"]
            auto_lng = landmark["auto_lng"]
            landmark_name = landmark["landmark_name"]
            coordinate_source = landmark["coordinate_source"]
            coordinate_status = "仮"
        else:
            auto_lat = ""
            auto_lng = ""
            landmark_name = ""
            coordinate_source = "unknown"
            coordinate_status = "要確認"

        output_rows.append(
            {
                "source_year": row.get("source_year", ""),
                "record_no": row.get("record_no", ""),
                "date_text": row.get("date_text", ""),
                "location_text": row.get("location_text", ""),
                "category_text": row.get("category_text", ""),
                "body_text": row.get("body_text", ""),
                "pin_label_draft": row.get("pin_label_draft", ""),
                "matched_keywords": row.get("matched_keywords", ""),
                "landmark_key": landmark_key,
                "landmark_name": landmark_name,
                "auto_lat": auto_lat,
                "auto_lng": auto_lng,
                "coordinate_source": coordinate_source,
                "coordinate_status": coordinate_status,
                "confirmed_lat": "",
                "confirmed_lng": "",
                "confirmed_location_memo": "",
                "map_review_status": "未確認",
                "map_review_note": "",
                "public_map_candidate": "",
            }
        )
    return output_rows


def write_output_csv(rows: List[Dict[str, str]]) -> None:
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def project_points(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    numeric_rows = [row for row in rows if row["auto_lat"] and row["auto_lng"]]
    lats = [float(row["auto_lat"]) for row in numeric_rows]
    lngs = [float(row["auto_lng"]) for row in numeric_rows]

    min_lat = min(lats)
    max_lat = max(lats)
    min_lng = min(lngs)
    max_lng = max(lngs)

    lat_span = max(max_lat - min_lat, 0.0001)
    lng_span = max(max_lng - min_lng, 0.0001)

    projected = []
    for row in rows:
        item = dict(row)
        if row["auto_lat"] and row["auto_lng"]:
            lat = float(row["auto_lat"])
            lng = float(row["auto_lng"])
            item["plot_x"] = 60 + ((lng - min_lng) / lng_span) * 680
            item["plot_y"] = 60 + ((max_lat - lat) / lat_span) * 420
        else:
            item["plot_x"] = None
            item["plot_y"] = None
        projected.append(item)
    return projected


def build_html(rows: List[Dict[str, str]]) -> str:
    data_json = json.dumps(rows, ensure_ascii=False)

    table_rows = []
    for index, row in enumerate(rows):
        table_rows.append(
            "<tr "
            f"data-row-index=\"{index}\" "
            f"data-landmark=\"{html.escape(row['landmark_key'])}\" "
            f"data-status=\"{html.escape(row['coordinate_status'])}\">"
            f"<td>{html.escape(row['source_year'])}</td>"
            f"<td>{html.escape(row['record_no'])}</td>"
            f"<td>{html.escape(row['pin_label_draft'])}</td>"
            f"<td>{html.escape(row['landmark_key'])}</td>"
            f"<td>{html.escape(row['coordinate_status'])}</td>"
            f"<td>{html.escape(row['location_text'])}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>美笛キャンプ場 仮置きピン確認</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  >
  <style>
    :root {{
      --bg: #f4efe4;
      --ink: #1f2c2a;
      --muted: #657069;
      --card: #fffdf9;
      --line: #d7cfbf;
      --pin: #b6422a;
      --accent: #2d6658;
      --soft: #e9e1d1;
    }}
    body {{
      margin: 0;
      font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #efe7d8 0, transparent 35%),
        linear-gradient(180deg, #f8f5ee 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .lead {{
      margin: 0 0 20px;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 20px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(20, 24, 18, 0.06);
    }}
    #map {{
      width: 100%;
      min-height: 620px;
      border-radius: 12px;
      border: 1px solid var(--line);
    }}
    .controls {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .controls label {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    select, button {{
      font: inherit;
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
    }}
    button {{
      cursor: pointer;
    }}
    .leaflet-popup-content {{
      line-height: 1.5;
      min-width: 240px;
    }}
    .popup-meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .legend {{
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
      margin-top: 12px;
      font-size: 14px;
      color: var(--muted);
    }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--pin);
      margin-right: 8px;
      vertical-align: middle;
    }}
    .legend .status-confirmed::before {{
      background: #43795d;
    }}
    .legend .status-review::before {{
      background: #bf8b2e;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid #e6ddce;
      padding: 8px 6px;
      vertical-align: top;
    }}
    th {{
      color: var(--accent);
      font-weight: 700;
    }}
    tbody tr {{
      cursor: pointer;
    }}
    tbody tr:hover,
    tbody tr.active {{
      background: #f4efe2;
    }}
    .note {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    @media (max-width: 900px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>美笛キャンプ場 仮置きピン確認</h1>
    <p class="lead">internal review only。各ピンは provisional coordinates であり、confirmed coordinates ではありません。public map inclusion も未確定です。</p>
    <div class="grid">
      <section class="card">
        <div class="controls">
          <label>status
            <select id="status-filter">
              <option value="all">all</option>
              <option value="仮">仮</option>
              <option value="要確認">要確認</option>
              <option value="確認済">確認済</option>
            </select>
          </label>
          <label>landmark
            <select id="landmark-filter">
              <option value="all">all</option>
            </select>
          </label>
          <button id="fit-all" type="button">全ピン表示</button>
        </div>
        <div id="map" role="img" aria-label="美笛近接 仮置きピン地図"></div>
        <div class="legend">
          <span>仮</span>
          <span class="status-review">要確認</span>
          <span class="status-confirmed">確認済（将来用）</span>
        </div>
        <p class="note">Leaflet は CDN 読み込み、base map は 国土地理院 淡色地図です。browser runtime のネットワーク接続が必要です。auto_lat / auto_lng は internal review 用の review-start coordinates で、確定地点ではありません。</p>
      </section>
      <section class="card">
        <table>
          <thead>
            <tr>
              <th>year</th>
              <th>record</th>
              <th>label</th>
              <th>landmark</th>
              <th>status</th>
              <th>location</th>
            </tr>
          </thead>
          <tbody>
            {''.join(table_rows)}
          </tbody>
        </table>
      </section>
    </div>
    <script type="application/json" id="review-data">{html.escape(data_json)}</script>
    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script>
      const reviewRows = JSON.parse(document.getElementById('review-data').textContent);
      const map = L.map('map', {{ zoomControl: true }}).setView([42.6996, 141.3098], 14);

      const paleLayer = L.tileLayer(
        'https://cyberjapandata.gsi.go.jp/xyz/pale/{{z}}/{{x}}/{{y}}.png',
        {{
          maxZoom: 18,
          attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">地理院タイル</a>'
        }}
      ).addTo(map);

      const stdLayer = L.tileLayer(
        'https://cyberjapandata.gsi.go.jp/xyz/std/{{z}}/{{x}}/{{y}}.png',
        {{
          maxZoom: 18,
          attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">地理院タイル</a>'
        }}
      );

      L.control.layers(
        {{ '淡色地図': paleLayer, '標準地図': stdLayer }},
        {{}},
        {{ position: 'topright', collapsed: true }}
      ).addTo(map);

      const statusColor = {{
        '仮': '#b6422a',
        '要確認': '#bf8b2e',
        '確認済': '#43795d'
      }};

      const markers = [];
      const tbodyRows = Array.from(document.querySelectorAll('tbody tr'));
      const landmarkFilter = document.getElementById('landmark-filter');
      const statusFilter = document.getElementById('status-filter');

      const landmarkKeys = [...new Set(reviewRows.map(row => row.landmark_key).filter(Boolean))].sort();
      for (const key of landmarkKeys) {{
        const option = document.createElement('option');
        option.value = key;
        option.textContent = key;
        landmarkFilter.appendChild(option);
      }}

      function popupHtml(row) {{
        return `
          <div>
            <strong>${{row.pin_label_draft}}</strong><br>
            <span class="popup-meta">source_year: ${{row.source_year}} / record_no: ${{row.record_no}}</span><br>
            <span class="popup-meta">landmark_key: ${{row.landmark_key}} / coordinate_status: ${{row.coordinate_status}}</span>
            <hr>
            <div>${{row.location_text}}</div>
            <p class="popup-meta">この座標は provisional / internal review 用であり、confirmed coordinates ではありません。</p>
          </div>
        `;
      }}

      function highlightRow(index) {{
        tbodyRows.forEach((tr, i) => tr.classList.toggle('active', i === index));
      }}

      reviewRows.forEach((row, index) => {{
        const marker = L.circleMarker([parseFloat(row.auto_lat), parseFloat(row.auto_lng)], {{
          radius: 8,
          color: '#ffffff',
          weight: 2,
          fillColor: statusColor[row.coordinate_status] || '#b6422a',
          fillOpacity: 0.92
        }});
        marker.bindPopup(popupHtml(row));
        marker.on('click', () => highlightRow(index));
        marker.addTo(map);
        markers.push({{ marker, row, index }});
      }});

      tbodyRows.forEach((tr, index) => {{
        tr.addEventListener('click', () => {{
          const item = markers[index];
          map.panTo(item.marker.getLatLng());
          item.marker.openPopup();
          highlightRow(index);
        }});
        tr.addEventListener('mouseenter', () => highlightRow(index));
      }});

      function applyFilters() {{
        const landmarkValue = landmarkFilter.value;
        const statusValue = statusFilter.value;
        const visibleLatLngs = [];

        markers.forEach(item => {{
          const landmarkMatch = landmarkValue === 'all' || item.row.landmark_key === landmarkValue;
          const statusMatch = statusValue === 'all' || item.row.coordinate_status === statusValue;
          const visible = landmarkMatch && statusMatch;
          if (visible) {{
            item.marker.addTo(map);
            visibleLatLngs.push(item.marker.getLatLng());
            tbodyRows[item.index].style.display = '';
          }} else {{
            item.marker.remove();
            tbodyRows[item.index].style.display = 'none';
          }}
        }});

        if (visibleLatLngs.length > 0) {{
          map.fitBounds(L.latLngBounds(visibleLatLngs), {{ padding: [32, 32], maxZoom: 16 }});
        }}
      }}

      document.getElementById('fit-all').addEventListener('click', () => {{
        const visible = markers.filter(item => map.hasLayer(item.marker)).map(item => item.marker.getLatLng());
        if (visible.length > 0) {{
          map.fitBounds(L.latLngBounds(visible), {{ padding: [32, 32], maxZoom: 16 }});
        }}
      }});

      landmarkFilter.addEventListener('change', applyFilters);
      statusFilter.addEventListener('change', applyFilters);
    </script>
  </main>
</body>
</html>
"""


def write_html(rows: List[Dict[str, str]]) -> None:
    OUTPUT_HTML_PATH.write_text(build_html(rows), encoding="utf-8")


def write_plan(rows: List[Dict[str, str]]) -> None:
    execution_date = date.today().isoformat()
    landmark_counter = Counter(row["landmark_key"] for row in rows)
    status_counter = Counter(row["coordinate_status"] for row in rows)
    lines = [
        "# 美笛キャンプ場 Phase 4-2 実行メモ",
        "",
        f"- execution date: {execution_date}",
        f"- input CSV path: {INPUT_CSV_PATH}",
        f"- landmark reference path: {LANDMARK_CSV_PATH}",
        f"- provisional coordinates path: {OUTPUT_CSV_PATH}",
        f"- internal review HTML path: {OUTPUT_HTML_PATH}",
        f"- selected rows: {len(rows)}",
        "- map renderer: Leaflet",
        "- base map: 国土地理院 淡色地図（初期）",
        "- Leaflet loading: CDN",
        "- runtime network required: yes (Leaflet CDN + 地理院タイル)",
        "",
        "## count by landmark_key",
    ]
    for key, count in sorted(landmark_counter.items()):
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## count by coordinate_status"])
    for key, count in sorted(status_counter.items()):
        lines.append(f"- {key}: {count}")
    lines.extend(
        [
            "",
            "## 注意",
            "- auto_lat / auto_lng は manual landmark table に基づく仮座標であり、確定地点ではない。",
            "- confirmed_lat / confirmed_lng は人手レビュー後にのみ記入する。",
            "- public_map_candidate は未記入のまま維持する。",
            "- internal review only。公開用HTMLや公開用地図画像ではない。",
            "- Phase 4 の静的画像生成はまだ開始していない。",
        ]
    )
    OUTPUT_PLAN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    review_rows = read_csv_rows(INPUT_CSV_PATH)
    landmarks = read_landmarks(LANDMARK_CSV_PATH)
    output_rows = build_output_rows(review_rows, landmarks)

    write_output_csv(output_rows)
    write_html(output_rows)
    write_plan(output_rows)

    all_status = all(row["map_review_status"] == "未確認" for row in output_rows)
    all_have_auto = all(row["auto_lat"] and row["auto_lng"] for row in output_rows)
    all_blank_confirmed = all(
        not row["confirmed_lat"] and not row["confirmed_lng"] and not row["public_map_candidate"]
        for row in output_rows
    )

    print(f"input_review_candidate_row_count={len(review_rows)}")
    print(f"output_provisional_coordinate_row_count={len(output_rows)}")
    print(f"all_map_review_status_unconfirmed={'yes' if all_status else 'no'}")
    print(f"all_auto_coordinates_present={'yes' if all_have_auto else 'no'}")
    print(f"confirmed_and_public_fields_blank={'yes' if all_blank_confirmed else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
