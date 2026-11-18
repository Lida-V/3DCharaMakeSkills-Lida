# 手の関節・ロール・ウェイトを、形から測って置く

[日本語](hand-rig.md) · [English](en/hand-rig.md)

[工程索引](process-index.md) · [同梱ツール](model-tools.md) · [手を作る](hand-shape.md)

**手の形を直したり作り直したりした後に、指の関節の位置、曲げる向き（ロール）、指ごとのウェイトを、毎回手作業で合わせ直さずに済ませる方法です。** 同梱の [lida_hand_rig.py](../scripts/lida_hand_rig.py) が手のメッシュを測って関節を置き、握る姿勢で曲げて、指どうしの交差・指の中の折れ・伸びた辺を数えます。前後は数値で比べ、画像は必要な時だけ描きます。人が見るのは、報告で「推定」と出た関節と、警告が残った姿勢の画像です。

入力の blend は読むだけで、保存しません。`place` と `run` は新しい blend に書き出します。

## 使う場面と、使わない場面

| 状況 | 行うこと |
| --- | --- |
| 手が大きい・手のひらが長い・親指が届かないなど、形の比を確かめたい | `measure` の `proportions` を読む。手の中の比と、頭・前腕・身長との比が出る |
| 手の形を直した。今の骨が新しい形に合っているか知りたい | `measure` で関節を測り、今の骨との差を見る |
| 指の骨・ロール・ウェイトを形に合わせて置き直したい | `place` で写しに書き出す |
| 握る・指さし・つまむで、指が交差しないか、折れないか確かめたい | `check` で曲げて数える。前後の版で比べる |
| 直す前と後、または前の版と今の版で、良くなったか悪くなったかを知りたい | `compare` で 2 つの報告を比べる。描画なし |
| 承認済みの版より悪くなった所だけを知りたい | `check --accept` に、承認済みの版の `check` の報告を渡す |
| 骨の対応表（JSON）が無い | `bones` で骨組みから作る |
| 測る・置く・確かめる・比べるを一度に行いたい | `run`。画像は既定で作らない |
| 親指が短い・指が細いなど、形そのものの問題 | [手を作る](hand-shape.md)で形を直してから使う。関節とウェイトでは直らない |
| 爪のように、指についていく固い部品 | `place --rigid-followers` で、部品ごとに真下の骨 1 本へ付け直す。`check --followers` でずれを測る |
| 手袋・指輪など、やわらかい物や複数の骨にまたがる物 | このツールはウェイトを作り直さない。[ウェイトと網目](mesh-weight.md)で合わせる |

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

### 3　手の比を、手の中と体の両方で測る

`measure` は関節と一緒に、形の比を出します。

| 比 | 測り方 | 人の手の目安 |
| --- | --- | --- |
| 手のひら ÷ 手の長さ `palm_share` | 手首から中指の股まで ÷ 手首から中指の先まで | 約 0.57 |
| 手のひらの長さ ÷ 幅 `palm_length_per_width` | 幅は指の付け根の手前で測る | 約 1.25 |
| 親指の届く位置 `thumb_reach` | 親指の先 ÷ 手のひらの長さ（手の向きに沿って）。1 未満は指の股に届かない | 約 1.15 |
| 親指 ÷ 人差し指 `thumb_per_index` | 見える長さどうし | 約 0.67 |
| 手 ÷ 前腕 `hand_per_forearm` | 前腕は骨のひじから手首まで | 約 0.73 |
| 手 ÷ 頭の高さ `hand_per_head` | 頭は `--head-meshes`（髪や冠のない頭）の頭頂からあごまで | 約 0.78 |
| 頭身 `heads`・手 ÷ 身長 | 身長は `--body-meshes` の高さ（立った休みの姿勢、上が Z） | 7.5 頭身・約 0.108 |

手の中の比は頭身にあまり左右されませんが、手の大きさは頭身と絵柄で変わります。頭身の低いデザインは、頭に対して手が小さく、人の値から外れるのが普通です。だから人の値は参考として並べるだけにし、警告の幅はオプションにしています。デザイン画の比が決まっているなら、その値で幅を指定します。

