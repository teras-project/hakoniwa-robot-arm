# SO-101 キューブ把持デモ

SO-101 が床の上のキューブ（一辺3 cm、30 g）をつかんで持ち上げ、手首を回してから横へ置くデモです。箱庭単体で実行し、ROS 2は使用しません。

手順: [一覧](../README.md) → [セットアップ](host-standalone/setup.md) → **SO-101 キューブ把持デモ**

## 前提

- [箱庭単体セットアップ](host-standalone/setup.md)の「FoundationとRuntime Recipeを準備する」までが完了している。
- このページのコマンドはすべて`host-hako`で実行し、Foundation管理の`python`を使用する。

## 仕組み

| 項目 | 内容 |
| --- | --- |
| 作業空間 | `recipes/so101/config/environment/workspace.json`の`grasp_cube`が床に置かれる |
| 爪の当たり判定 | 同ファイルの`robot_collision_pads`が、曲面の爪メッシュの当たり判定を平らなパッドへ置き換える。数値は`tools/grasp/compute_gripper_pads.py`の出力 |
| 把持の保持 | 同ファイルの`physics.noslip_iterations`がMuJoCoのnoslip solverを有効にし、つかんだキューブが爪の間から少しずつ滑り落ちるのを防ぐ |
| 把持の軌道 | `recipes/so101/grasp-trajectory.json`。キューブの真上へ移動、爪を開いて下降、爪を閉じる、持ち上げる、手首を左右に回す、横へ運ぶ、下ろして爪を開く、初期姿勢へ戻る、の順に関節目標を並べたもの。`tools/grasp/generate_pick_place_trajectory.py`の出力 |

| 変換の段階 | 担当 | 爪まわりで行うこと |
| --- | --- | --- |
| Model Forge | `tools/recipe/so101.py forge` | 上流URDF／MJCFを取得し、アクチュエータと関節範囲を設定した`so101.xml`を作る |
| 作業空間の生成 | `so101.py configure --environment`が`tools/generate_arm_environment.py`を実行 | `workspace.json`を読み、爪メッシュの当たり判定を無効にしてパッドを取り付け、キューブとnoslip設定を加えた`so101.environment.xml`を作る |

パッドと軌道の数値はキューブの大きさと初期位置に合わせています。`grasp_cube`の位置や大きさを変えた場合は、[5. パッドと軌道を作り直す](#5-パッドと軌道を作り直す)で数値を作り直します。

## 1. SO-101のモデルを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | 準備済みのFoundation |
| この作業のゴール | `../work-host/model-forge/so101/install/so101.xml`が生成される。 |

実行するコマンド（`host-hako`）:
```bash
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/so101/so101-model-forge.yaml
python ../hakoniwa-robot-arm/tools/recipe/so101.py forge
```

`SO-101 forge complete.`が表示されればOKです。

## 2. 把持用の作業空間でbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root（最初のコマンドの後に`hakoniwa-robot-arm`へ移動する） |
| この作業の入力成果物 | 前段で生成した`so101.xml` |
| この作業のゴール | キューブと爪パッドを含む作業空間で、SO-101 Runtimeがbuildされる。 |

`--environment`を付けると、キューブ、爪パッド、noslip設定を含む`so101.environment.xml`が生成されます。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/so101/so101-joint-trajectory-control.yaml
cd ../hakoniwa-robot-arm
python tools/recipe/so101.py configure \
  --environment --realtime-sync-cycle-msec 50
python tools/recipe/so101.py build
python tools/recipe/so101.py doctor
```

`doctor`のすべての行が`[OK]`ならOKです。

## 3. 起動してキューブをつかむ

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みのSO-101 Runtime |
| この作業のゴール | MuJoCo Viewer上でSO-101がキューブをつかんで持ち上げ、横へ置く。 |

`start`直後は標準デモ軌道（`demo-trajectory.json`）が自動で送られ、約10秒で初期姿勢へ戻ります。標準デモはキューブに触れません。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/so101.py start
python tools/recipe/so101.py status
```

`status`が`RUNNING`を返し、標準デモが初期姿勢へ戻るまで待ちます。その後、把持の軌道を送ります。

実行するコマンド（`host-hako`）:
```bash
python tools/control/send_joint_trajectory.py \
  ../work-host/recipes/so101-joint-trajectory-control/config/asset-manifest-environment.json \
  --trajectory recipes/so101/grasp-trajectory.json
```

`Successfully sent JointTrajectory PDU.`が表示され、MuJoCo Viewer上で約19秒かけてSO-101が緑のキューブをつかんで持ち上げ、手首を回し、左前方へ置いて初期姿勢へ戻ればOKです。もう一度試す場合は、手順4で停止してから`start`し直します。

## 4. 終了する

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/so101.py stop
python tools/recipe/so101.py status
```

`status`が`TERMINATED`を返せば停止完了です。

## 5. パッドと軌道を作り直す

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 手順1の`so101.xml`と、手順2の`so101.environment.xml` |
| この作業のゴール | パッドの数値と把持の軌道がツールから再生成され、MuJoCo上の再生で`PASS`になる。 |

キューブの大きさや位置を変えたときに使います。変更していない場合、出力は登録済みの数値と同じになります。

パッドは、爪の当たり判定メッシュから内側の面を測り、キューブ幅だけ開いた角度で両方の面に平行な薄い箱を置きます。

実行するコマンド（`host-hako`）:
```bash
python tools/grasp/compute_gripper_pads.py \
  ../work-host/model-forge/so101/install/so101.xml --object-width 0.03
```

表示されたJSON配列が`recipes/so101/config/environment/workspace.json`の`robot_collision_pads`と同じならOKです。キューブ幅を変えた場合は、`--object-width`へ新しい幅を指定し、表示された配列で`robot_collision_pads`を置き換えてから、手順2の`so101.py configure`をやり直します。

軌道は、キューブの位置から真上向きの把持姿勢を逆運動学で求め、関節目標の列として書き出します。`--verify`は書き出した軌道をRuntimeと同じ50 HzでMuJoCo上に再生し、キューブの持ち上げ量、置いた位置、傾きを判定します。

実行するコマンド（`host-hako`）:
```bash
python tools/grasp/generate_pick_place_trajectory.py \
  ../work-host/model-forge/so101/install/so101.environment.xml \
  --output recipes/so101/grasp-trajectory.json --verify
```

最後の行が`PASS`ならOKです。`FAIL`の場合は軌道を送らず、表示された持ち上げ量、置いた位置のずれ、傾きを確認します。置く位置は`--place-angle-deg`、持ち上げる高さは`--lift`で変更できます。
