# Excavator Digging Environment

このディレクトリは、油圧ショベルの簡易掘削PoCで使用するHField穴と球形土粒子の
設定正本です。生成済みの`$HAKONIWA_WORK_DIR/model-forge/excavator/install/*.xml`を直接編集しません。

## 設定ファイル

| ファイル | 役割 |
| --- | --- |
| [`terrain.json`](terrain.json) | HFieldの大きさ、穴の中心、深さ、平坦部、外縁、摩擦、色 |
| [`soil.json`](soil.json) | 球形粒子の個数、配置、半径、間隔、高さ、密度、接触条件、色 |

`excavator-model-forge.yaml`にある`current_soil_candidate`は検証状態を記録する
メタデータです。粒子モデルへ実際に反映される値は[`soil.json`](soil.json)です。

## 現在のPoC設定

### 穴

- 中心：`[9.0, 0.0] m`
- 深さ：`1.2 m`
- 平坦部半径：`[2.0, 1.4] m`
- 外縁半径：`[2.733333334, 2.0] m`

半径はX、Y方向の値です。穴の全幅はそれぞれ半径の2倍になります。

### 粒子

- 配置：`5 × 5 × 2 = 50個`
- `particle_radius_m`：`0.18 m`
- 粒子直径：`0.36 m`
- 中心間隔：`0.42 m`
- 最下層中心Z：`-1.01 m`

`particle_radius_m`は半径です。見た目の直径を0.30 mにしたい場合、設定値は
`0.18`です。`spacing_m`は粒子直径より大きくし、初期状態で粒子同士が貫通しない
ようにします。

## 粒子数を変更する場合

粒子数は次の積です。

```text
particle_count = grid_count[0] × grid_count[1] × grid_count[2]
```

粒子は1個ごとにMuJoCoの`freejoint`を持つため、個数を増やすと自由度と接触計算が
急増します。120粒子ではMuJoCo単体RTFが約1まで低下したため、現在は少し大きな50粒子を
候補値としています。粒子数を増やした場合は接触が集中する掘削中のRTFも確認してください。

調整時は、次の順序を推奨します。

1. `grid_count`で個数を決める
2. `particle_radius_m`で見た目の粒径を決める
3. `spacing_m > 2 × particle_radius_m`を満たす
4. 格子全体が穴の外縁へ概ね収まることを確認する
5. `bottom_z_m`を穴底と粒子半径に合わせる
6. PS5操作で応答性、すくい上げ、保持、排出を確認する

## 再生成と実行

通常は、`--digging-worksite`付きの`configure`が`bucket-collision.yaml`、
`terrain.json`、`soil.json`を順にmaterializeします。設定変更後にForgeを別途実行する
必要はありません。

```bash
python tools/recipe/excavator.py configure --digging-worksite --gamepad
python tools/recipe/excavator.py build
python tools/recipe/excavator.py start
```

`configure`は、次の生成物と`SHA256SUMS`を更新してからLauncherを生成します。

- `excavator.bucket.xml`
- `excavator.bucket-proxy-debug.xml`
- `excavator.terrain.xml`
- `excavator-worksite-height.png`
- `excavator.soil.xml`

上流モデルの取得・正規化を含むForge全体を再現したい場合だけ、次を実行します。

Forge全体を再現する場合は次を実行します。

```bash
PYTHON_CMD=../hakoniwa-mbody-registry/.venv/bin/python3 \
  recipes/excavator/forge-excavator.sh
```

PS5で掘削モデルを確認する場合は、モデル生成と選択をLauncherへ反映するため、必ず
`configure`からやり直します。

```bash
python tools/recipe/excavator.py configure --digging-worksite --gamepad
python tools/recipe/excavator.py build
python tools/recipe/excavator.py start

# 確認後
python tools/recipe/excavator.py stop
```

## 適用範囲

この粒子群は、バケット操作と粒状物らしい見た目を確認する簡易剛体PoCです。
土圧、粘着、締固め、含水率、粒子破砕などの土質力学は再現・保証しません。