- 手首は、指定した手首の点（骨があれば手の骨の根元）から測ります。メッシュがいちばん細くなる位置との差を `narrowest_wrist_section_mm` に出すので、手首の骨が前腕側や手のひら側にずれていないかを見ます。
- 頭の高さと身長は、名前で指定したメッシュから測ります。指定しなければ測らず、`notes` にそう書きます。数値で直接渡すこともできます（`--head-height-mm`・`--height-mm`）。
- 脚のない体（尾など）では、身長と頭身は人と同じ意味になりません。頭と前腕との比を主に使います。

### 頭身ごとの手の大きさの表

手の大きさは、頭身に合わせた表（手の長さ ÷ 頭の高さ）と比べます。頭身は、測った身長 ÷ 頭の高さか、`--heads` で渡したデザインの頭身を使います。

| 頭身 | 手 ÷ 頭の高さ | 手 ÷ 身長（同じ値を身長で言い直したもの） | 出どころ |
| --- | --- | --- | --- |
| 3 | 0.30 | 約 10% | 一般的な目安（測っていない） |
| 4 | 0.36 | 約 9% | 一般的な目安（測っていない） |
| 5 | 0.42 | 約 8.4% | 一般的な目安（測っていない） |
| 6 | 0.46 | 約 7.7% | 測定：様式化したデザイン画 1 点とそのモデル |
| 7 | 0.64 | 約 9.1% | 測定：アニメ調の作例の手 ÷ 身長。頭身は仮定 |
| 7.5 | 0.81 | 約 10.8% | 成人の人体 |
| 8 | 0.86 | 約 10.8% | 成人の人体 |

**この表は出発点で、決まりではありません。** 測定に基づくのは下の 4 行だけで、そのうち様式化した絵柄の行は作例が 1〜数点です。同じ頭身でも絵柄で手の大きさは変わります（6 頭身と 7 頭身の間の差が大きいのは、作例の絵柄が違うためです）。行の間は直線で補い、表の外は端の行を使います。報告の `basis` に、使った行の出どころが出ます。

合わせ方は 4 通りあります。

| したいこと | 方法 |
| --- | --- |
| デザイン画の頭身で判断したい（尾や高い靴で身長が変わる時も） | `--heads 6` |
| 許す幅を広げる・狭める（既定は表の値の ±15%） | `--proportion-tolerance 0.25` |
| 自分の作品の表を使う | `--proportion-table 表.json`（下の形） |
| 表を使わず、幅を直接決める | `--hand-head-min 0.4 --hand-head-max 0.6` |

```json
[
  {"heads": 5, "hand_per_head": 0.50, "basis": "自分のデザイン画"},
  {"heads": 7, "hand_per_head": 0.60, "basis": "自分のデザイン画"}
]
```

デザイン画で手と頭を測った値があるなら、それを表にして渡すのがいちばん確かです。1 行だけの表でも使えます（どの頭身でもその値になります）。表から外れても、デザインとして意図した大きさなら直す必要はありません。

### 4　曲げる向きを、手首の中心へ少し寄せる

各骨のロールを、曲げると指が手のひらへ巻き込み、指先ほど手首の中心へ少し寄るように決めます（`--converge`）。強すぎると薬指が中指へ入ります。親指は手のひらへ向かってではなく、手のひらを横切る向きに曲がります。曲がる向きを「手のひら側」と「小指側」の間（45°、`--thumb-roll` で小指側へ足す）に置き、握る姿勢とつまむ姿勢の両方で親指がいちばん届くロールを探します。

### 5　ウェイトを指の鎖で作り直す

`place` は（`--keep-weights` がなければ）手のウェイトを、指に沿った鎖として作り直します。関節では指の太さに合わせた幅でなめらかに切り替え（`--joint-band`）、手首の先では元のウェイトへなじませます（`--fade-mm`）。

### 6　爪を指先の骨へ付け直す

`--rigid-followers` に爪などのメッシュを指定すると、つながった 1 かたまり（爪 1 枚）ごとに、真下の肌がいちばん従っている骨 1 本へウェイト 1 で付け直します。爪の真下の肌も同じ骨にそろえるので、指を曲げても爪が肌の上をすべりません。この手から離れたかたまり（反対の手の爪など）は変えません。

### 7　曲げて数える

`check` は、くつろぎ・軽く握る・握る・指さし・つまむ・開く・親指を手のひらへ、の 7 姿勢を、途中の段階も含めて曲げます。曲げは休みの形とウェイトから計算した線形スキニングで、握る姿勢だけ Blender 自身の変形とも比べて、差を報告します。

