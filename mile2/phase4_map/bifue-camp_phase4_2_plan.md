# 美笛キャンプ場 Phase 4-2 実行メモ

- execution date: 2026-06-09
- input CSV path: C:\myprojects\kumayoke\mile2\phase4_map\bifue-camp_map_review_candidates.csv
- landmark reference path: C:\myprojects\kumayoke\mile2\phase4_map\bifue-camp_landmark_reference.csv
- provisional coordinates path: C:\myprojects\kumayoke\mile2\phase4_map\bifue-camp_provisional_coordinates.csv
- internal review HTML path: C:\myprojects\kumayoke\mile2\phase4_map\bifue-camp_auto_pin_review.html
- selected rows: 13
- map renderer: Leaflet
- base map: 国土地理院 淡色地図（初期）
- Leaflet loading: CDN
- runtime network required: yes (Leaflet CDN + 地理院タイル)

## count by landmark_key
- bifue_bridge: 4
- bifue_camp_gate: 1
- bifue_tunnel: 2
- chitose_bridge: 3
- harubue_bridge: 1
- route_78_bifue_area: 2

## count by coordinate_status
- 仮: 13

## 注意
- auto_lat / auto_lng は manual landmark table に基づく仮座標であり、確定地点ではない。
- confirmed_lat / confirmed_lng は人手レビュー後にのみ記入する。
- public_map_candidate は未記入のまま維持する。
- internal review only。公開用HTMLや公開用地図画像ではない。
- Phase 4 の静的画像生成はまだ開始していない。
