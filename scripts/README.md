# 検査と配布用ZIP

[日本語](README.md) · [English](README.en.md)

`validate.py` は許可した収録物・相対リンク・スキル形式・図版ハッシュを検査する。`build_package.py` は検査後に同じファイル一覧から再現可能なZIPとSHA256を作る。どちらもモデルや外部サービスは変更しない。

詳しい操作は[更新手順](../UPDATING.md)を参照。

完成ZIPにはSkills構成要素の参照VRMを必須同梱します。ソースのみでモデルがない場合は、`python scripts/build_package.py --fetch-reference-model`で、固定した公式ZIPから容量・SHA・メンバーを検証して取得します。通常のbuildはネットへ接続しません。モデルは読むだけで取得・実行されるものではありません。