親指の角度は決まった数値を使わず、その手ごとに解きます。握る・軽く握る・指さしでは親指の先が曲げた指の外側に乗る所、つまむでは人差し指の先、親指を手のひらへでは小指の先を目標にし、「どれだけ丸めるか（3 つの関節を決まった割合で一緒に）」と「付け根をどれだけ手のひらへ向けるか」の 2 つだけを探します。指や手のひらを突き抜ける形は選びません。届かなかった距離は報告に出ます。

数えるもの：

- 指どうしの交わる線（休みにもあった分を引く）
- 指の中の折れ（指が自分に食い込む）
- 指先が手のひらに入る所（参考。握れば入るのが普通）
- 休みの長さより伸びた辺
- 親指から人差し指までの距離（つまむ・握る）と、親指が目標に届かなかった距離
- `--followers` に指定した爪などが、真下の肌に対して動いた量

### 8　前後を数値で比べる

`compare` は、2 つの `measure` の報告、または 2 つの `check` の報告を読み、値ごとに比べます。Blender も描画も使いません。

- `check` どうし：交わる線・伸びた辺・親指が届かなかった距離・爪のずれは、どれも小さいほど良い値です。許す幅（既定は長さ 0.5mm・数 0）を超えて増えた値を `worse`、減った値を `better` に並べます。
- `measure` どうし：長さと比に良し悪しは付けず、変わった値を `changed` に並べます。新しく出た警告だけを問題として数えます。
- 片方の報告にしかない手や姿勢は `not_compared` に出ます。

承認済みのモデルでも、生の警告は残ります（握れば指先は手のひらに入り、辺は伸びます）。見た目を了承した版の `check` の報告を `check --accept` に渡すと、その報告より悪くなった値と、新しい種類の警告だけが残ります。元の警告は `accept.warnings_without_accept` に全部残ります。基準にする報告は、画像で見て了承した版から作ります。

### 9　骨の対応表を、骨組みから作る

`bones` は、骨組みが持っている情報から対応表（`--bones` に渡す JSON）を書き出します。読む順番：

1. VRM アドオンが骨組みに保存した人型の割り当て。アドオンを読み込まない背景実行でも、ファイルに残っていれば読みます。
2. 骨の名前。thumb・index・middle・ring・little（pinky）と、左右の印（Left・L など）を読みます。番号の名前でも言葉の名前でも、親子の深さの順に 3 本を選びます。
3. 手の骨は、指の鎖が集まる骨。腕は名前で探し、無ければ手の親をたどります。
4. 指の名前が読めない時は、名前の付いた手の骨の下にある 5 本の鎖を、位置で親指から順に並べます。この時は注意が出ます。対応表を確かめてから使います。

報告の `methods` に、役割ごとの決め方が出ます。出力は `rig-audit` が読む形と同じです。

### 10　一度に実行する

`run` は、対応表（`--bones` が無い時）→ `measure` → 今の骨での `check` → `place` → 置き直した後の `check` → `compare` を、1 回の起動で行い、新しいフォルダ 1 つへ書き出します。

画像は、既定では作りません（`--views none`）。数値で通れば、描画は要りません。

| `--views` | 描く物 |
| --- | --- |
| `none`（既定） | 描かない |
| `findings` | 置き直した後に警告が残った手と姿勢だけ。前と後を左右に並べる（左が前。画像の中に BEFORE・AFTER の札）。警告が無ければ 1 枚も描かない |
| `all` | 全部の姿勢。前と後を左右に並べる |

描画は簡易表示（Workbench、640px）です。画像が要るのは、選んでもらう時、最初の 1 回の見た目の了承、数値は通ったのに形がおかしい時です。

## 用意するもの

