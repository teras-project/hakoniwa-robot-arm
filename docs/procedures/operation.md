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

以下の`bash`コマンド例はLinux/macOSの箱庭Workspace用です。Windowsでは上の表にあるWindows専用手順のPowerShellコマンドを使用してください。

ROS 2連携を使用する場合は、次の2トピックを確認します。

確認するトピック（参照用。コマンドではない）:
```text
/joint_trajectory   trajectory_msgs/msg/JointTrajectory
/pdu/joint_states   sensor_msgs/msg/JointState
```

期待結果は次のとおりです。

- Nova5 RuntimeとLauncherが`RUNNING`になる。
- `control`が6軸の軌道をpublishする。
- Viewerありの場合はNova5の動作を画面で確認できる。
- `monitor`の`joint1`から`joint6`が軌道指令に応じて変化する。

Viewerでは`p`でpause/resume、`r`でreset、`q`またはEscでViewerを閉じます。通常終了ではROSプロセスをCtrl+Cで停止してから、箱庭WorkspaceでLauncherを停止します。

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
