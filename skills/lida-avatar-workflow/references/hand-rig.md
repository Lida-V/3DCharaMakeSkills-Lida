# 手の関節・ロール・ウェイトを、形から測って置く

[日本語](hand-rig.md) · [English](en/hand-rig.md)

[工程索引](process-index.md) · [同梱ツール](model-tools.md) · [手を作る](hand-shape.md)

**手の形を直したり作り直したりした後に、指の関節の位置、曲げる向き（ロール）、指ごとのウェイトを、毎回手作業で合わせ直さずに済ませる方法です。** 同梱の [lida_hand_rig.py](../scripts/lida_hand_rig.py) が手のメッシュを測って関節を置き、握る姿勢で曲げて、指どうしの交差・指の中の折れ・伸びた辺を数えます。人が見るのは、報告で「推定」と出た関節と、曲げた画像です。

入力の blend は読むだけで、保存しません。`place` は新しい blend に書き出します。

## 使う場面と、使わない場面

| 状況 | 行うこと |
| --- | --- |
| 手の形を直した。今の骨が新しい形に合っているか知りたい | `measure` で関節を測り、今の骨との差を見る |
| 指の骨・ロール・ウェイトを形に合わせて置き直したい | `place` で写しに書き出す |
| 握る・指さし・つまむで、指が交差しないか、折れないか確かめたい | `check` で曲げて数える。前後の版で比べる |
| 親指が短い・指が細いなど、形そのものの問題 | [手を作る](hand-shape.md)で形を直してから使う。関節とウェイトでは直らない |
| 爪・手袋・指輪のように指の骨についていく別のメッシュ | このツールはウェイトを作り直さない。[ウェイトと網目](mesh-weight.md)で合わせる |

## 考え方

### 1　指を表面のつながりで分ける

手首から表面に沿った距離を測り、指先から手のひらへ向かって枝が合流する所で 5 本に分けます。光線や「いちばん近い点」で探すと、指が近い所で隣の指を拾うので、表面のつながりだけで分けます。手の甲の向きは、左右・指の向き・親指の側から決めるので、骨の名前や軸を当て推量しません。

### 2　関節は、形に出ている所を読む

指ごとに、指の軸に垂直な断面を細かく切り、各断面で次を測ります。

- 手のひら側のしわ（手のひら側の面がへこむ所）
- 甲側の関節のふくらみ
- 網目の輪が集まる所（四角い網目では関節に輪が集まる）

高さは指の軸の線から測ります。断面の中心から測ると、しわで中心も動いて、しわと関節のふくらみが打ち消し合います。

人の手のおおよその比（基節：中節：末節 ＝ 約 1 : 0.6 : 0.45）から各関節の見込みの位置を決め、その近くでいちばん強い特徴を選びます。特徴が弱ければ見込みの位置を使い、報告に `prior`（推定）と書きます。付け根の関節（MCP）は手のひらの中にあって形に出にくいので、たいてい推定になります。付け根が推定の時は、PIP と DIP を組で探し、指先寄りの部分の割合が指らしいか（指先〜DIP が指先〜PIP の 3〜6.5 割）で選びます。

### 3　曲げる向きを、手首の中心へ少し寄せる

各骨のロールを、曲げると指が手のひらへ巻き込み、指先ほど手首の中心へ少し寄るように決めます（`--converge`）。強すぎると薬指が中指へ入ります。親指は、手の長さの軸のまわりに手のひらへ向けてから曲げ、つまむ姿勢で人差し指に届き、握る姿勢で他の指を突き抜けないロールを探します。

### 4　ウェイトを指の鎖で作り直す

`place` は（`--keep-weights` がなければ）手のウェイトを、指に沿った鎖として作り直します。関節では指の太さに合わせた幅でなめらかに切り替え（`--joint-band`）、手首の先では元のウェイトへなじませます（`--fade-mm`）。

### 5　曲げて数える

