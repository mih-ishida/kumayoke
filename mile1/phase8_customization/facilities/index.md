# 施設別HTML 一覧管理

作成日：2026-06-01
用途：施設別ページ量産前の管理表。差し替え案は `../facility_replacement_drafts.md`、施設タイプ別方針は `../facility_type_rules.md` を参照。

- エリア・施設タイプは正本 `mile1/phase9_target_list/target_list.md` に準拠。施設タイプは現時点の仮分類であり、送信前に必要に応じて見直す。
- 管理表内の施設名は可読性のため敬称なし表記。公開ページ・eyebrow・件名例では「様」を付ける（各差し替え案参照）。
- slug は小文字・ハイフン区切り。HTML予定パスは `web/f/<slug>.html`、メモ予定パスは `mile1/phase8_customization/facilities/<slug>.md`。

| No | 施設名 | エリア | 施設タイプ | slug案 | HTML予定パス | メモ予定パス | 作成状態 | 人間確認 |
|---:|---|---|---|---|---|---|---|---|
| 1 | レイクサイドヴィラ翠明閣 | 支笏湖 | ホテル | lakeside-villa-suimeikaku | web/f/lakeside-villa-suimeikaku.html | mile1/phase8_customization/facilities/lakeside-villa-suimeikaku.md | 試作 | 未 |
| 2 | 雨ノ日と夕やけ | 支笏湖 | ロッジ・小規模宿 | amenohi-to-yuyake | web/f/amenohi-to-yuyake.html | mile1/phase8_customization/facilities/amenohi-to-yuyake.md | 試作 | 未 |
| 3 | モラップキャンプ場 | 支笏湖 | キャンプ場 | morappu-camp | web/f/morappu-camp.html | mile1/phase8_customization/facilities/morappu-camp.md | 試作 | 未 |
| 4 | Forever Camping Paradise | 千歳 | キャンプ場 | forever-camping-paradise | web/f/forever-camping-paradise.html | mile1/phase8_customization/facilities/forever-camping-paradise.md | 試作 | 未 |
| 5 | 松原温泉旅館 | 千歳 | 旅館 | matsubara-onsen-ryokan | web/f/matsubara-onsen-ryokan.html | mile1/phase8_customization/facilities/matsubara-onsen-ryokan.md | 試作 | 未 |
| 6 | NOMAD STAY CHITOSE | 千歳 | 一棟貸し宿泊施設 | nomad-stay-chitose | web/f/nomad-stay-chitose.html | mile1/phase8_customization/facilities/nomad-stay-chitose.md | 試作 | 未 |
| 7 | Piece Chitose S1 | 千歳 | ホテル | piece-chitose-s1 | web/f/piece-chitose-s1.html | mile1/phase8_customization/facilities/piece-chitose-s1.md | 試作 | 未 |
| 8 | 定山渓自然の村 | 定山渓 | キャンプ場・自然体験施設 | jozankei-nature-village | web/f/jozankei-nature-village.html | mile1/phase8_customization/facilities/jozankei-nature-village.md | 作成済み | 未 |
| 9 | 悠久の宿 白糸 | 定山渓 | 旅館 | yukyu-no-yado-shiraito | web/f/yukyu-no-yado-shiraito.html | mile1/phase8_customization/facilities/yukyu-no-yado-shiraito.md | 試作 | 未 |
| 10 | SAKURA 定山渓 膳 | 定山渓 | 一棟貸し・ロッジ系 | sakura-jozankei-zen | web/f/sakura-jozankei-zen.html | mile1/phase8_customization/facilities/sakura-jozankei-zen.md | 試作 | 未 |

## 状態の凡例

- **作成済み**：HTML・メモともに作成済み（定山渓自然の村）。
- **試作**：HTML・メモを差し替え案から試作済み。文面・公式情報の人間確認はこれから（定山渓自然の村を除く9施設すべて）。
- **未作成**：差し替え案のみ整理済み。HTML・メモは未着手。
- **人間確認「未」**：エリア・施設タイプ・公式情報の事実確認が未了。HTML作成前に確認する。

## 進め方の目安

1. エリア・施設タイプは正本に準拠済み。公式サイトで受付体制（有人/無人）・屋外滞在の有無・野生動物/クマ案内の有無を確認する。
2. `facility_type_rules.md` の該当タイプ方針を当てる。
3. `facility_replacement_drafts.md` の該当施設の差し替え案を当てて HTML 作成。
4. 作成後に本表の作成状態・人間確認を更新。
