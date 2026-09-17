# host+dockerビルド

[host+dockerセットアップ](setup.md)の完了が前提です。Host側の箱庭workは`../work-host`、Container側のROS 2成果物はdistributionごとの`/workspace/ros2-work-<distro>`を使用します。

## 1. Host側のROS 2連携構成を生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | Forge済み`nova5.contact.xml`と、接続先となるDocker環境 |
| この作業のゴール | ROS 2用Launcher、TCP設定、`binding.json`が`../work-host`へ生成される。 |

macOS Docker Desktopでは次を実行します。

```bash
HAKONIWA_ROS2_TCP_HOST=host.docker.internal \
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

Linux HostでDockerのhost networkを使用する場合は、接続先だけを`127.0.0.1`へ変更します。

```bash
HAKONIWA_ROS2_TCP_HOST=127.0.0.1 \
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

画面のないHostでは、選択したコマンドへ`--headless`を追加します。正常時は次の形式で表示されます。

```text
Launcher        : /.../work-host/recipes/nova5-joint-trajectory-control/config/launcher.json
ROS 2 TCP       : enabled
```

`ROS 2 TCP`が`enabled`ならOKです。`error:`で終了した場合はNGです。

## 2. Host側Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で生成したLauncherと、Forge済み`nova5.contact.xml` |
| この作業のゴール | `robot-arm-hakoniwa-asset`が`../work-host`へ生成される。 |

Viewerを使用する場合は次を実行します。

```bash
python tools/recipe/nova5.py build
```

画面のないHostでは`python tools/recipe/nova5.py build --headless`へ置き換えます。続けて成果物と設定を確認します。

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

```bash
cd /absolute/path/to/hakoniwa-robot-arm
HAKONIWA_DOCKER_GUI=off \
HAKONIWA_ROS2_TCP_CONFIG=../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp \
bash docker/run.bash jazzy
```

Humbleでは`jazzy`を`humble`へ置き換えます。起動ログに次が表示され、Container shellが開けばOKです。

```text
Mount: ... -> /workspace
Container: hakoniwa-arm-dev-jazzy; ...
GUI: off; DISPLAY: disabled
```

このshellを終了するとContainerも削除されるため、以後`docker-ros-bridge`端末として最後まで開いたままにします。

## 4. ROS 2 Bridgeとサンプルをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-bridge` |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainerと、distribution単位の`HAKONIWA_ROS2_WS` |
| この作業のゴール | ROS 2 Bridgeとサンプルの`control`、`monitor`が実行可能になる。 |

```bash
/usr/bin/python3 tools/recipe/ros2_workspace.py build
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor

colcon --log-base "${HAKONIWA_ROS2_WS}-samples/log" build \
  --base-paths ros2_packages/hakoniwa_arm_samples \
  --build-base "${HAKONIWA_ROS2_WS}-samples/build" \
  --install-base "${HAKONIWA_ROS2_WS}-samples/install" \
  --symlink-install \
  --packages-select hakoniwa_arm_samples

source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"
ros2 pkg executables hakoniwa_arm_samples
```

doctorに`hakoniwa_pdu_ros bridge`、最後のコマンドに次の2行が表示されればOKです。

```text
hakoniwa_arm_samples control
hakoniwa_arm_samples monitor
```

ROS 2成果物は`/workspace/ros2-work-jazzy`または`/workspace/ros2-work-humble`へ保存され、同じdistributionのdocker-only構成でも再利用します。

次は[host+docker起動・動作確認](operation.md)へ進んでください。
