# 3DCharaMakeSkills-Lida

画像から3Dキャラクターを作るときの、素材・調整方法・AIへの指示をまとめた **配布版1.0.0** です。初心者向けに「素材→順番→具体調整→つまずき」を整理し、13枚の自作図解をPNG／SVGで収録しています。リポジトリは現在Privateです。

## 入手して使う

1. このリポジトリの **Code → Download ZIP** で取得して展開します。配布ZIPを受け取った場合も展開します。
2. `skills/lida-avatar-workflow` を、参照文書・画像・LICENSE・NOTICE・補助スクリプトを含め、エージェントのスキル保存先へ丸ごとコピーします。`SKILL.md`だけにしないでください。
3. スキルを読み込ませ、次の導入確認を依頼します。読むだけの利用者にPythonやシェーダーの導入は必要ありません。

> lida-avatar-workflowを読み、モデル制作を始める前に、必要な素材・推奨する品質・最初の工程のゴールを短く提案してください。実サービスの実行はまだ不要です。

名前付き指定が使える環境では `$lida-avatar-workflow` と指定できます。読み込めない時は、保存先・同名スキルの重複・参照文書や画像の欠落を確認してください。[利用者向け更新手順](UPDATING.md#利用者の更新)も用意しています。

## 最初に読む

- [品質と工程ゴール](skills/lida-avatar-workflow/references/quality-goals.md)：初回の完成像と各工程の終了条件。
- [工程索引](skills/lida-avatar-workflow/references/process-index.md)：今扱う部位の資料だけ選ぶ。
- [図解索引](skills/lida-avatar-workflow/references/diagram-index.md)：素材、網目、表情、手、髪、衣装、翼、統合を画像で確認。
- [画像付きの依頼](skills/lida-avatar-workflow/references/visual-handoff.md)：変更部と固定部、比較・採否をAIへ渡す。

作例の寸法・本数は他モデルの既定値にしません。確認範囲と既知制限も読み、外観の好みは[短いあとがき](skills/lida-avatar-workflow/references/lida-design.md)へ分けます。

## 利用と出典表記

| 利用方法 | 出典の扱い |
| --- | --- |
| 読んで手順を使い、モデル・画像・動画を制作 | その成果物へのクレジットは不要 |
| 本資料を組み込み・改変したアプリや新Skillsを公開 | README・About・NOTICE等へ参照元名・Lida・URL・利用／改変内容を記載 |
| 本資料自体を転載・改変・再配布 | LICENSEとNOTICEを保持 |

方法を参考にした公開アプリやSkillsについても、AIの制作手順では出典を書きます。[利用区分・コピペ例・出典作成ツール](skills/lida-avatar-workflow/references/usage-and-attribution.md)、[正式な利用条件](LICENSE)、[出典情報](NOTICE.md)を確認してください。キャラクターや第三者素材の利用許可とは別です。

## シェーダーは必要な場合だけ取得

トゥーン表現を使いたい場合は、別リポジトリ [LidaAngelToon](https://github.com/Lida-V/LidaAngelToon) を取得します。Skillsでモデルを作るための必須依存ではありません。
Blender版0.1.0と、Unity／UEへの移植状況を分けて案内します。[取得・導入・対応範囲](skills/lida-avatar-workflow/references/shader-setup.md)とシェーダー側のLICENSEを確認してください。

## 同梱範囲

文書・自作図解・スキル・補助コードを配布します。Blender本体、生成サービス、接続ツール、APIキー、モデル本体、受領原本は同梱しません。
**参考ダンスFBX、改名コピー、変換した参考モーションも配布しません。** 動作確認には、自分で利用権を持つ動きを用意してください。

## 保守と検査

利用者は検査を実行せず読んで使えます。改変・再配布する人は[更新手順](UPDATING.md)、[変更履歴](CHANGELOG.md)、[配布範囲と権利条件](LICENSE-POLICY.md)を確認します。

```sh
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build_package.py
```

GitHub Actionsでも検査とZIP作成を行います。自動検査に加え、追加資料の出所・画像内文字・権利を目視で確認してください。ZIP作成は公開範囲変更や公開リリースを行いません。
