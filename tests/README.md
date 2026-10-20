# 検査の動作確認

[日本語](README.md) · [English](README.en.md)

検査が壊れたリンク、ローカルパス、掲載対象外の資料、認証情報、図版の差し替えを止めることと、ZIPが同じ入力から同じ内容になることを確認する。

翻訳の登録表の欠落、英訳の未登録・空ファイル・照合済み原文からの変更、英語出典と既存出典の保持も確認する。これは訳の意味の同等性や見た目を保証する検査ではない。

ライセンスと出典の欠落・不一致、版の不一致、拡張子を変えた参考FBX、画像の偽装、完成ZIPの欠落・追加・重複・内容改変も検査する。スキル単体コピーで条件・出典・ヘルパーが残ることと、ヘルパーのモデル用途・読み込み・確認モードがプロジェクトを書き換えないことを確認する。

```sh
python -m unittest discover -s tests
```

`test_model_tools.py`は通常Pythonで実行できる制作補助ツールの回帰テストです。Blenderなしの読込み・ヘルプ、snapshotのスキーマと差分、未検査項目、既存JSONを上書きしないCLIの契約を確認します。これだけでBlender上のモデル処理を検証したとは扱いません。

配布版のモデル処理は別途、Blender 5.2.1 LTSで合成fixtureの従来のAPI14項目・CLI19項目と、追加したrig-auditのAPI15項目・CLI9項目、合成FBX1件を確認しています。検査範囲と制限は[制作補助ツール](../skills/lida-avatar-workflow/references/model-tools.md#確認済みの範囲)へ。fixtureのblend・実制作モデルは同梱しません。

この制作ワークスペースでは、環境変数 `LIDA_DISTRIBUTION_TEST_TEMP` を制作プロジェクトの `assets/validation/distribution_release20261015/test-temp` へ設定して実行する。未指定の環境では通常の一時領域を使う。各試験はその下の専用一時フォルダだけを整理する。試験用の条件文はfixtureであり、配布物の正式なLICENSEを生成・変更しない。
