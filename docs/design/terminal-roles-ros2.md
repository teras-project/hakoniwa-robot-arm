# Host ROS 2連携の端末ロール

Host ROS 2連携では、動作確認時に合計4端末を使用します。`host-hako`は起動中のRuntimeを維持し、残りの3端末は通常のHost terminalからprofileをsourceして作成します。

| ロール | prompt | 維持するもの／実行すること |
| --- | --- | --- |
| `host-hako` | `(host-hako) (hako)` | Nova5 Runtime、MuJoCo Viewer、Host SHM/TCP Bridgeを起動・維持する。 |
| `host-ros-bridge` | `(host-ros-bridge)` | 箱庭PDUとROS topicを接続するROS Bridgeを起動・維持する。 |
| `host-ros-monitor` | `(host-ros-monitor)` | `/pdu/joint_states`を受信し、関節状態を観察する。 |
| `host-ros-control` | `(host-ros-control)` | `/joint_trajectory`へ軌道指令を送信する。 |

```text
host-hako ── Runtime / Viewer / Host TCP Bridge
     │
     └── host-ros-bridge ── ROS Bridge
                 │
                 ├── host-ros-monitor ── JointStateを観察
                 └── host-ros-control ── JointTrajectoryを送信
```

ROS 2 workspaceをbuildする段階では、通常のHost terminalに`host-ros-build` profileをsourceします。このロールはbuild専用であり、動作確認時の4端末には含めません。

初回の`host-hako`は、Robot Arm repositoryの通常Host terminalから開きます。

```bash
source profiles/tool-env/enter-host-hako.bash
```

`nova5.py configure --ros2-tcp`が完了すると、`$HAKONIWA_WORK_DIR/profiles/`へ各ROS 2端末のprofileが生成されます。具体的なsource手順と実行順序は[Host ROS 2連携手順](../procedures/host-ros2/operation.md)を参照してください。
