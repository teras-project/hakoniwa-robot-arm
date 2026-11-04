# Host ROS 2連携ビルド

[Host ROS 2連携セットアップ](setup.md)でNova5 MJCFを生成してから実行します。**基本経路は Dobot 仮想サービス**です。`real`／`both` は実機接続の発展構成です。

手順: [一覧](../README.md) → [セットアップ](setup.md) → **ビルド** → [起動・動作確認](operation.md)

`host-hako`ではFoundationの`python`でRuntimeをbuildします。ROS 2のbuildは別の通常Host terminalで`host-ros-build` profileを有効にし、システムの`/usr/bin/python3`を使用します。両環境を同じ端末で有効にしないでください。

## 1. ROS 2連携用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | `../work-host/model-forge/nova5/install/nova5.contact.xml` |
| この作業のゴール | ROS 2用Launcher、binding、4種類のROS端末profileが`../work-host`へ生成される。 |

`--ros2-tcp`を付けることで、ROS 2用Launcher、binding、4種類のROS端末profileを生成します。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50

ls -l ../work-host/profiles/activate-host-ros-build.bash
ls -l ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

`Profiles`に`activate-host-ros-build.bash`などが表示され、`ROS 2 TCP`が`enabled`で、profileとbindingの両方の出力先が確認できればOKです。`No such file or directory`なら先へ進まず、この手順の`configure --ros2-tcp`を再実行します。

## 2. Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で生成した`launcher.json`と、Forge済みの`nova5.contact.xml` |
| この作業のゴール | MuJoCo上でNova5を動かす`robot-arm-hakoniwa-asset`が生成される。 |

MuJoCo Viewerを使用する通常ビルドです。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py build
ls -l ../work-host/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
```

画面のないHostやCIでは、最初のコマンドだけ`build --headless`へ置き換えます。最後の`ls`で`robot-arm-hakoniwa-asset`が表示されればOK、`No such file or directory`ならNGです。

続けてROS 2基盤環境をbuildします。

## 3. Dobot の ROS / Native 環境をビルドする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この作業で`host-ros-build`になる。`host-hako`では実行しない。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 手順1で生成した`activate-host-ros-build.bash`と、手順2でbuildしたNova5 Runtime |
| この作業のゴール | 公式 `.srv`、Dobot driver / demo、Service Bridge / PDU-RPC、Dobot 型・サービス binding が `../work-host` に生成される。 |

手順1の configure が端末 profile を生成済みです。この手順では ROS 端末と箱庭 Native 端末を**分離**します。[Dobot 共通ビルド手順](../ros2/dobot-build.md)の1・2を以下の環境で実行してください。

生成されるファイルの配置と、`ros2 run`からEndpoint共有ライブラリ、TCP、箱庭Runtimeまでの接続関係は、[ROS 2 Bridge基盤環境の成果物と接続関係](../../design/ros2-bridge-environment.md)を参照してください。

この手順へ進む前に、手順1の`ls`で`activate-host-ros-build.bash`が表示されたことを確認してください。未確認の場合は手順1へ戻ります。

新しい通常Host terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。

実行する確認コマンド（通常のHost terminal）:
```bash
ls -l ../work-host/profiles/activate-host-ros-build.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`ならprofileをsourceせず、手順1へ戻ります。

実行するコマンド（`host-ros-build`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-build.bash

export DOBOT_WORK="$(realpath ../work-host)"
export ROS_DISTRO=jazzy
export DOBOT_RPC_ADDRESS=127.0.0.1
```

Ubuntu 22.04／Humble では `ROS_DISTRO=humble` に置き換えます。ROS profile による `ROS_DOMAIN_ID` は既定 73 です。共通手順1・2の実行後、次を確認します。

```bash
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor --workdir "$DOBOT_WORK/ros2"
```

## 4. Native PDU-RPC と Dobot Asset をビルドし Launcher を切り替える

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako`（ROS 端末ではない） |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段の生成型・Native サービス設定と、Nova5 Runtime の既存 CMake build |
| この作業のゴール | `robot-arm-dobot-asset` が生成され、Launcher が公式サービスを受ける専用 Asset に切り替わる。 |

`host-hako` で Robot Arm ルートへ移動し、[Dobot 共通ビルド手順](../ros2/dobot-build.md#3-native-端末rpc-を-foundation-に接続し専用-asset-を作る)の3を実行します。

実行する設定コマンド（`host-hako`）:
```bash
export DOBOT_WORK="$(realpath ../work-host)"
test -d "$DOBOT_WORK/foundation/install/include"
```

共通手順3の CMake と `adapt_launcher.py` の成功、`launcher.pre-dobot.json` の生成を確認してください。`nova5.py configure` を再実行した場合は Launcher 適用をやり直します。

次は[Host ROS 2連携の起動・動作確認](operation.md)へ進みます。

## 応用：独自ROS 2 nodeを追加する

まず[Host ROS 2連携の起動・動作確認](operation.md)で virtual の状態と安全な小動作を確認してください。

標準動作確認の完了後、この基盤環境を利用して独自packageを作成できます。手順は[独自ROS 2 nodeの作成とbuild](../ros2/custom-nodes.md)を参照してください。
