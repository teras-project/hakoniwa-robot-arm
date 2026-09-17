# 端末ロール

この文書は、host-onlyでNova5を動かすときに必要な端末の役割を定義します。端末を閉じて開き直しても、対応するprofileをsourceすれば同じロールを再現できます。

## 単体デモ

単体デモでは、端末は1つです。

| ロール | prompt | 役割 |
| --- | --- | --- |
| `host-hako` | `(host-hako) (hako)` | 箱庭Workspace、Foundation、Forge、Runtime、MuJoCo Viewerを操作する。 |

## ROS 2連携

ROS 2連携では、合計4端末を開きます。`host-hako`は起動中のRuntimeを維持し、残りの3端末は通常のHost terminalからprofileをsourceして作成します。

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

## profileの使用

初回の`host-hako`は、Robot Arm repositoryの通常Host terminalから開きます。

```bash
source profiles/tool-env/enter-host-hako.bash
```

`nova5.py configure --ros2-tcp`が完了すると、`$HAKONIWA_WORK_DIR/profiles/`へ各ロールのprofileが生成されます。新しい通常Host terminalでは、まず共通profileをsourceしてから、対応するローカルprofileをsourceします。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source "$HAKOBASE_DIR/work-host/profiles/activate-host-ros-bridge.bash"
```

profileが設定するパスと生成時点は[環境profile](environment-profiles.md)を参照してください。
