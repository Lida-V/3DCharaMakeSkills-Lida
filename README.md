# 3DCharaMakeSkills-Lida

日本語 · [English](README.en.md)

画像から3Dキャラクターを作るときの、素材・調整方法・AIへの指示をまとめた **日本語・英語対応の配布用1.8.1** です。初心者向けに「素材→順番→具体調整→つまずき」を整理し、24枚の図解と実モデルの表示例を収録しています。英語版はREADME・スキル入口・参照全章と依頼文に対応し、図内の日本語ラベルは英語の凡例と説明を併用します。

## 実際の制作例

リダの3DモデルをBlenderで描画した画像です。生成したベースから、顔・髪・衣装・装飾・翼の形状、表情、ウェイト、材質を調整して仕上げた作例です。

| 全身・衣装・翼 | 顔・髪・装飾 |
| --- | --- |
| ![リダの実モデルの全身。多段スカート・ロングヘアー・翼・靴まで確認できるBlender描画](media/lida-finished-body.png) | ![リダの実モデルのバストアップ。顔・髪・冠・襟・ペンダントを確認できるBlender描画](media/lida-finished-face.png) |

**[10秒動画：全身の回転と表情を見る](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.2.2/lida-model-turntable-attributed.mp4)** — 左は全身の1周、右は笑顔・驚き・口型「あ」・瞬き。音声なし。

表示はBlender 5.2.1 LTS／EEVEEと制作モデル内のトゥーン材質です。[画像・動画の内容と表示条件](media/README.md)を確認できます。

図解と紹介画像・動画には、画像だけで共有された時も出所を確認できるよう、余白へLida名と配布元URLを表示しています。本文やモデルの見える範囲は遮っていません。利用条件は従来どおりです。

**Tripoなどの3Dモデル生成サービスの利用を前提とした制作手順です。商用利用も可能です。**

## Skillsに含まれる完成参照モデル

**[参照モデルを含むSkills一式をダウンロード](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.8.1/3DCharaMakeSkills-Lida-1.8.1.zip)** — 公式の完成ZIPに、制作例「チャイナ和服新キャラ r35」のVRM 1.0を収録しています。展開後のスキルフォルダを丸ごと導入すると、参照モデルも一緒に配置されます。別ダウンロードは不要です。

このモデルはSkillsの制作参照資料です。顔・手指・関節・袖・材質・表情・揺れの関係を実物で学べます。[何を見るか・AIへの依頼例](skills/lida-avatar-workflow/references/model-reference.md)から必要な部位だけを参照してください。

**モデル本体の再配布・改変による販売は禁止です。モデルを含む一式ZIPも利用者が再配布しないでください。** [モデル専用条件](model-reference/china-wafuku/MODEL-TERMS.md)を適用します。文書・図解・コードの個別条件は維持し、モデルを除いた資料・コードは各LICENSEに従って再配布できます。参照して独自に作った別モデルの販売は禁止しません。VRM三角面は元の編集用網目ではなく、Unity/UEの外観・動作は保証しません。

## 制作の前提

基準となるイラストを用意し、Tripoなどのサービスでベースモデルや口型・表情の参考モデルを生成してから、Blenderなどで形状・メッシュ・骨・スキンウェイト・表情を調整します。新規の動く人型では、通常形と関節の網目を整え、**150MB以内のFBX → TripoのVRM 1.0オートリグ → 骨・ウェイトの調整**を挟みます。骨格の導入と完成VRMの出力は別工程です。既存の良いリグは再利用します。

実制作には、利用する3D生成サービス、モデリングソフト、必要な画像素材を別途用意してください。本パックにサービスやソフト本体は同梱しません。別の生成サービスを使う場合も、必要な角度・同一性・出力形式がそろうかを確認します。既存モデルの修正だけなら、改めて生成する必要はありません。

## 入手して使う

