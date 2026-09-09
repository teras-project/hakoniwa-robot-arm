# docker-onlyビルド

[docker-onlyセットアップ](setup-docker-only.md)の完了が前提です。同じ1つのContainerを使用します。

## 1. Nova5 Runtime

`run.bash`からWorkspaceへenterした`(hako)` shellで実行します。

native Linux HostでViewerを使用する場合:

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

macOS Docker Desktop、CI、画面のない環境ではheadlessでビルドします。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

`nova5.py doctor`は、Launcher設定も検査するため、この時点では実行しません。[operation-docker-only.md](operation-docker-only.md)で利用モードを`configure`した後に実行します。

## 2. ROS 2 workspace

通常Host terminalから同じContainerへattachします。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
bash docker/attach.bash jazzy
```

attachしたshellは箱庭Workspaceへenterしません。ROS 2専用workspaceを構築します。

```bash
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" build
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" doctor
```

`doctor`でBridge、`control`、`monitor`が検出されることを確認します。attach shellを閉じても、最初のrun shellとContainerは終了しないでください。

次は[docker-only起動・動作確認](operation-docker-only.md)へ進んでください。
