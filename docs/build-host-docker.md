# host+dockerビルド

[host+dockerセットアップ](setup-host-docker.md)の完了が前提です。

## 1. HostのNova5 Runtime

HostのComposer `(hako)` shellで実行します。人がViewerを確認する場合は通常ビルドを使用します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

画面のない環境や自動確認ではheadlessでビルドします。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

## 2. Host側のROS 2 TCP設定

同じ`(hako)` shellで、Dockerから見えるHost名を指定してLauncherとTCP設定を生成します。

macOS Docker Desktop:

```bash
export HAKONIWA_ROS2_TCP_HOST=host.docker.internal
```

Linux Hostの既定host network:

```bash
export HAKONIWA_ROS2_TCP_HOST=127.0.0.1
```

Viewerありの場合:

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

headlessの場合:

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --headless --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

続けて設定を検査し、Dockerへ渡すHost側パスを確認します。

```bash
python "$ARM_PACK/tools/recipe/ros2_tcp.py" doctor --robot nova5
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/ros2_tcp.py" config-root --robot nova5
```

最後のコマンドが表示した絶対パスを、次節の`HAKONIWA_ROS2_TCP_CONFIG`へ指定します。

## 3. ROS 2 Containerとworkspace

通常Host terminalで実行します。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
export NOVA5_HOST_WORK="$HOME/hakoniwa-robot-arm-workspace/work-host-nova5"
export HAKONIWA_ROS2_TCP_CONFIG="$NOVA5_HOST_WORK/recipes/nova5-joint-trajectory-control/config/ros2-tcp"
export HAKONIWA_DOCKER_GUI=off

bash docker/run.bash jazzy
```

改名または標準外配置のComposerを使う場合は、`run.bash`より前に`HAKONIWA_COMPOSER`も設定します。

Container内では箱庭Workspaceへenterしません。新しいROS 2 workspaceを構築します。

```bash
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" build
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" doctor
```

`doctor`でBridge、`control`、`monitor`が検出されることを確認します。このrun shellとContainerを終了せず、[host+docker起動・動作確認](operation-host-docker.md)へ進んでください。

