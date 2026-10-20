# 同梱の制作補助ツールを使う

[日本語](model-tools.md) · [English](en/model-tools.md)

**Skillsが作業の判断と順番を示し、ツールが繰り返す検査と処理を担当します。** 毎回同じ検査コードを書き直さず、同じ条件で修正前後を比べるための補助です。

実制作で使ったLida Avatar Toolkitの汎用処理を基に、[lida_model_tools.py](../scripts/lida_model_tools.py)を配布用に再構成しています。常駐アドオン全体を登録せず、必要な時だけBlenderの別セッションから実行するスクリプトです。既存アドオンの設定や制作パネルを置き換えません。

## 含まれるものと、できること

| 機能 | 使う場面 | 出力 |
| --- | --- | --- |
| `rig-audit` | オートリグの受領後、骨の修正前後 | 明示リグの構造、指定した人型割当・対象メッシュの機械検査。画像・動作の未確認も明記 |
| `audit` | 粗い3Dの受領後、網目・UV・ウェイト・表情キーの調整前後 | 明示したメッシュの構造と値を調べたJSON |
| `snapshot` | 修正前、保存して開き直した後、部位の合流前後 | 基礎座標・接続・UV・変形ウェイト・キー座標と差分・材質スロットと面の割当の項目別ハッシュ、入力ファイルSHA |
| `compare` | 修正前後のsnapshotがそろった時 | 対象と項目ごとの一致・差分。通常のPythonでも実行可 |
| `normalize-copy` | ウェイト総和だけを直す必要があり、対象と保持条件が決まった時 | 対象の候補コピーと、別名のblend、検査JSON |

ウェイト検査は変形に使う骨のグループを対象にし、単なるマスクを総和へ混ぜません。正規化はロックとマスクを保持し、未ロックの変形ウェイトの合計を調整します。未割当・負値・非有限値・ロック条件の矛盾は、勝手に補完骨へ割り当てず未解決として扱います。

このツールは、原画に似ているか、線の配置が適切か、自然に曲がるかを自動採点しません。境界辺、範囲外UV、変化のないキーは意図的な場合もあるため、件数だけで削除・修復せず[画像で判断](visual-handoff.md)してください。正規化も、骨位置・形状・面の流れ・不適切な割当先を直す処理ではありません。

## 用意するもの

- Blenderと、検査する保存済みのblend。実測した対応版は検証欄で確認します。
- 対象メッシュ名。ウェイトを扱う場合は対応するアーマチュア名。
- 新しく作るJSONの保存先。修復候補には入力と異なる新規blendの保存先。
- [工程のゴール](quality-goals.md)と、どの項目の変化を許し、何を保持するか。

APIキー、外部サービス、追加Pythonパッケージ、ネットワーク接続は使いません。Blenderの自動導入や、元モデル・参考モーションの取得を行うツールでもありません。スキルを読むだけなら実行環境の導入は不要です。

## AIが行う順序

1. 使用可能なBlender、入力版、メッシュ名、リグ、出力先を確認する。名前を推測せず、現在のファイルと対応を調べる。
2. まず`audit`を実行し、JSONの対象・検査範囲・未検査項目を読む。診断だけで原blendを保存しない。
3. 変更前の`snapshot`を取り、固定する項目を決める。修正後と保存再読込後に取り直し、`compare`で比較する。
4. 必要な場合だけ、明示した対象へ`normalize-copy`を使う。新規候補と保持結果を確認し、原本へ自動採用しない。
5. 同じ角度・姿勢の画像と動作を比較し、数値検査、外観、保存、使用先の合格を分けて報告する。

Blenderが使えない場合は、ツールを実行済みと報告しません。実行できない理由と手動で確認した範囲を残します。既存の採用版や原画を、検査に通すために変えないでください。

機械検査の終了コードだけで工程を完了にしません。[機械・画像・動作の役割と判定](mechanical-visual-review.md)で、同じ保存版の原画比較、必要な途中動作、使用先の残件を確認します。

## 最初の実行例

パスと名前は自分のファイルへ置き換えます。`--`より後ろはこのツールの引数です。入力のスクリプト自動実行を無効にし、通常の作業セッションとは別に起動します。

