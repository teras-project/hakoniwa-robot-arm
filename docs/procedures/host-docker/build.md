# host+dockerビルド

[host+dockerセットアップ](setup.md)の完了が前提です。基本経路は Dobot 仮想サービスです。Host の箱庭workは`../work-host`、Container の Dobot / ROS 生成物も同じ Host mount の `/workspace/work-host` に置きます（旧 `/workspace/ros2-work-<distro>` の生成物はこの経路では使用しません）。

手順: [一覧](../README.md) → [セットアップ](setup.md) → **ビルド** → [起動・動作確認](operation.md)

`host-hako`ではFoundationの`python`、通常のHost terminalではDocker CLI、`docker-ros-bridge`ではROS 2のシステムPythonと専用venvを使用します。端末を切り替えるときは新しいプロンプトを確認してから次のコマンドを実行してください。

## 1. Host側のROS 2連携構成を生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | Forge済み`nova5.contact.xml`と、接続先となるDocker環境 |
| この作業のゴール | ROS 2用Launcher、TCP設定、`binding.json`が`../work-host`へ生成される。 |

macOS Docker Desktopで実行するコマンド（`host-hako`）:

```bash
HAKONIWA_ROS2_TCP_HOST=host.docker.internal \
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

Linux HostでDockerのhost networkを使用する場合のコマンド（`host-hako`、macOSでは実行しない）:

```bash
HAKONIWA_ROS2_TCP_HOST=127.0.0.1 \
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

画面のないHostでは、選択したコマンドへ`--headless`を追加します。`Launcher`の出力先が表示され、`ROS 2 TCP`が`enabled`ならOKです。`error:`で終了した場合はNGです。

## 2. Host側Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で生成したLauncherと、Forge済み`nova5.contact.xml` |
| この作業のゴール | `robot-arm-hakoniwa-asset`が`../work-host`へ生成される。 |

実行するコマンド（`host-hako`、Viewerを使用する場合）:

```bash
python tools/recipe/nova5.py build
```

画面のないHostでは`python tools/recipe/nova5.py build --headless`へ置き換えます。この通常 Asset のビルドは、同じ build ディレクトリに以前の Dobot 専用設定が残っていても、Dobot 用 PDU 型を要求しません。Dobot 専用 Asset は手順5で別途ビルドします。続けて成果物と設定を確認します。

実行する確認コマンド（`host-hako`）:
```bash
ls -l ../work-host/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
python tools/recipe/ros2_tcp.py doctor --robot nova5
python tools/recipe/nova5.py doctor
```

実行ファイルが表示され、doctorの全項目が`[OK]`ならHost側は完了です。

## 3. ROS 2 Containerを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | セットアップで用意した通常Host terminal。このコマンド後、Container shellを`docker-ros-bridge`として維持する。 |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | `hakoniwa-arm-dev:jazzy` imageと、生成済み`../work-host/.../ros2-tcp` |
| この作業のゴール | TCP設定をread-only mountしたROS 2 Containerが起動する。 |

通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してください。次のコマンドでContainer shellが開くため、このブロックだけを実行してプロンプトを待ちます。

実行するコマンド（通常のHost terminal）:
```bash
HAKONIWA_DOCKER_GUI=off \
HAKONIWA_ROS2_TCP_CONFIG=../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp \
HAKONIWA_DOCKER_WORK_DIR=/workspace/work-host \
bash docker/run.bash jazzy
```

Humbleでは`jazzy`を`humble`へ置き換えます。起動ログに次の内容が表示され、Container shellが開けばOKです。

```text
Mount: ... -> /workspace
Container: hakoniwa-arm-dev-jazzy; ...
GUI: off; DISPLAY: disabled
Workdir: /workspace/work-host; Foundation mmap: tmpfs
```

この構成では `HAKONIWA_WORK_DIR=/workspace/work-host`、`HAKONIWA_ROS2_WS=/workspace/work-host/ros2` になります。このshellを終了するとContainerも削除されるため、以後`docker-ros-bridge`端末として最後まで開いたままにします。

## 4. Dobot / ROS サービスとサンプルを build する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 手順3の`docker/run.bash`で開いた同じContainer shell（`docker-ros-bridge`）。 |
| 実行ディレクトリ | 最初はContainer内の`hakoniwa-business-pack`リポジトリルート。手順4.1で`hakoniwa-robot-arm`へ移動する。 |
| この作業の入力成果物 | 起動中のContainerと、共有 mount `/workspace/work-host` |
| この作業のゴール | 公式メッセージ・demo、ROS Service Bridge、Dobot サンプルが実行可能になる。 |

