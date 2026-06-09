# 千歳市ヒグマ目撃情報 解析メモ

- execution date: 2026-06-09
- fetched target years: 2026, 2025, 2024, 2023, 2022, 2021
- number of source pages fetched: 6
- raw CSV row count: 303
- mode: parse-only

## parsing uncertainties
- 2026: parsed from heading/body pattern
- 2025: parsed from heading/body pattern
- 2024: parsed from heading/body pattern
- 2023: parsed from heading/body pattern
- 2022: parsed from heading/body pattern
- 2021: parsed from heading/body pattern

## parser improvement
- parser improvement date: 2026-06-09
- added location extraction patterns for directional movement, road crossing, roadside sighting, direct sighting, and trace phrases
- before/after location_text blank count: 1 -> 0
- before/after raw CSV row count: 303 -> 303
- remaining limitations: 年ごとの差分や本文の表現揺れにより、一部の location_text は引き続き空欄の可能性がある

## manual checks needed
- 年ごとの表構造差分がないか確認すること
- date_text / location_text / category_text / body_text の対応が自然か確認すること
- Bifue relevance と public map inclusion judgment は Phase 3 で行うこと