- 保存済みの blend（読むだけ）。開いている制作ファイルは直接使わず、保存した版か写しを指定する。
- 手の肌を持つメッシュの名前（`--mesh`。体と一体のことが多い）。
- 骨組みの名前（`--rig`）と、人型の骨の対応表（`--bones`）。[同梱ツール](model-tools.md)の `rig-audit` と同じ形の JSON で、`human_bones` に VRM の役割名（`leftHand`・`leftIndexProximal` など）と骨の名前を対応させる。対応表が無ければ `bones` で作る（`run` は `--bones` を省くと骨組みから作る）。骨がない時の `measure` は `--wrist` と `--toward` で手首と指の向きを与える。
- 新しい報告の JSON と、`place` なら新しい blend、画像が要るなら新しいフォルダ。`run` は新しいフォルダ 1 つ。どれも既にあると止まる。
- Blender（背景実行）。計算部分は通常の Python と numpy だけで動く。

## AI が行う順序

1〜5 は `run` で一度に実行できます。対応表が無ければ `bones` で作り（`run` は自動）、報告の `methods` を読みます。

1. 手の形がそろっていることを確かめる（形の直しが先。[手を作る](hand-shape.md)）。
2. `measure` を実行し、まず `proportions` と形の警告を読む。手のひらが長い・親指が届かないなどが出たら、関節を置く前にユーザーへ伝える（形を直すと関節も置き直しになる）。次に関節ごとの `method`（`mesh`／`prior`）と、今の骨との差を読む。推定の関節は画像で位置を見る。
3. 今の骨で `check` を実行し、前の状態を残す。
4. `place` で写しに書き出す。親指のロールは `auto` で探す。爪があれば `--rigid-followers` に指定する。
5. 書き出した写しで同じ `check` を実行し、`compare` で前後を比べる。`worse` に出た所は、置き直した後の方が悪い所。
6. 画像は、警告が残った姿勢・ユーザーに選んでもらう時・最初の見た目の了承の時に描く。描いた画像は自分の目で見て、数値と合っているか、握った形が自然かを確かめる。
7. 結果・画像・限界をユーザーへ示す。手袋など、やわらかい別のメッシュは別に合わせる。親指が短いという警告が出たら、形の問題として伝える。

## 実行例

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- measure --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report measure.json --render-dir measure_views --head-meshes Head --body-meshes Body Head

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_before.json --render-dir check_before_views

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- place --input model.blend --mesh Body --rig Armature --bones humanoid.json --side both --report place.json --output-blend model_hands.blend --rigid-followers Nails

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_hands.blend --mesh Body --rig Armature --bones humanoid.json --side left --report check_after.json --render-dir check_after_views --followers Nails
```

対応表を作る、一度に実行する、前後を比べる、承認済みの版を基準にする：

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- bones --input model.blend --rig Armature --report bones_report.json --output-map humanoid.json

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- run --input model.blend --mesh Body --rig Armature --side both --out-dir hands_run --rigid-followers Nails --views findings

python lida_hand_rig.py compare --before check_before.json --after check_after.json --report compare.json

blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python lida_hand_rig.py -- check --input model_next.blend --mesh Body --rig Armature --bones humanoid.json --side both --followers Nails --accept check_approved.json --report check_next.json
```

`compare` は Blender を使わないので、通常の Python（numpy が要ります）で実行できます。

## 報告の読み方

### measure・place

- `hands.<左右>.fingers.<指>.joints`：関節ごとの位置（骨組みの座標）、`method`（`mesh` は形から、`prior` は推定、`tip` は指先、`estimated` は親指の付け根の計算値）、`score` と `features`（しわ・ふくらみ・輪の強さ）、`from_web_mm`（指の股からの距離）、`current_bone_offset_mm`（今の骨との差）。
- `back_of_hand`：測った手の甲の向き。
- `proportions.hand`：手の中の長さ（mm）と比。`proportions.body`：前腕・上腕・頭の高さ・身長と、手との比、頭身。`human_reference`：人の値（参考）。`table`：使った頭身、表の値と幅、その頭の高さでの手の長さの目安（mm）、行の出どころ。`notes`：測れなかった項目と、表を使わなかった理由。
- `place` では、`thumb_roll_deg`（選んだ親指のロール）と `flex_sign`（どちらへ回すと指が曲がるか）。`--z-toward` で骨の Z を手のひらへ向けるか甲へ向けるかを選ぶ。`rigid_followers` に、付け直したかたまりの数と骨ごとの内訳。
- 親指の見える長さが人差し指の 55% 未満だと警告が出ます（人の手ではおよそ 3 分の 2）。握っても指に届かない原因は形で、関節とウェイトでは直りません。

### check

