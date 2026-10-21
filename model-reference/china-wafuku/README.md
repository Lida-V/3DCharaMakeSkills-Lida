# チャイナ和服新キャラ — 制作参照用モデル r35

日本語 · [English](README.en.md)

© 2026 Lida · [公式配布元](https://github.com/Lida-V/3DCharaMakeSkills-Lida)

ユーザーが完成参照として選んだ、リダとは別の制作例です。**[参照専用ZIPを取得](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/model-reference-r35/ChinaWafuku-Reference-r35.zip)**して、VRM 1.0対応のツールでモデルを開きます。通常のSkills ZIPにモデル本体は含みません。

**モデル本体の再配布・改変による販売は禁止です。** [モデル専用の利用条件](MODEL-TERMS.md)を先に確認してください。Skills本体の商用利用・再配布の条件は変わりません。

## 使い方

1. ZIP内の`SHA256SUMS.txt`とReleaseの`.zip.sha256`で取得物の一致を確認します。
2. `ChinaWafuku-Reference-r35.vrm`を参照として開き、作業対象とは別に保管します。VRMを読むための環境は別途必要です。
3. 必要な部位だけ、形・表面の線・骨とウェイト・表情・材質を同条件で観察します。AIには対象部位と見たい特徴を指定します。[詳しい観察手順](https://github.com/Lida-V/3DCharaMakeSkills-Lida/blob/main/skills/lida-avatar-workflow/references/model-reference.md)へ進んでください。
4. 数値・網目・キャラの意匠をそのまま転用せず、観察した考え方を自分のモデルの資料と構造へ適用します。調整は新しい候補へ保存し、見た目と動作でも確かめます。

## 内容と確認範囲

| 項目 | 内容 |
| --- | --- |
| 入力版 | r35 / internal revision37 |
| 配布形式 | VRM 1.0。メッシュ28、ノード125、内蔵画像38、揺れ鎖18、コライダー13 |
| 収録 | モデル1体、日英の案内と利用条件、構成・SHAのJSON、チェックサム |
| 含まないもの | 編集用Blend、FBX、参考ダンス・モーション、APIログ、制作環境 |
| 保持検査 | 元VRMと配布コピーのBINが完全一致。JSONも公開メタデータ以外は一致 |
| 表示の注意 | VRMの材質はMToon系。LidaAngelToonの編集用ノードは含まない |
| 検証の限界 | 書出し後の三角面であり元の編集用網目ではない。Unity/UEでの見た目・動作合格を保証しない |

メタデータだけ公開用に整えたため、元VRMと配布VRMのファイルSHAは異なります。各値と変更フィールドは`reference-manifest.json`に記録しています。作者情報の公開表記はLidaです。元の制作モデルは変更していません。