`check` は、くつろぎ・軽く握る・握る・指さし・つまむ・開く・親指を手のひらへ、の 7 姿勢を、途中の段階も含めて曲げます。曲げは休みの形とウェイトから計算した線形スキニングで、握る姿勢だけ Blender 自身の変形とも比べて、差を報告します。数えるもの：

- 指どうしの交わる線（休みにもあった分を引く）
- 指の中の折れ（指が自分に食い込む）
- 指先が手のひらに入る所（参考。握れば入るのが普通）
- 休みの長さより伸びた辺
- 親指から人差し指までの距離（つまむ・握る）

## 用意するもの

- 保存済みの blend（読むだけ）。開いている制作ファイルは直接使わず、保存した版か写しを指定する。
- 手の肌を持つメッシュの名前（`--mesh`。体と一体のことが多い）。
- 骨組みの名前（`--rig`）と、人型の骨の対応表（`--bones`）。[同梱ツール](model-tools.md)の `rig-audit` と同じ形の JSON で、`human_bones` に VRM の役割名（`leftHand`・`leftIndexProximal` など）と骨の名前を対応させる。骨がない時の `measure` は `--wrist` と `--toward` で手首と指の向きを与える。
- 新しい報告の JSON と、`place` なら新しい blend、画像が要るなら新しいフォルダ。どれも既にあると止まる。
- Blender（背景実行）。計算部分は通常の Python と numpy だけで動く。

## AI が行う順序

1. 手の形がそろっていることを確かめる（形の直しが先。[手を作る](hand-shape.md)）。
2. `measure` を実行し、関節ごとの `method`（`mesh`／`prior`）と、今の骨との差を読む。推定の関節は画像で位置を見る。
3. 今の骨で `check` を実行し、前の状態を残す。
4. `place` で写しに書き出す。親指のロールは `auto` で探す。
5. 書き出した写しで同じ `check` を実行し、交差・折れ・伸びた辺が減ったか、新しく出た所がないかを比べる。
6. 画像を自分の目で見て、数値と合っているか、握った形が自然かを確かめる。
7. 結果・画像・限界をユーザーへ示す。爪や手袋など、指についていく別のメッシュは別に合わせる。