```sh
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- audit --input source.blend --objects Body --rig Rig --report audit-before.json
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- snapshot --input source.blend --objects Body --rig Rig --report before.json
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- snapshot --input candidate.blend --objects Body --rig Rig --report after.json
python lida_model_tools.py compare --left before.json --right after.json --report difference.json
```

JSONの出力先には既存ファイルを指定しません。実際の呼び方は`--help`でも確認できます。モデルを開いたままのUIから同名スクリプトを繰り返し登録する手順ではありません。

ウェイトの影響骨数は`audit --max-influences N`で使用先の条件へ合わせます。既定の4は集計の比較基準で、全モデルの品質条件ではありません。検査の終了コード0は処理完了、1は入力・実行エラー、2はsnapshotの差または正規化の未解決です。差が予定どおりかはJSONを読み、終了コードだけで自動修正を繰り返しません。

引数不足や未知の引数など、使用方法のエラーも終了コード2となり、JSON生成前に停止します。差分・未解決との区別は、新しく生成されたJSONの有無と`status`で判断してください。以前のJSONを今回の結果として読みません。

### 骨構成と人型への割当を調べる

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_model_tools.py -- rig-audit --input source.blend --rig Rig --objects Body --human-bones human-bones.json --report rig-before.json
```

リグ・メッシュの実名を調べて指定します。`--objects`を省くとメッシュ/重みとの対応、`--human-bones`を省くとVRM人型割当は未検査です。骨名から自動推定して合格にはしません。`rig-audit`の0は指定した機械項目に問題を検出しなかったこと、2は機械的な指摘、1は入力/実行エラーです。指摘の理由と観測値を読み、見た目を確かめず一律に修正しません。

`human-bones.json`は、このツール専用の対応表です。左はVRM 1.0の役割、右は**実際の骨名**。次は必須部分の例で、使用先で必要な眼・顎・指・肩などは実データを調べて加えます。

```json
{
  "schema": "lida.model-tools.humanoid-map.v1",
  "spec_version": "1.0",
  "human_bones": {
    "hips": "Hips", "spine": "Spine", "head": "Head",
    "leftUpperArm": "UpperArm.L", "leftLowerArm": "LowerArm.L", "leftHand": "Hand.L",
    "rightUpperArm": "UpperArm.R", "rightLowerArm": "LowerArm.R", "rightHand": "Hand.R",
    "leftUpperLeg": "UpperLeg.L", "leftLowerLeg": "LowerLeg.L", "leftFoot": "Foot.L",
    "rightUpperLeg": "UpperLeg.R", "rightLowerLeg": "LowerLeg.R", "rightFoot": "Foot.R"
  }
}
```

[VRM 1.0公式仕様](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)の必須/任意、重複割当、骨の存在、途中の補助骨を許す祖先関係を調べます。任意骨にも親が必要なものがあり、例えば`upperChest`には`chest`、親指の`Proximal`には`Metacarpal`の割当が必要です。15本は必須の役割数であり、モデルの総骨数や高品質の条件ではありません。このJSONはVRMファイル自体の`humanBones`やglTFノード番号ではなく、エクスポーターへの割当書込みも行いません。

骨の数値・長さ、基準姿勢と現在姿勢、指定メッシュのArmature参照と変形ウェイトも調べます。`--length-epsilon`はリグのローカル単位での長さの閾値、`--weight-tolerance`は総和の許容差、`--max-influences`は使用先に合わせた影響数の集計上限です。既定の影響数4をVRM仕様の固定条件にしません。左右を逆に対応表へ書いた場合の意味上の正しさ、肩や膝の位置が原画に合うか、曲げた時に自然かは画像と動作で確認してください。

### Tripoへ送るFBXの容量と識別形式を調べる

次は通常Pythonで動く別の補助CLI [lida_file_check.py](../scripts/lida_file_check.py)です。Blenderや追加パッケージは不要です。

```sh
python lida_file_check.py --input upload.fbx --report upload-check.json
```

実ファイルの容量・拡張子・FBX識別ヘッダ・SHAを確認します。既定上限は150,000,000バイトを安全側の目安とし、実行時のTripoの表示も[送信準備](tripo-autorig.md)で確認します。必要な上限が明示された場合だけ`--max-bytes`で変更します。

0は列挙したファイル条件に適合、2は条件不適合、1は入力/I/Oエラーです。識別ヘッダの確認は、完全なFBX構文・骨/画像の保持・インポート可能性やTripoの受付成功を保証しません。原本を変更せず、新規JSONへ出力します。モデルや入力ファイルと同じ出力先、既存レポートは拒否します。

### ウェイト総和だけを候補コピーで直す

```sh
blender --background --factory-startup --disable-autoexec --python lida_model_tools.py -- normalize-copy --input source.blend --objects Body --rig Rig --report normalize.json --output-blend weight-candidate.blend
```

入力と同じパス、既存の出力ファイルは拒否します。未解決のウェイトがあれば、その内容を報告し、修復済みの候補として保存しません。影響骨数の削減、最近傍面への転写、全自動リグ、形状の再生成は初版の機能に含みません。

候補blendには元メッシュと新しい候補コピーが両方残ります。レポートの元名・候補名を使い、一方ずつ表示して比較してください。同位置の両方を重ねて描画した画像を修正結果にせず、確認後にどちらを採用するか決めます。

## レポートで分かる範囲

`snapshot`の内容一致は、列挙した基礎データの確認です。骨の基準姿勢、親子・制約、ドライバー、Geometry Nodes、材質ノードの内部、評価後の形状、外部画像の内容、アニメーション、使用先の実行まで同じとは判断できません。未対応の項目は別に確認します。

マスクなどの非変形グループ、グループのロック、キー値・ミュート・再生設定もsnapshotの比較対象外です。相対キーは各キーの座標・差分と参照先を記録し、絶対キーのsnapshotは対応外として拒否します。材質はスロットの名前・順・リンクと面への割当を記録し、ノード内部は記録しません。ウェイト正規化時のロック・マスク保持は、その処理の検査で別に確認します。

`compare`はハッシュで完全一致を調べます。差がある時の最大距離や許容差の合格を出す機能ではありません。形状を変える修正では、その項目が変わるのは正常です。変更を許した項目と固定項目を照合し、頂点の意味上の対応や外観は実メッシュで判断してください。

監査は基礎メッシュと現在の保存データが対象です。自己交差、身体と衣装の接触、全フレームの動作を調べる機能ではありません。眼球や翼の専用生成、制作時の全操作パネル、旧Toolkitの二次揺れハンドラ、宝石生成、シェーダーもこのスクリプトへまとめていません。

## 確認済みの範囲

2026-10-15の初版は、**Blender 5.2.1 LTSの背景実行**で合成モデルに対するAPI14項目・CLI19項目と、通常Pythonの回帰テスト7件を確認しました。2026-10-19の拡張では、骨監査のAPI15ケース・CLI9ケースと、既存CLI19項目を同環境で再確認しました。元のToolkitの過去の合格を新実装の検証に代用していません。

正常なモデルに加え、退化面・非有限座標・範囲外UV・変化のないキー・未割当／非有限ウェイト・ロック矛盾、同じ頂点数でも異なる接続を試しています。コピーのロックとマスク保持、原本ファイルのSHA保持、別候補の保存と再読込、既存出力の拒否も確認しました。

FBX条件CLIは合成ヘッダ・容量境界・既存出力の保持など19テストを用意しました。今回の環境ではリンク作成を使う2件を実行できず、17件が成功しています。同一パスや通常の別名参照による出力拒否は確認済みです。Blenderで生成した合成FBX1件でも識別ヘッダと容量の適合・原本SHA保持を確認しました。これはFBX全構文やサービス受付の検証ではありません。

これは合成モデルで列挙した処理の検証です。他のBlender版、GUIアドオン導入、実モデルの全姿勢、造形・原画再現・使用先の品質を検証したという意味ではありません。

## 利用条件と導入範囲

このBlender用スクリプトは **GPL-3.0-or-later**。適用範囲はファイル冒頭と[同梱GPL本文](../scripts/LICENSE-GPL-3.0-or-later.txt)を確認します。文書・図解の条件とは分け、GPLコードへ独自の出典条件を上乗せしません。元の著作者表示と適用ライセンスを保持します。

モデル・画像・動画を制作するだけなら、その成果物へのクレジットは不要です。文書や指示を組み込む公開アプリ・新Skillsの出典は[利用区分](usage-and-attribution.md)を引き継ぎます。
