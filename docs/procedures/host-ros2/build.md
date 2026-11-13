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

ROS 2 と Dobot の成果物は次の手順3で用意します。

## 3. Dobot の ROS / Native 環境をビルドする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この作業で`host-ros-build`になる。`host-hako`では実行しない。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 手順1で生成した`activate-host-ros-build.bash`と、手順2でbuildしたNova5 Runtime |
| この作業のゴール | 公式 `.srv` と demo、Service Bridge / PDU-RPC、Dobot 型・サービス binding が `../work-host` に生成される。 |

手順1の`ls`で`activate-host-ros-build.bash`が表示されたことを確認してください。未確認の場合は手順1へ戻ります。ROS 端末と箱庭 Native 端末は**分離**します。

新しい通常Host terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。

実行する確認コマンド（通常のHost terminal）:
```bash
ls -l ../work-host/profiles/activate-host-ros-build.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`ならprofileをsourceせず、手順1へ戻ります。

まず次の設定を行ってください。

実行する設定コマンド（`host-ros-build`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-build.bash

export DOBOT_WORK="$(realpath ../work-host)"
export ROS_DISTRO=jazzy
source "/opt/ros/$ROS_DISTRO/setup.bash"
export DOBOT_RPC_ADDRESS=127.0.0.1
```

Ubuntu 22.04／Humble の Dobot 経路は[対応待ち](../ros2/dobot-build.md)のため、この手順では `ROS_DISTRO=humble` に置き換えないでください。ROS profile による `ROS_DOMAIN_ID` は既定 73 です。

次に、**同じ `host-ros-build` 端末で**[Dobot 共通ビルド手順](../ros2/dobot-build.md)の **1 → 2** を順に実行してください。共通手順3はこの端末では実行せず、手順4で `host-hako` に戻って行います。共通手順1・2の完了後、次を確認します。

実行する確認コマンド（`host-ros-build`。共通手順1・2の完了後）:
```bash
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor --workdir "$DOBOT_WORK/ros2"
```

生成されるファイルの配置と、`ros2 run`からEndpoint共有ライブラリ、TCP、箱庭Runtimeまでの接続関係は、[ROS 2 Bridge基盤環境の成果物と接続関係](../../design/ros2-bridge-environment.md)を参照してください。

## 4. Native PDU-RPC と Dobot Asset をビルドし Launcher を切り替える

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako`（ROS 端末ではない） |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段の生成型・Native サービス設定と、Nova5 Runtime の既存 CMake build |
| この作業のゴール | `robot-arm-dobot-asset` が生成され、Launcher が公式サービスを受ける専用 Asset に切り替わる。 |

手順3の完了後、`host-ros-build` 端末ではなく、手順1・2で使用した `host-hako` 端末に戻ります。端末を閉じていた場合は[セットアップの手順2](setup.md#2-host-hako端末を開く)に従って開き直してください。プロンプトが `(host-hako) (hako)` であることを確認します。`(venv) (host-ros-build)` のままでは実行しません。`hakoniwa-robot-arm` の repository root へ移動し、`pwd` で確認してから、まず次の設定を行ってください。

実行する設定コマンド（`host-hako`）:
```bash
export DOBOT_WORK="$(realpath ../work-host)"
test -d "$DOBOT_WORK/foundation/install/include"
```

`test -d` が成功しなければ先へ進まず、Foundation と `DOBOT_WORK` を確認してください。次に、**同じ `host-hako` 端末で**[Dobot 共通ビルド手順3](../ros2/dobot-build.md#3-native-端末rpc-を-foundation-に接続し専用-asset-を作る)を実行してください。手順4は共通手順3の準備と実行であり、その前に別途行うビルドではありません。

共通手順3の CMake と `adapt_launcher.py` の成功、`launcher.pre-dobot.json` の生成を確認してください。`nova5.py configure` を再実行した場合は Launcher 適用をやり直します。

次は[Host ROS 2連携の起動・動作確認](operation.md)へ進みます。

実機 driver はこの箱庭用ビルドには含めません。箱庭での確認後、実機へ進む場合だけ[実機追加手順](real.md)でビルドします。

## 応用：独自ROS 2 nodeを追加する

まず[Host ROS 2連携の起動・動作確認](operation.md)で virtual の状態と安全な小動作を確認してください。

標準動作確認の完了後、この基盤環境を利用して独自packageを作成できます。手順は[独自ROS 2 nodeの作成とbuild](../ros2/custom-nodes.md)を参照してください。
