# host-onlyビルド

[host-onlyセットアップ](setup-host-only.md)の完了が前提です。

## 1. Nova5 Runtime

セットアップで開いたComposerの`(hako)` shellで実行します。

Viewerを利用する場合は通常ビルドを行います。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

画面のないHostや自動確認ではheadlessでビルドします。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

実行ファイルが選択したHost workへ生成されていることを確認します。

```bash
test -x "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset"
```

`nova5.py doctor`は、Launcher設定も検査するため、この時点では実行しません。[operation-host-only.md](operation-host-only.md)で利用モードを`configure`した後に実行します。

## 2. ROS 2 workspace（UbuntuでROS 2連携する場合）

ROS 2を使わない箱庭シミュレーション単体の場合、この節はスキップします。

[setup-host-only.md](setup-host-only.md#5-ros-2側の通常shell)で準備した、箱庭WorkspaceではないROS 2 shellで実行します。

```bash
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" build
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" doctor
```

`doctor`で`hakoniwa_pdu_ros`のBridgeと、`hakoniwa_arm_samples`の`control`、`monitor`が検出されることを確認します。

次は[host-only起動・動作確認](operation-host-only.md)へ進んでください。