- `poses`：姿勢ごとの `crossings`（組ごとの交わる線の長さ・箇所の数・いちばん長かった段階 `at`・種類 `kind`）、`stretched_edges_max`、`thumb_to_index_mm` または `thumb_to_index_tip_mm`、`thumb`（解いた親指の角度・目標・届かなかった距離 `gap_mm`・突き抜け `crossing_mm`）。
- `kind` は `fingers`（指どうし）、`fold`（指の中の折れ）、`palm`（指先が手のひらに入る。警告にしない）。
- `blender_vs_numpy_fist_mm`：握る姿勢での Blender の変形との差。0.5mm を超えると警告。ほかのモディファイア・シェイプキー・体積保持があると数値の読み方に注意。
- `weights_in_hand.vertices_without_hand_weights`：手の範囲で骨のウェイトがない頂点の数。
- `followers.<名前>`：この手にあるかたまりの数、2 本以上の骨にまたがるかたまりの数、姿勢ごとの `drift_mm`（真下の肌に対して動いた量）。1mm を超えると警告。

### compare・accept・bones・run

- `compare`：`worse`・`better`（`check` どうし）、`changed`（`measure` どうし）、`not_compared`、`new_warnings`・`resolved_warnings`、件数の `summary`。`summary.findings` が 0 でなければ終了コード 2。
- `check --accept`：`warnings` は、基準より悪くなった値と新しい種類の警告だけ。`accept` に、悪くなった値・良くなった値・比べられなかった項目・元の警告（`warnings_without_accept`）・使った許す幅。
- `bones`：`human_bones`（役割 → 骨の名前）、`methods`（役割ごとの決め方：`declared`＝保存済みの割り当て、`name`＝名前、`where the finger chains meet`＝指の鎖が集まる骨、`hierarchy above the hand`＝手の親をたどった、`position under the hand`＝位置で並べた）、`missing`（見つからなかった手の役割）。`missing` があれば終了コード 2。
- `run`：フォルダの中に `bones.json`（作った時）・`measure.json`・`check_before.json`・`place.json`・`<入力の名前>_hands.blend`・`check_after.json`・`compare.json`・`run.json`。`run.json` の `steps` に各段の警告の数、`files` に各ファイルのハッシュ、`views` に描いた枚数、`warnings` に全部の段の警告（頭に段の名前）。画像は `views/before`・`views/after`・`views/pairs`。

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
| `--palm-share-min`・`--palm-share-max` | 0.48・0.62 | 手のひら ÷ 手の長さがこの外だと警告 |
| `--palm-aspect-max` | 1.45 | 手のひらの長さ ÷ 幅がこれを超えると警告 |
| `--thumb-reach-min` | 1.0 | 親指の届く位置がこれ未満だと警告 |
| `--hand-head-min`・`--hand-head-max` | 0.5・0.95 | 手 ÷ 頭の高さがこの外だと警告 |
| `--hand-forearm-min`・`--hand-forearm-max` | 0.5・0.9 | 手 ÷ 前腕がこの外だと警告 |
| `--head-meshes`・`--body-meshes`（measure） | なし | 頭の高さ・身長を測るメッシュ |
| `--head-height-mm`・`--height-mm`（measure） | なし | 頭の高さ・身長を数値で渡す |
| `--heads`（measure） | 測った値 | デザインの頭身。表を引く頭身をこれに替える |
| `--proportion-table`（measure） | 同梱の表 | 頭身ごとの「手 ÷ 頭の高さ」の表（JSON） |
| `--proportion-tolerance` | 0.15 | 表の値から許す割合 |
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
| `--thumb-roll`（place） | auto | 親指の曲がる向き。数値は、手のひら側と小指側の真ん中（45°）から小指側へ足す角度 |
| `--rigid-followers`（place） | なし | 爪などの固い部品のメッシュ。かたまりごとに真下の骨 1 本へ付け直す |
| `--followers`（check） | なし | 爪などのメッシュ。画像に描き、肌に対するずれを測る |
| `--follower-drift-mm` | 1 | ずれがこれを超えると警告 |
| `--accept`（check・run） | なし | 承認済みの版の `check` の報告。これより悪くなった値と、新しい種類の警告だけを残す |
| `--accept-tolerance-mm`・`--accept-tolerance-count`（check・run） | 0.5・0 | `--accept` で、長さ・数がこれ以内の増え方なら悪化と数えない |
| `--tolerance-mm`・`--tolerance-count`・`--tolerance-ratio`（compare） | 0.5・0・0.01 | これを超えて変わった値だけを並べる |
| `--output-map`（bones） | 必須 | 作った対応表の新しい JSON |
| `--out-dir`（run） | 必須 | 報告・候補・画像を入れる新しいフォルダ |
| `--views`（run） | none | 画像を描くか。`none`・`findings`・`all` |

