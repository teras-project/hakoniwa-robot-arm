# docker-onlyビルド

[docker-onlyセットアップ](setup.md)の完了が前提です。箱庭workは`/workspace/work-docker-<distro>`、ROS 2成果物は共有の`/workspace/ros2-work-<distro>`を使用します。

## 1. ROS 2連携用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | Forge済み`nova5.contact.xml`と、同じContainer内で動くROS 2 Bridge |
| この作業のゴール | ROS 2用Launcher、TCP設定、`binding.json`がContainer側workへ生成される。 |

macOS Docker Desktop、CI、画面のない環境ではheadless構成を生成します。

```bash
HAKONIWA_ROS2_TCP_HOST=127.0.0.1 \
python tools/recipe/nova5.py configure \
  --headless --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

Linux HostでX11 Viewerを有効にした場合だけ、`--headless`を外します。

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

headless構成では次を実行します。

```bash
python tools/recipe/nova5.py build --headless
```

X11 Viewerを使用する構成では`python tools/recipe/nova5.py build`へ置き換えます。続けて確認します。

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

```bash
cd /absolute/path/to/hakoniwa-robot-arm
bash docker/attach.bash jazzy
```

Humbleでは`jazzy`を`humble`へ置き換えます。Container shellが開き、`echo "$HAKONIWA_ROS2_WS"`に`/workspace/ros2-work-jazzy`または`/workspace/ros2-work-humble`が表示されればOKです。

## 4. ROS 2 Bridgeとサンプルをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-build` |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainerと、configure済みTCP設定 |
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

doctorに`hakoniwa_pdu_ros bridge`、最後のコマンドに`hakoniwa_arm_samples control`と`hakoniwa_arm_samples monitor`が表示されればOKです。

このROS 2成果物は、同じdistribution・CPU architectureのhost+docker構成でも再利用できます。build完了後は`docker-ros-build`を`exit`して構いません。`docker-hako`とContainerは終了しないでください。

次は[docker-only起動・動作確認](operation.md)へ進んでください。
