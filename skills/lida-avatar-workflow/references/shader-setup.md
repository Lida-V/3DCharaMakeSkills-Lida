# LidaAngelToonの取得と使い分け

[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon)はシェーダーの別リポジトリです。モデル制作の方法を使うだけなら取得は不要。使う見た目とソフトに合わせて選びます。

公開リポジトリの[Release v0.2.1](https://github.com/Lida-V/LidaAngelToon/releases/tag/v0.2.1)から、使用する環境のZIPを選びます。リポジトリの配布版は0.2.1、各実装の版は0.1.0です。ソースZIP全体は開発者向けで、Blenderのアドオン導入には使いません。

| 対象 | 配布するもの・状態 |
| --- | --- |
| Blender | [BlenderアドオンZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-blender-addon.zip)。Blender 5.2.1 LTS／EEVEE、原始図形で適用・復帰・保存再読込を検証。Cyclesや他のBlender版は未対応・未検証 |
| Unity | [Unity用ZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-unity.zip)。Unity 6000.6.0f1／URP 17.6／Linear／Forward+／D3D11、Windowsで実描画を検証。[導入](https://github.com/Lida-V/LidaAngelToon/blob/main/unity/README.md) |
| Unreal Engine | [UE用ZIP](https://github.com/Lida-V/LidaAngelToon/releases/download/v0.2.1/LidaAngelToon-0.2.1-unreal.zip)。UE 5.8／Windowsで実描画を検証。Pythonで材質等を作り、.uassetは収録しない。Unlitで落ち影を受けない。[導入](https://github.com/Lida-V/LidaAngelToon/blob/main/unreal/README.md) |
| VRMのMToon | 別の材質仕様。Blenderの全機能が同じまま移るものではない。実出力を読み戻して比較 |

[READMEのリダ実モデル画像](https://github.com/Lida-V/LidaAngelToon#リダのモデルで見る3つの表示例)は、Blenderの開発基準材質とUnity・UE実装を比較した作例です。Blender列は配布アドオンの実適用ではなく、各エンジン列も専用の材質・画像を設定しています。初期値だけで同じ見た目になる例ではありません。アドオンと共通HLSLの数値一致、未記載のOS/API/版、VRM自動変換は未検証・未収録です。

## Blenderの最短の導入

1. 上表のBlenderアドオンZIPを取得し、[対応範囲](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/SUPPORT.md)と[LICENSE](https://github.com/Lida-V/LidaAngelToon/blob/main/LICENSE)を読む。
2. Blenderの「編集 → プリファレンス → アドオン → ディスクからインストール」で、ZIPを展開せずに選び、有効にする。表示エンジンをEEVEEにする。
3. 球を追加し、3Dビューの `N` キーからLidaAngelToonを開く。`Cloth` → `Apply to selected meshes` → レンダー表示で色と影を確認してから、モデルのコピーへ適用する。元の材質と画像を保持し、同じ光・カメラで全身と必要なアップを比べる。
4. 出力する場合は材質・AO・艶・輪郭線の再現範囲を[読み戻し手順](visual-handoff.md#vrmを読み戻し提出動作を確認する)で確認する。

対象は選択メッシュのアクティブ材質です。導入・主光の選択・元材質への復帰方法はシェーダー側の[導入と更新](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/INSTALL.md)を優先します。Blenderで表示できることを、別の使用先で同じ見た目になる保証にしません。

Skills、Blenderの素材生成器、Unity／UE、VRMの追加機能を一度に導入する必要はありません。対応環境だけを選び、必要な依存物を用意します。参考ダンスFBXやアバターモデルはシェーダーパックにも含めません。

## Unity・UEで始める

UnityはZIP内の`unity/com.github.lida-v.lidaangeltoon`を`.meta`ごと配置し、URPの材質を作って基本色・画像を設定します。UEは`unreal/LidaAngelToon`をContentへ置き、Python Editor Script Pluginを有効にして同梱の構築スクリプトから材質等を作ります。詳しい配置・必要設定は上表の各導入文書を優先してください。

まず原始図形で主光・輪郭・色を確認し、モデルのコピーへ材質を割り当て、全身とアップを比較します。半透明の重なり、輪郭法線、露出・トーン曲線、UEの落ち影の制限も確認します。モデル・画像・材質表は自分で用意し、Blenderの設定が自動で移るとは扱いません。

差が出た時は[使用先ごとの外観調整](cross-engine-look.md)を使います。画像の取り込みと色管理、基本色と影、髪の艶、輪郭と透過の順に確認し、共通素材の修正とエンジン固有の仕様差を分けます。

## 更新と出典

使った版・プリセット・自分の材質変更を控え、戻せるコピーで更新します。原始図形→モデルの同条件比較→保存再読込を確認し、旧版の動画を新版の検証へ流用しません。

モデルや通常の描画成果だけならクレジット不要です。公開アプリや新Skillsへシェーダーを組み込む場合は[出典表記](usage-and-attribution.md)と、シェーダー側のファイル別ライセンスを引き継ぎます。bpyを使うBlenderアドオンはGPL-3.0-or-later、0.2.1のUnity・UE・共通HLSLと文書・自作素材はLida Attribution License 1.1です。UnityパッケージとUEフォルダ内のLICENSE.mdを保持し、ファイル別の対応は同リポジトリLICENSEを優先します。Skills本体の利用条件を変更するものではありません。