既定の値は作例で、どのモデルにも合う値ではありません。

## AI への依頼文の例

```text
保存済みの <版> を読むだけで、<左右> の手を lida_hand_rig.py で調べてください。
- メッシュ <名前>、骨組み <名前>、人型の対応表 <JSON>。
- まず measure。頭 <名前> と体 <名前> を指定して、手の比（手のひら・親指・頭・前腕との比）を報告してください。デザイン画の比は <値> です。
- 次に、今の骨での check。次に place で <新しい blend> へ書き出し、同じ check で前後を比べてください。
- 報告と画像は <新しいフォルダ> へ。入力は保存しないでください。
- 結果は、推定になった関節、交差・折れ・伸びた辺の前後、画像を見て数値と合わなかった所、限界を分けて報告してください。
- 爪 <名前> は --rigid-followers で付け直し、check の --followers でずれを確かめてください。ほかのメッシュのウェイトは変えないでください。
```

一度に実行する時の例：

```text
保存済みの <版> を読むだけで、両手を lida_hand_rig.py の run で置き直してください。
- メッシュ <名前>、骨組み <名前>。対応表は骨組みから作り、methods に name・declared 以外が出たら知らせてください。
- 爪 <名前> は --rigid-followers に指定してください。出力は <新しいフォルダ> へ。
- 画像は --views findings（警告が残った姿勢だけ）にしてください。
- compare.json の worse と、置き直した後に残った警告を報告してください。置き直した後の方が悪い所があれば、候補を使う前に知らせてください。
```

## 確認済みの範囲

- Blender 5.3.0 の背景実行で、別の制作の保存済みファイルの写しを読むだけで `measure`・`place`・`check` を実行した。PIP と DIP は、手で合わせた骨と多くの指で 1mm 前後で一致した。書き出した写しでは、握る・指さしの伸びた辺が手で合わせた版より減り、親指の付け根のつぶれもなくなった。爪は握る姿勢でのずれが約 6mm から 0 になった。手のひらが長く親指が指の股に届かない形を、比の警告として出せた。入力は変わらない。
- 同じ写しで `bones`・`run`・`compare`・`check --accept` を実行した。骨組みに保存された人型の割り当てを、アドオンを読み込まない背景実行で読めた。名前だけからも同じ対応表になった。`run`（両手、画像なし）は約 1 分。`run` の中の置き直した後の `check` と、保存した候補を別に `check` した結果は、`compare` で差 0 件。`--views findings` で、警告が残った姿勢だけの前後の画像ができた。
- 通常 Python のテストで、合成の手を使って、指の分け方、左右の鏡写し、しわからの PIP・DIP、曲げる向き、ウェイトの鎖、線形スキニング、親指の解き方、固い部品の骨の選び方とずれ、報告の比較と承認済みの版を基準にした読み方、名前・親子・位置からの対応表（5 通りの名前の付け方）、前後の画像の合成、既存出力の保護を確かめている。

未確認：小指のように形に関節が出にくい指で推定と手作業のどちらが正しいか（画像で見る）、握った形の自然さ、親指が短い手での握り方、頭身ごとの手の大きさの表の妥当性（低い頭身の行は測っていない目安、様式化した行は作例が少ない）、複数の骨にまたがる部品、日本語の骨の名前や制御用の骨が多いリグでの対応表、実際の制作での `--accept` の運用、ほかの Blender 版、体積保持のスキニング、使用先での見え方。作例の数を品質の基準にしません。

## 利用条件

`lida_hand_rig.py` は GPL-3.0-or-later です（著作者 Lida）。[同梱ツールの利用条件](model-tools.md#利用条件と導入範囲)と同じ扱いで、GPL 本文とファイル冒頭の表示を保持します。この文書は[利用区分とクレジット](usage-and-attribution.md)に従います。
