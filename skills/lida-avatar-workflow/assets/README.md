# 同梱図版と参照モデル

[日本語](README.md) · [English](README.en.md)

[図解索引](../references/diagram-index.md)から、説明章とPNG/SVGへ進みます。全25枚に表示用PNGと拡大用SVGを同梱しています。

- `material-repair-selection`：割当/画像設定/UV・材質値/共有先・形/法線、共有材質と元画像保持を分ける自作模式図。
- `mesh-repair-selection`：意図した開口を残し、向き・局所パッチ・境界接続・局所再構築を選ぶ自作模式図。
- `mesh-boundary-repair`：固定境界、新規面、対応点、確認済み/推定を分ける施工の自作模式図。実モデルの修復成功を示すものではない。

## 制作参照モデル

公式Skills完成配布ZIPには、`model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm`をSkillsの構成要素として同梱します。スキルフォルダと一緒にコピーし、[観察ガイド](../references/model-reference.md)に従って必要な工程で構造を参照してください。通常の導入にモデルの別ダウンロードは不要です。

モデル本体の再配布・改変による販売は禁止です。[モデル専用条件](model-reference/china-wafuku/MODEL-TERMS.md)を適用し、下記の自作図版やGPLコードの条件とは分けます。モデルを含む一式ZIPを利用者が再配布することはできません。

GitHubのCode / Source code ZIPは保守用ソースです。モデルも一緒に導入する場合は[公式完成配布ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.9.0/3DCharaMakeSkills-Lida-1.9.0.zip)を使ってください。

## 出所と役割

- `wink-eye-isolation`（自作模式図）：通常の瞬きと笑った閉眼を分け、同一基準の目差分、本人左右のマスク、途中・隣接列・別層の追従を対応。自動造形や実モデルの成功図ではない。
- `input-alignment-flow`（自作模式図）：同じ基準から段階別素材と三面図を用意する。段階別生成は次回の予防案。
- `local-mask-transition`（自作模式図）：移動量と戻す幅の違い。修正マスクとスキンウェイトは別。
- `eye-structure-flow`（自作模式図）：球面・虹彩/瞳孔・白目・任意の薄い反射面、眼球と一緒に回さない線の層。
- `face-key-locality`（自作模式図）：対象部位だけの表情キーと、顎・輪郭・対象外の固定。
- `mouth-seam-opening`（自作模式図）：通常顔に描いた口線と開口時の上下のメッシュ境界、口角の支点、表側と裏の折り返しを区別。実際の修正完了例ではない。
- `eyelid-band-follow`（自作模式図）：まぶたの縁と隣接列の局所変換、外側への減衰。
- `hand-shortening-flow`（自作模式図）：掌の高さとU字周辺の輪郭を別々に調整。
- `hand-structure-map`（自作模式図）：手の向き・目印と、指関節の輪・骨・母指球・指間の面のつながりを対応。最適トポロジーや比率を指定する図ではない。
- `hand-deformation-check`（自作模式図）：空間距離と皮膚表面の経路の違い、形・骨・ウェイトの診断、単指・親指・握りの途中と爪の確認。
- `skirt-layer-route`（自作模式図）：層順序、支持域、自由裾と脚の通り道。
- `hair-strand-structure`（自作模式図）：髪だけの配置、中心線と幅/厚み/断面、根元・先端、頭皮下地と固定/自由端。ガイドと網目・骨を区別する。
- `hair-cause-isolation`（自作模式図）：髪の基本色・接続・面順序の原因切分け。
- `wing-build-sequence`（自作模式図）：外形・支持体・少数羽・全列・途中動作を確認する順序。
- `wing-feather-terms`（自作模式図）：鳥の一般的な羽群の名称と全体の区域、上下面、根元を覆う関係。創作の固定仕様ではない。
- `wing-feather-layout`（自作模式図）：創作翼の羽種別・羽軸・覆う順序・根元面の取付。
- `wing-root-fit`（自作模式図）：創作翼の断面・付着幅・方向・重みの対応。
- `integration-dependencies`（自作模式図）：部品の採用版と依存物を合わせて統合。版記号は説明用。
- `bend-support`（自作模式図）：関節前後の連続した支持帯。
- `flow-continuity`（自作模式図）：最大変形帯の面と辺の流れ。
- `actual-knee-layout`（以前の実メッシュ診断）：当時の実メッシュと、未実施の配置案を区別した図。
- `actual-knee-bend`（以前の実メッシュ診断）：当時の実メッシュを曲げた診断図。完成済みの成功例ではない。

模式図は制作記録の方法を整理したもので、実モデルの修正前後・採用済み成果を新たに示すものではありません。実エッジ、破線の案、模式図を取り違えない。[膝の図の読み方](../references/knee-edge-placement.md)。

図内の形・寸法・列数・版記号は共通の設定値ではありません。色と番号、実線/破線、向きの説明を使い、対象部位の実画像と対応させてください。PNGの表示も目視確認してから更新します。

## 資料単体で分かる出典表示

全25組のSVGとPNGは、説明の下へ余白を足し、「© 2026 Lida · 3DCharaMakeSkills-Lida」と `github.com/Lida-V/3DCharaMakeSkills-Lida` を表示しています。本文・線・矢印を覆う透かしではなく、画像だけで共有された時の来歴表示です。

SVGの元の図形・文字は保持し、PNGはそのSVGから描画しています。PNGとSVGの両方で出典帯が読めることを確認して更新してください。表示の追加で利用条件を変更してはいません。
