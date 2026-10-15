# 図解索引

[工程索引](process-index.md)

文字だけでは取り違えやすい「変える場所・固定する場所・方向・つながり」を図で確認します。各工程では対応する説明章へ進んでください。PNGは表示・AIへの添付用、SVGは拡大用です。

| 工程・つまずき | 図で確かめること | 説明章 | 図版 |
|---|---|---|---|
| 入力素材・三面図 | 同じ基準から素材を分け、複数角度と基準絵を両方渡す | [入力素材](input-materials.md)、[三面図](multiangle-threeview.md) | [PNG](../assets/input-alignment-flow.png) / [SVG](../assets/input-alignment-flow.svg) |
| 局所補正の境目 | 移動量と戻す幅を別々に決める。修正マスクとスキンウェイトは別 | [調整方法](adjustment-methods.md) | [PNG](../assets/local-mask-transition.png) / [SVG](../assets/local-mask-transition.svg) |
| 眼球の構成と視線 | 球面・虹彩/瞳孔・白目・任意の反射面と固定する線の層を分ける | [眼球の制作](eye-modeling.md) | [PNG](../assets/eye-structure-flow.png) / [SVG](../assets/eye-structure-flow.svg) |
| 口・表情キー | 共通の顔で対象部位だけ動かす。顎・輪郭・対象外を固定する | [口型](mouth-shapes.md) | [PNG](../assets/face-key-locality.png) / [SVG](../assets/face-key-locality.svg) |
| まぶたの白い帯・折れ | 縁と隣接列で同じ局所変換を共有し、外側へ減衰する | [表情の調整](expression-adjustment.md) | [PNG](../assets/eyelid-band-follow.png) / [SVG](../assets/eyelid-band-follow.svg) |
| 手を短くしたときの段 | 掌の高さとU字周辺の輪郭を分け、保持端へ滑らかにつなぐ | [手](hand-shape.md) | [PNG](../assets/hand-shortening-flow.png) / [SVG](../assets/hand-shortening-flow.svg) |
| スカートの干渉・見えない面 | 層順序と自由裾を保持し、脚が布を横切る経路を診断する | [スカートと補完](skirt-hidden-modeling.md) | [PNG](../assets/skirt-layer-route.png) / [SVG](../assets/skirt-layer-route.svg) |
| 髪の模様・穴・突出 | 基本色、接続、面の順序を一つずつ切り分ける | [調整方法](adjustment-methods.md) | [PNG](../assets/hair-cause-isolation.png) / [SVG](../assets/hair-cause-isolation.svg) |
| 翼を最初から作る順序 | 外形→支持体→少数羽→全列→途中動作の順で確認する | [翼の制作](wing-workflow.md) | [PNG](../assets/wing-build-sequence.png) / [SVG](../assets/wing-build-sequence.svg) |
| 翼全体の羽の配置と名前 | 初列/次列/三列、雨覆、小翼羽、肩羽を上下面と対応させる | [翼の配置と用語](wing-feather-terms.md) | [PNG](../assets/wing-feather-terms.png) / [SVG](../assets/wing-feather-terms.svg) |
| 翼の羽の配置と向き | 羽種別、羽軸、覆う順序、根元を面で付ける意味を確認する | [翼の制作](wing-workflow.md) | [PNG](../assets/wing-feather-layout.png) / [SVG](../assets/wing-feather-layout.svg) |
| 翼の根元が浮く | 支持体断面、付着幅、方向、重みを同時に合わせる | [翼の制作](wing-workflow.md)、[試行錯誤](trial-and-error.md) | [PNG](../assets/wing-root-fit.png) / [SVG](../assets/wing-root-fit.svg) |
| 部品を統合する | 採用版と依存物を対応させ、保存・全身・使用先を別確認する | [画像の渡し方と統合](visual-handoff.md) | [PNG](../assets/integration-dependencies.png) / [SVG](../assets/integration-dependencies.svg) |
| 曲がる場所の線 | 関節の前後に連続した支持帯を作る | [網目と重み](mesh-weight.md) | [PNG](../assets/bend-support.png) / [SVG](../assets/bend-support.svg) |
| 強く変形する帯の接続 | 面と辺の流れ、急な密度変化、接続集中を見る | [網目と重み](mesh-weight.md) | [PNG](../assets/flow-continuity.png) / [SVG](../assets/flow-continuity.svg) |
| 膝の実メッシュの線 | 当時の実辺と、未実施の配置案を区別する | [膝の図の読み方](knee-edge-placement.md) | [PNG](../assets/actual-knee-layout.png) / [SVG](../assets/actual-knee-layout.svg) |
| 膝を曲げた診断 | 通常・途中・曲げた形で伸びと潰れを確認する | [膝の図の読み方](knee-edge-placement.md) | [PNG](../assets/actual-knee-bend.png) / [SVG](../assets/actual-knee-bend.svg) |

## AIに渡すとき

1. 必要な図を一枚選び、対象部位の実画像・基準素材と一緒に渡す。
2. 「図のどの番号・線が、実モデルのどこに対応するか」を指定する。画面の左右とモデルの左右、移動軸と単位もそろえる。
3. 変える部位、固定する部位、途中姿勢、終了条件を添える。[依頼の型](ai-instructions.md)を使う。

膝の2枚は以前の実メッシュの診断で、現在の完成や合格を示す図ではありません。他の15枚は自作模式図です。模式図の形・列数・寸法をそのまま実モデルへ移す指示にはせず、実際の形と必要な動作で決め直してください。

身体と服を段階別に生成する方法は次回の予防案です。複数角度を先に用意した顔の改善は今回の制作経験です。図の出所と確認範囲は[同梱図版](../assets/README.md)にも記載しています。
