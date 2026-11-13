# docker-onlyビルド

[docker-onlyセットアップ](setup.md)の完了が前提です。基本経路は Dobot 仮想サービスです。箱庭workは`/workspace/work-docker-<distro>`、この構成の Dobot / ROS 成果物も同 work 内の `ros2` に置きます（旧 `/workspace/ros2-work-<distro>` は使用しません）。

手順: [一覧](../README.md) → [セットアップ](setup.md) → **ビルド** → [起動・動作確認](operation.md)

`docker-hako`の`(hako)` shellではFoundationの`python`を使用し、ROS 2用の`docker-ros-build`は別のattach shellでシステムの`/usr/bin/python3`を使用します。

## 1. ROS 2連携用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | Forge済み`nova5.contact.xml`と、同じContainer内で動くROS 2 Bridge |
| この作業のゴール | ROS 2用Launcher、TCP設定、`binding.json`がContainer側workへ生成される。 |

macOS Docker Desktop、CI、画面のない環境で実行するコマンド（`docker-hako`、headless）:

```bash
HAKONIWA_ROS2_TCP_HOST=127.0.0.1 \
python tools/recipe/nova5.py configure \
  --headless --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

Linux HostでX11 Viewerを有効にした場合だけ実行するコマンド（`docker-hako`。headlessブロックの代わり）:

```bash
HAKONIWA_ROS2_TCP_HOST=127.0.0.1 \
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

`ROS 2 TCP: enabled`が表示されればOKです。`error:`で終了した場合はNGです。

## 2. Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 前段で生成したLauncherと、Forge済み`nova5.contact.xml` |
| この作業のゴール | `robot-arm-hakoniwa-asset`がContainer側workへ生成され、doctorが成功する。 |

実行するコマンド（`docker-hako`、headless構成）:

```bash
python tools/recipe/nova5.py build --headless
```

X11 Viewerを使用する構成では`python tools/recipe/nova5.py build`へ置き換えます。続けて確認します。

実行する確認コマンド（`docker-hako`）:
```bash
ls -l "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset"
python tools/recipe/ros2_tcp.py doctor --robot nova5
python tools/recipe/nova5.py doctor
```

実行ファイルが表示され、doctorの全項目が`[OK]`ならOKです。

## 3. ROS 2 build端末を開く

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この操作後のattach shellが`docker-ros-build`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainerと、distribution単位のROS 2成果物ディレクトリ |
| この作業のゴール | 箱庭Workspaceへ入っていないROS 2 build用attach shellが開く。 |

新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してください。次のブロックだけを実行してContainerのプロンプトを待ちます。

実行するコマンド（通常のHost terminal。Containerに入る）:
```bash
bash docker/attach.bash jazzy
```

Containerのプロンプトが出てから、次を実行します。

実行するコマンド（`docker-ros-build`）:
```bash
cd ../hakoniwa-robot-arm
pwd
echo "$HAKONIWA_WORK_DIR"
```

Humbleでは`jazzy`を`humble`へ置き換えます。`attach.bash`はContainer内の`hakoniwa-business-pack`リポジトリルートを開くため、Container側のブロックでRobot Arm repositoryへ移動します。`pwd`の末尾が`hakoniwa-robot-arm`で、`echo "$HAKONIWA_WORK_DIR"`に`/workspace/work-docker-jazzy`または`/workspace/work-docker-humble`が表示されればOKです。

## 4. Dobot / ROS workspace とサービス binding を build する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-build` |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainerと、configure済みTCP設定 |
| この作業のゴール | 公式メッセージ・demo、Service Bridge、サンプルと binding が実行可能になる。 |

まず `docker-ros-build` で次の設定を行ってください。Docker が同じ Container のため RPC 接続先は localhost です。

実行する設定コマンド（`docker-ros-build`）:
```bash
export DOBOT_WORK="$HAKONIWA_WORK_DIR"
export ROS_DISTRO=jazzy
export DOBOT_RPC_ADDRESS=127.0.0.1
```

Humble では `ROS_DISTRO=humble` に変更します。次に、**同じ `docker-ros-build` 端末で**[Dobot 共通ビルド手順](../ros2/dobot-build.md)の **1 → 2** を順に実行してください。共通手順3はここでは実行せず、手順5で `docker-hako` に戻って行います。`dobot_demo demo` と `hakoniwa_dobot configure` が表示され、service / endpoint JSON が存在すればOKです。

## 5. Native RPC / Asset をビルドし Launcher を切り替える

手順4の完了後、`docker-hako` の `(hako)` shell に戻り、Robot Arm ルートでまず次の設定を行ってください。

実行する設定コマンド（`docker-hako`）:
```bash
export DOBOT_WORK="$HAKONIWA_WORK_DIR"
test -d "$DOBOT_WORK/foundation/install/include"
```

`test -d` が成功しなければ先へ進まず、Foundation と `DOBOT_WORK` を確認してください。次に、**同じ `docker-hako` 端末で**[共通ビルド手順3](../ros2/dobot-build.md#3-native-端末rpc-を-foundation-に接続し専用-asset-を作る)を実行してください。

`robot-arm-dobot-asset` と Launcher backup を確認してください。`docker-ros-build` は `exit` して構いませんが、`docker-hako` と Container は終了しないでください。

次は[docker-only起動・動作確認](operation.md)へ進んでください。