## 実行例

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- measure --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report measure.json --render-dir measure_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_before.json --render-dir check_before_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- place --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report place.json --output-blend model_hands.blend

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_hands.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_after.json --render-dir check_after_views
```

## 報告の読み方

### measure・place

- `hands.<左右>.fingers.<指>.joints`：関節ごとの位置（骨組みの座標）、`method`（`mesh` は形から、`prior` は推定、`tip` は指先、`estimated` は親指の付け根の計算値）、`score` と `features`（しわ・ふくらみ・輪の強さ）、`from_web_mm`（指の股からの距離）、`current_bone_offset_mm`（今の骨との差）。
- `back_of_hand`：測った手の甲の向き。
- `place` では、`thumb_roll_deg`（選んだ親指のロール）と `flex_sign`（どちらへ回すと指が曲がるか）。`--z-toward` で骨の Z を手のひらへ向けるか甲へ向けるかを選ぶ。

### check

- `poses`：姿勢ごとの `crossings`（組ごとの交わる線の長さ・箇所の数・いちばん長かった段階 `at`・種類 `kind`）、`stretched_edges_max`、`thumb_to_index_mm` または `thumb_to_index_tip_mm`。
- `kind` は `fingers`（指どうし）、`fold`（指の中の折れ）、`palm`（指先が手のひらに入る。警告にしない）。
- `blender_vs_numpy_fist_mm`：握る姿勢での Blender の変形との差。0.5mm を超えると警告。ほかのモディファイア・シェイプキー・体積保持があると数値の読み方に注意。
- `weights_in_hand.vertices_without_hand_weights`：手の範囲で骨のウェイトがない頂点の数。

### 終了コード

| 値 | 意味 |
| --- | --- |
| 0 | 警告なし |
| 2 | 見つかった、または警告がある。報告を読んで判断する。使い方の誤りも 2 で、この時は JSON を作らない |
| 1 | 入力・出力・実行の誤り。報告の JSON に理由が入る |

## 主なオプション

| オプション | 既定 | 働き |
| --- | --- | --- |
| `--window` | 0.10 | 見込みの位置の前後、指の長さのこの割合の中で関節を探す |
| `--feature-floor` | 0.12 | 形を推定より信じるのに要る特徴の強さ |
| `--mcp-prior`・`--pip-prior`・`--dip-prior` | 0.25・0.49・0.78 | 関節の見込みの位置（付け根は指の股から手首側へ見える長さの割合、PIP・DIP は付け根〜指先の割合） |
| `--thumb-mcp-prior`・`--thumb-ip-prior` | 0.02・0.55 | 親指の関節の見込みの位置 |
| `--thumb-metacarpal` | 1.35 | 親指の中手骨の長さ（基節の何倍か） |
| `--converge` | 0.3 | 曲げた指先を手首の中心へ寄せる強さ（0〜1） |
| `--joint-band` | 1.0 | 関節でのウェイトの切り替えの半幅（指の太さの何倍か）。狭いと関節が折れる |
| `--fade-mm` | 15 | 手首の先で元のウェイトへなじませる距離 |
| `--smooth` | 4 | 新しいウェイトをならす回数 |
| `--steps` | 4 | 姿勢ごとに途中を調べる段階の数 |
| `--stretch`・`--stretch-mm` | 1.5・3 | 休みの長さのこの倍より長く、かつこの長さ以上伸びた辺を「伸びた」と数える |
| `--cross-tolerance-mm` | 1 | これより短い交わる線は警告しない |
| `--poses`（check） | 7 姿勢 | 調べる姿勢を選ぶ |
| `--keep-weights`（place） | なし | 骨の位置とロールだけを直し、ウェイトは変えない |
| `--thumb-roll`（place） | auto | 親指のロール。数値で角度を指定もできる |

既定の値は作例で、どのモデルにも合う値ではありません。

## AI への依頼文の例

```text
保存済みの <版> を読むだけで、<左右> の手を lida_hand_rig.py で調べてください。
- メッシュ <名前>、骨組み <名前>、人型の対応表 <JSON>。
- まず measure と、今の骨での check。次に place で <新しい blend> へ書き出し、同じ check で前後を比べてください。
- 報告と画像は <新しいフォルダ> へ。入力は保存しないでください。
- 結果は、推定になった関節、交差・折れ・伸びた辺の前後、画像を見て数値と合わなかった所、限界を分けて報告してください。
- 爪 <名前> などのウェイトは別に合わせます。勝手に変えないでください。
```

## 確認済みの範囲

- Blender 5.3.0 の背景実行で、別の制作の保存済みファイルの写しを読むだけで `measure`・`place`・`check` を実行した。PIP と DIP は、手で合わせた骨と多くの指で 1mm 前後で一致した。書き出した写しでは、握る・指さしの伸びた辺が手で合わせた版より減り、親指の付け根のつぶれもなくなった。入力は変わらない。
- 通常 Python のテストで、合成の手を使って、指の分け方、左右の鏡写し、しわからの PIP・DIP、曲げる向き、ウェイトの鎖、線形スキニング、既存出力の保護を確かめている。

未確認：小指のように形に関節が出にくい指で推定と手作業のどちらが正しいか（画像で見る）、握った形の自然さ、ほかの Blender 版、体積保持のスキニング、使用先での見え方。作例の数を品質の基準にしません。

## 利用条件

`lida_hand_rig.py` は GPL-3.0-or-later です（著作者 Lida）。[同梱ツールの利用条件](model-tools.md#利用条件と導入範囲)と同じ扱いで、GPL 本文とファイル冒頭の表示を保持します。この文書は[利用区分とクレジット](usage-and-attribution.md)に従います。
