# LidaAngelToonの取得と使い分け

[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon)はシェーダーの別リポジトリです。モデル制作の方法を使うだけなら取得は不要。使う見た目とソフトに合わせて選びます。

公開リポジトリの[Release v0.1.0](https://github.com/Lida-V/LidaAngelToon/releases/tag/v0.1.0)から取得できます。通常の利用は **[lida_angel_toon-0.1.0-addon.zip](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.1.0/lida_angel_toon-0.1.0-addon.zip)** を選びます。ソースZIPは開発者向けで、アドオンの導入には使いません。

| 対象 | 配布するもの・状態 |
| --- | --- |
| Blender | 0.1.0。Blender 5.2.1 LTS／EEVEEで検証済み。汎用材質に適用するノード・アドオン、自作の手続き素材。Cyclesや他のBlender版は未対応・未検証 |
| VRMのMToon | 別の材質仕様。Blenderの全機能が同じまま移るものではない。実出力を読み戻して比較 |
| Unity／UE | この配布版に実装は含まれず、未対応・未検証。VRMへの自動変換も収録しない |

## 最短の導入

1. 上記のaddon ZIPを取得し、[対応範囲](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/SUPPORT.md)と[LICENSE](https://github.com/Lida-V/LidaAngelToon/blob/main/LICENSE)を読む。
2. Blenderの「編集 → プリファレンス → アドオン → ディスクからインストール」で、ZIPを展開せずに選び、有効にする。表示エンジンをEEVEEにする。
3. 球を追加し、3Dビューの `N` キーからLidaAngelToonを開く。`Cloth` → `Apply to selected meshes` → レンダー表示で色と影を確認してから、モデルのコピーへ適用する。元の材質と画像を保持し、同じ光・カメラで全身と必要なアップを比べる。
4. 出力する場合は材質・AO・艶・輪郭線の再現範囲を[読み戻し手順](visual-handoff.md#vrmを読み戻し提出動作を確認する)で確認する。

対象は選択メッシュのアクティブ材質です。導入・主光の選択・元材質への復帰方法はシェーダー側の[導入と更新](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/INSTALL.md)を優先します。Blenderで表示できることを、別の使用先で同じ見た目になる保証にしません。

Skills、Blenderの素材生成器、Unity／UE、VRMの追加機能を一度に導入する必要はありません。対応環境だけを選び、必要な依存物を用意します。参考ダンスFBXやアバターモデルはシェーダーパックにも含めません。

## 更新と出典

使った版・プリセット・自分の材質変更を控え、戻せるコピーで更新します。原始図形→モデルの同条件比較→保存再読込を確認し、旧版の動画を新版の検証へ流用しません。

モデルや通常の描画成果だけならクレジット不要です。公開アプリや新Skillsへシェーダーを組み込む場合は[出典表記](usage-and-attribution.md)と、シェーダー側のファイル別ライセンスを引き継ぎます。Blender APIを使うアドオンと、文書・自作素材の条件は同リポジトリLICENSEの対応表を確認してください。
