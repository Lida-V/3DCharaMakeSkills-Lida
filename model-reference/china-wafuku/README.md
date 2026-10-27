# チャイナ和服新キャラ — 制作参照用モデル r35

日本語 · [English](README.en.md)

© 2026 Lida · [公式配布元](https://github.com/Lida-V/3DCharaMakeSkills-Lida)

リダとは別の完成例として、Skillsに含める制作参照モデルです。**[モデルを含むSkills一式ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.9.0/3DCharaMakeSkills-Lida-1.9.0.zip)**を展開し、スキルフォルダを丸ごと導入してください。VRM 1.0とモデル専用条件も同じフォルダへ配置されます。別取得は不要です。

**モデル本体の再配布・改変販売は禁止。モデルを含む一式ZIPの利用者による再配布もできません。** [専用利用条件](MODEL-TERMS.md)を確認してください。文書・図解・コードは、モデルを除いて各LICENSEに従い利用・再配布できます。

## 使い方

1. Releaseの`.zip.sha256`で取得したSkills一式ZIPの一致を確認します。
2. スキル内の`assets/model-reference/china-wafuku/ChinaWafuku-Reference-r35.vrm`を参照として開き、作業対象とは別に保管します。VRMを読むための環境は別途必要です。
3. 必要な部位だけ、形・表面の線・骨とウェイト・表情・材質を同条件で観察します。AIには対象部位と見たい特徴を指定します。[詳しい観察手順](https://github.com/Lida-V/3DCharaMakeSkills-Lida/blob/main/skills/lida-avatar-workflow/references/model-reference.md)へ進んでください。
4. 数値・網目・キャラの意匠をそのまま転用せず、観察した考え方を自分のモデルの資料と構造へ適用します。調整は新しい候補へ保存し、見た目と動作でも確かめます。

## 内容と確認範囲

| 項目 | 内容 |
| --- | --- |
| 入力版 | r35 / internal revision37 |
| 配布形式 | VRM 1.0。メッシュ28、ノード125、内蔵画像38、揺れ鎖18、コライダー13 |
| 収録 | Skills一式に参照モデル1体、日英の専用条件、構成・SHAのJSONを同梱 |
| 含まないもの | 編集用Blend、FBX、参考ダンス・モーション、APIログ、制作環境 |
| 保持検査 | 元VRMと配布コピーのBINが完全一致。JSONも公開メタデータ以外は一致 |
| 表示の注意 | VRMの材質はMToon系。LidaAngelToonの編集用ノードは含まない |
| 検証の限界 | 書出し後の三角面であり元の編集用網目ではない。Unity/UEでの見た目・動作合格を保証しない |

メタデータだけ公開用に整えたため、元VRMと配布VRMのファイルSHAは異なります。各値と変更フィールドは`reference-manifest.json`に記録しています。作者情報の公開表記はLidaです。元の制作モデルは変更していません。