1. **[公式のSkills一式ZIP](https://github.com/Lida-V/3DCharaMakeSkills-Lida/releases/download/v1.8.1/3DCharaMakeSkills-Lida-1.8.1.zip)**を取得して展開します。参照モデル・専用条件も含まれています。GitHubのCode → Download ZIPと自動生成のSource code ZIPは保守用ソースで、モデル本体を含みません。通常の導入には上記の完成ZIPを使ってください。
2. `skills/lida-avatar-workflow` を、参照文書・画像・LICENSE・NOTICE・補助スクリプトを含め、エージェントのスキル保存先へ丸ごとコピーします。`SKILL.md`だけにしないでください。
3. スキルを読み込ませ、次の導入確認を依頼します。読むだけの利用者にPythonやシェーダーの導入は必要ありません。

> lida-avatar-workflowを読み、モデル制作を始める前に、必要な素材・推奨品質・工程順・各終了条件を短い制作計画にしてください。メッシュ、貫通、材質、手指の動き、眼球の5項目の診断予定と、材質の変更可能範囲も示してください。今回は導入確認だけで、実サービスやモデル処理の実行はまだ不要です。

名前付き指定が使える環境では `$lida-avatar-workflow` と指定できます。読み込めない時は、保存先・同名スキルの重複・参照文書や画像の欠落を確認してください。[利用者向け更新手順](UPDATING.md#利用者の更新)も用意しています。

## 最初に読む

- [新規制作からの追加フィードバック](skills/lida-avatar-workflow/references/generation-feedback.md)：自動生成の手・親指の軸・口内・顎の調整、FBX表示と埋込画像、リグ/揺れもの往復の失敗を次の初回指示へ反映する。
- [最初の制作計画](skills/lida-avatar-workflow/references/production-plan.md)：必要な5項目の診断・補正を計画し、材質の変更範囲、工程順と保留理由を整理する。
- [品質と工程ゴール](skills/lida-avatar-workflow/references/quality-goals.md)：初回の完成像と各工程の終了条件。
- [工程索引](skills/lida-avatar-workflow/references/process-index.md)：今扱う部位の資料だけ選ぶ。
- [アクセサリー・装飾の材質補正](skills/lida-avatar-workflow/references/accessory-materials.md)：画像・材質・形のどこを直すか判断し、銀の艶・宝石・細い輪郭を比較する。
- [メッシュの破綻修正と補完](skills/lida-avatar-workflow/references/mesh-repair-completion.md)：必要な開口を残し、面張り・境界接続・局所再構築・欠落部位の補完を図で選ぶ。
- [使用先とショット間の見た目を揃える](skills/lida-avatar-workflow/references/cross-engine-look.md)：色管理から陰影・艶・輪郭・透過を分けて調整。口内の暗さと羽の暗い縁の診断例も収録。
- [機械検査と見た目・動きの判定](skills/lida-avatar-workflow/references/mechanical-visual-review.md)：CLIで確認漏れを減らし、原画との画像比較・途中動作・保存/使用先を分けて検収する。
- [自作の制作補助ツール](skills/lida-avatar-workflow/references/model-tools.md)：骨構成・人型への割当、網目・UV・ウェイト・キー、修正前後の比較、コピー限定のウェイト正規化と送信FBXの条件確認。
- [Tripoで初期骨格を導入する](skills/lida-avatar-workflow/references/tripo-autorig.md)：150MB以内のFBXを用意し、VRM 1.0オートリグから保持照合・リグとウェイトの調整へ進む。
- [眼球を作る工程](skills/lida-avatar-workflow/references/eye-modeling.md)：球面・虹彩・白目・線の層・視線・瞬き・出力まで。
- [ウインクの閉じ方](skills/lida-avatar-workflow/references/wink-closure.md)：通常の瞬きと笑った閉じ目を分け、目だけの差分・左右・影の層・途中動作を確認する。
- [表情シートを生成する](skills/lida-avatar-workflow/references/expression-sheets.md)：同じ通常顔から必要な口型・目・感情の一覧と単体画像を作り、個別3D参考と局所キーへつなぐ。
- [手を作り、動かして確認する工程](skills/lida-avatar-workflow/references/hand-shape.md)：掌と指の形、関節と網目、親指・指間のウェイト、爪、短縮で繰り返した修正を図で確認。
- [髪を作る工程](skills/lida-avatar-workflow/references/hair-workflow.md)：髪だけの資料、毛束の形と断面、根元・毛先・生え際、質感と艶、揺れ・干渉・出力まで。
- [翼を作る工程](skills/lida-avatar-workflow/references/wing-workflow.md)：資料・支持体・羽列・根元・ウェイト・開閉としなり・保存まで。工程ごとのゴールとAI依頼文付き。
- [翼全体の羽の配置と用語](skills/lida-avatar-workflow/references/wing-feather-terms.md)：初列・次列・三列風切、雨覆、小翼羽、肩羽を上下面の図と番号で対応。
- [図解索引](skills/lida-avatar-workflow/references/diagram-index.md)：素材、網目、表情、手、髪、衣装、翼、統合を画像で確認。
- [画像付きの依頼](skills/lida-avatar-workflow/references/visual-handoff.md)：変更部と固定部、比較・採否をAIへ渡す。

作例の寸法・本数は他モデルの既定値にしません。確認範囲と既知制限も読み、外観の好みは[短いあとがき](skills/lida-avatar-workflow/references/lida-design.md)へ分けます。

## 自作ツールとSkillsを組にして使う

Blenderで実行する制作補助スクリプトを同梱しています。AIは各工程で必要な検査を実行し、JSONと同条件画像から修正・保持結果を判断します。骨と人型対応の`rig-audit`、FBXの形式・容量確認も収録します。機械検査が通っても、画像・動作で不自然なら未達として扱います。ウェイト正規化は新規の候補コピーへ限定します。

[できること・実行方法・確認済みの範囲](skills/lida-avatar-workflow/references/model-tools.md)を参照してください。制作時の常駐アドオン全機能や操作パネル、眼球・翼の自動造形まで一式で導入するものではありません。

## 参考図解

**素材をそろえて3D生成へ進む流れ**。自作模式図です。身体・服・上着の段階別生成は次回向けの予防案で、制作で確認した成功例とは分けています。[素材準備の説明](skills/lida-avatar-workflow/references/input-materials.md)

![同じ基準の画像から段階別素材と三面図をそろえ、粗い3Dへ進む自作模式図](skills/lida-avatar-workflow/assets/input-alignment-flow.png)

**生成した口型を、共通の顔へ反映する考え方**。Tripoの参考モデルを使い、顎と顔の輪郭を固定して口周辺だけを調整します。自作模式図であり、完成モデルの比較画像ではありません。[口型制作の説明](skills/lida-avatar-workflow/references/mouth-shapes.md)

![Tripoの参考モデルから、一つの基準顔の口周辺だけにシェイプキーを作る自作模式図](skills/lida-avatar-workflow/assets/face-key-locality.png)

## 利用と出典表記

**Skillsの文書・図解・手順・補助コードは商用・非商用を問わず利用できます。** 同梱参照モデルは上記のモデル専用条件です。 モデルの販売・受託制作、商用の画像・動画、商用アプリやSkillsへの組込みも制限しません。商用の場合も、下記の出典保持条件は同じです。利用する生成サービス・入力素材・第三者モデルの利用条件は、それぞれ確認してください。

| 利用方法 | 出典の扱い |
| --- | --- |
| 読んで手順を使い、モデル・画像・動画を制作 | その成果物へのクレジットは不要 |
| 本資料を組み込み・改変したアプリや新Skillsを公開 | README・About・NOTICE等へ参照元名・Lida・URL・利用／改変内容を記載 |
| 本資料自体を転載・改変・再配布 | LICENSEとNOTICEを保持 |

方法を参考にした公開アプリやSkillsについても、AIの制作手順では出典を書きます。[利用区分・コピペ例・出典作成ツール](skills/lida-avatar-workflow/references/usage-and-attribution.md)、[正式な利用条件](LICENSE)、[出典情報](NOTICE.md)を確認してください。キャラクターや第三者素材の利用許可とは別です。

## シェーダーは必要な場合だけ取得

トゥーン表現は公開リポジトリ [LidaAngelToon](https://github.com/Lida-V/LidaAngelToon) で別配布しています。[Release 0.2.1からBlender・Unity・UEの導入用ZIPを選ぶ](https://github.com/Lida-V/LidaAngelToon/releases/tag/v0.2.1)ことができます。Skillsでモデルを作るための必須依存ではありません。

確認済み環境はBlender 5.2.1 LTS／EEVEE、Unity 6000.6.0f1／URP 17.6、UE 5.8（Windows）です。シェーダーREADMEではリダ実モデルの3環境の表示例を確認できます。Blenderの制作基準材質と配布アドオンの違い、UEの落ち影などの制限、VRM自動変換が含まれないことは[取得・導入・対応範囲](skills/lida-avatar-workflow/references/shader-setup.md)を参照し、各ファイルのLICENSEも確認してください。

## 同梱範囲

公式の通常ZIPに、文書・自作図解・スキル・補助コードと、制作参照モデルr35・モデル専用条件を同梱します。Blender本体、生成サービス、接続ツール、APIキー、編集原本や他のモデルは同梱しません。
**参考ダンスFBX、改名コピー、変換した参考モーションも配布しません。** 動作確認には、自分で利用権を持つ動きを用意してください。

## 保守と検査

利用者は検査を実行せず読んで使えます。改変・再配布する人は[更新手順](UPDATING.md)、[変更履歴](CHANGELOG.md)、[配布範囲と権利条件](LICENSE-POLICY.md)を確認します。

```sh
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build_package.py
```

GitHub Actionsでも検査とZIP作成を行います。自動検査に加え、追加資料の出所・画像内文字・権利を目視で確認してください。ZIP作成は公開範囲変更や公開リリースを行いません。
