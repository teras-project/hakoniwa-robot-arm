# 起動・動作確認手順

セットアップ・ビルド時に選んだ利用構成と同じ行の手順を使用してください。

[手順一覧](README.md) → [セットアップ](setup.md) → [ビルド](build.md) → **起動・動作確認**

| 利用構成 | 動作確認手順 |
| --- | --- |
| host-standalone | [箱庭単体の起動・動作確認](host-standalone/operation.md) |
| host-standalone + PS5 gamepad | [ゲームパッドの起動・操作](host-standalone/operation-gamepad.md) |
| windows-host-standalone | [Windows native起動・動作確認](windows-host-standalone/operation.md) |
| windows-host-docker | [Windows host+Docker起動・動作確認](windows-host-docker/operation.md) |
| host-ros2 | [Host ROS 2連携の起動・動作確認](host-ros2/operation.md) |
| host+docker | [operation-host-docker.md](host-docker/operation.md) |
| docker-only | [operation-docker-only.md](docker-only/operation.md) |

## ROS 2連携の確認対象

以下の`bash`コマンド例はLinux/macOSの箱庭Workspace用です。Windows native Host + Docker は[専用のPowerShell手順](windows-host-docker/operation.md)に従い、未検証のビルド・結合で失敗したら停止してください。

ROS 2 連携では、virtual のサービスと状態 topic を確認します。

確認する接続点（参照用。コマンドではない）:
```text
/dobot_bringup_ros2/srv/GetAngle    dobot_msgs_v4/srv/GetAngle
/dobot_bringup_ros2/srv/MovJ        dobot_msgs_v4/srv/MovJ
/joint_states_robot                sensor_msgs/msg/JointState
```

期待結果は次のとおりです。

- Nova5 RuntimeとLauncherが`RUNNING`になる。
- `control` は現在角からの +3° を dry-run 表示し、明示的な `--execute` でサービスを呼ぶ。
- 箱庭だけで公式 `dobot_demo demo` の連続する移動を確認する（実機には送らない）。
- Viewerありの場合はNova5の動作を画面で確認できる。
- `monitor`の6軸が動作に応じて変化する（既定表示周期 1 Hz）。

Viewerでは`p`でpause/resume、`r`でreset、`q`またはEscでViewerを閉じます。pause 中はサービスが timeout する可能性があります。通常終了ではロボットを無効化し、ROS プロセスを Ctrl+C で停止してから、箱庭 Workspace で Launcher を停止します。公式デモの 50° の動作を **real／both に送らない**でください。

実行するコマンド（選択した構成の箱庭Workspace）:
```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

ログとセッション情報の配置先（参照用。コマンドではない）:

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/logs/
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/runtime/launcher-session.json.log
```
