# 起動・動作確認手順

セットアップ・ビルド時に選んだ利用構成と同じ行の手順を使用してください。

| 利用構成 | 動作確認手順 |
| --- | --- |
| host-only | [operation-host-only.md](operation-host-only.md) |
| host+docker | [operation-host-docker.md](operation-host-docker.md) |
| docker-only | [operation-docker-only.md](operation-docker-only.md) |

## ROS 2連携の確認対象

ROS 2連携を使用する場合は、次の2トピックを確認します。

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

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

ログとセッション情報は次に生成されます。

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/logs/
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/runtime/launcher-session.json.log
```