以下はすべて、手順3で開いた同じContainer shellで実行します。新しいHost terminalを開いたり、追加attachしたりする必要はありません。`docker-ros-bridge`はこの端末の役割名であり、ROS 2 Bridgeのプロセスはまだ起動しません。Bridgeの起動は次の[起動・動作確認](operation.md)で行います。

コードブロックを1つずつ実行し、各段階の成功条件を確認してから次へ進んでください。buildに失敗した場合は、その段階で止めて原因を解消します。

### 4.1 作業ディレクトリを確認する

Containerのプロンプトが表示されてから、初期ディレクトリの`hakoniwa-business-pack`からRobot Arm repositoryへ移動します。

実行するコマンド（`docker-ros-bridge`）:
```bash
cd ../hakoniwa-robot-arm
pwd
```

`pwd`の結果が`/workspace/hakoniwa-robot-arm`ならOKです。以降は同じディレクトリで実行します。

### 4.2 Dobot / ROS workspace とサービス binding を build する

まず、`docker-ros-bridge` で次の設定を行ってください。macOS Docker Desktop では Host の RPC TCP 54020 に `host.docker.internal` で接続します。Linux Host の `docker/run.bash` 既定 host network では `DOBOT_RPC_ADDRESS=127.0.0.1` に変更します。Humble では `ROS_DISTRO=humble` に変更します。

実行する設定コマンド（`docker-ros-bridge`）:
```bash
export DOBOT_WORK=/workspace/work-host
export ROS_DISTRO=jazzy
export DOBOT_RPC_ADDRESS=host.docker.internal
```

次に、**同じ `docker-ros-bridge` 端末で**[Dobot 共通ビルド手順](../ros2/dobot-build.md)の **1 → 2 だけ**を順に実行してください。共通手順3は Container では実行せず、このページの手順5で Host に戻って行います。公式 checkout と成果物は Host と共有されるため、Native 側でも読めます。

共通手順1・2の完了後、生成結果で `dobot_demo demo` と `hakoniwa_dobot configure` が表示され、次の成果物がすべて存在することを確認します。

実行する確認コマンド（`docker-ros-bridge`。共通手順1・2の完了後）:
```bash
ls -l "$DOBOT_WORK/dobot-ros/install/setup.bash" \
  "$DOBOT_WORK/dobot-apps/install/setup.bash" \
  "$DOBOT_WORK/dobot-types/pdu/types/dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJRequestPacket.hpp" \
  "$DOBOT_WORK/dobot-services/dobot-services.json" \
  "$DOBOT_WORK/dobot-services/rpc/endpoints/dobot_virtual.json"
```

一つでも見つからなければ手順5へ進まず、共通手順1・2の失敗を解消してください。Docker Desktop 側の Host Firewall で TCP 54020 を使用できることも確認してください。

## 5. Host Native RPC / Asset をビルドし Launcher を切り替える

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Host 側の `host-hako`。手順1・2で使った端末へ戻る。`docker-ros-bridge` では実行しない。 |
| 実行ディレクトリ | Host 上の `hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 手順4.2で共通手順1・2を完了して生成した `dobot-types` とサービス binding、Host 側の Foundation |
| この作業のゴール | Host の Native RPC / Dobot Asset をビルドし、Launcher を切り替える。 |

手順4.2の完了後、**Host の `host-hako` に戻り**ます。端末を閉じていた場合は[セットアップの手順2](setup.md#2-host-hako端末を開く)に従って開き直してください。Host 上の Robot Arm repository root にいることを確認し、まず次の設定を行ってください。

実行する設定コマンド（Host の `host-hako`）:
```bash
export DOBOT_WORK="$(realpath ../work-host)"
test -d "$DOBOT_WORK/foundation/install/include"
```

`test -d` が成功しなければ先へ進まず、Host 側の Foundation と `DOBOT_WORK` を確認してください。次に、**同じ `host-hako` 端末で**[共通ビルド手順3](../ros2/dobot-build.md#3-native-端末rpc-を-foundation-に接続し専用-asset-を作る)を実行してください。手順5は共通手順3の準備と実行であり、その前に別途行うビルドではありません。Container の ROS shell に Foundation を source しないでください。

共通手順3の完了後に `robot-arm-dobot-asset` と Launcher backup を確認してください。Container は終了せず `docker-ros-bridge` として維持します。Host と Container の絶対パスが違うため、Host の Launcher に `/workspace/...` を書き込まないでください。

次は[host+docker起動・動作確認](operation.md)へ進んでください。
