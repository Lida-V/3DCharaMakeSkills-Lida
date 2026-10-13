# 制作で得た学びを更新する

## 普段の更新

1. 制作の正本に結果を残す。[初回の品質案と工程開始時のゴール](skills/lida-avatar-workflow/references/quality-goals.md)、入力版、依頼文、失敗理由、変更範囲、画像、採否、未検証を分け、終了時に達成・未達を追記する。
2. このリポジトリへ、再利用できる方法だけ抜き出す。初心者向けには「素材→順番→調整→つまずき」を短く、詳細は専用文書にまとめ、工程索引からリンクする。
3. 図版を足すときは画像内の文字、モデルの出所、比較の左右、姿勢、採否を目視で確認する。外部モデルや名称を含む比較資料は載せない。
4. `CHANGELOG.md` を更新し、配布版を変えるときは `VERSION` も更新する。新しいファイル/図版は `publication-manifest.json` の一覧と画像ハッシュへ追加する。
5. READMEに記載した3コマンドを実行する。図の修正は同じ姿勢・距離の見え方も確認する。
6. GitHubの作業ブランチへ更新し、PRで差分と検査結果を確認してmainへまとめる。個人の小さな訂正はmainへの通常コミットでもよい。既存履歴は書き換えない。

## GitHubの画面で更新する

対象ファイルの編集、または対象フォルダの **Add file → Upload files** を使う。フォルダ名を保ち、ローカルの制作プロジェクト全体を選ばない。コミット後は **Actions → Validate distribution pack** の成功を確認する。失敗した場合はログに表示されたファイルと理由を直す。

## Gitから更新する

LidaのアカウントでGitHubの通常の認証を済ませてから、この非公開リポジトリをcloneする。認証情報をファイル・コマンド本文・リポジトリURLに埋め込まない。

```sh
git clone https://github.com/Lida-V/3DCharaMakeSkills-Lida.git
cd 3DCharaMakeSkills-Lida
git switch -c docs/improve-workflow
# 制作メモから確認済みの学びを編集し、READMEの検査コマンドを実行
git add README.md CHANGELOG.md VERSION skills scripts tests publication-manifest.json
git commit -m "docs: improve avatar workflow"
git push -u origin docs/improve-workflow
```

この作業には、モデル本体の再生成・公開範囲の変更・新しい認証権限の発行は含まれない。

## 配布前

通常形、表情、変形、保存、使用先の確認を別々に記す。新しいモデルの検査を古い成功例で代用しない。[配布条件](LICENSE-POLICY.md)を決定し、Lida固有の好みはあとがきへ短く残す。最終ZIPを展開して、スキルと参照図のリンクも確認する。

公開リリースは明示的に決めてから作成する。タグは `v0.1.0` のようにVERSIONと対応させ、変更履歴と未検証範囲を添える。GitHub ActionsはZIPを作るだけで、公開操作は行わない。
