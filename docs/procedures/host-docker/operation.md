# host+docker起動・動作確認

[host+dockerビルド](build.md)の完了が前提です。動作確認では4端末を使用します。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `host-hako` | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `docker-ros-bridge` | ROS 2 Bridge。`docker/run.bash`で開いたContainer shell | 起動したまま |
| `docker-ros-monitor` | `/pdu/joint_states`のmonitor。追加attach shell | 受信したまま |
| `docker-ros-control` | `/joint_trajectory`への軌道送信。追加attach shell | 送信後に終了 |

## 1. Host側Nova5を起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | ROS 2用Launcher、build済みRuntime、Host TCP Bridge設定 |
| この作業のゴール | Nova5 Runtime、Viewer、Host TCP Bridgeが`RUNNING`になる。 |

```bash
python tools/recipe/nova5.py doctor
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

doctorの全項目が`[OK]`で、statusが`RUNNING`ならOKです。Viewerありの場合は、Host画面にNova5と周辺環境が表示されることも確認します。

## 2. ROS 2 Bridgeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-bridge` |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | build済みROS 2 Bridgeと、Containerへmount済みの`binding.json` |
| この作業のゴール | ROS 2 Bridgeが起動し、Host TCP Bridgeへの接続を維持する。 |

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor
ls -l "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

doctorがerrorなく終了し、`binding.json`が表示され、Bridgeが終了せず動作を継続すればOKです。この端末は開いたままにします。

## 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この操作後のattach shellが`docker-ros-monitor`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainer、Runtime、ROS 2 Bridge、build済みサンプル |
| この作業のゴール | `/pdu/joint_states`から6関節の状態を継続受信する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
bash docker/attach.bash jazzy
source "$HAKONIWA_ROS2_WS/activate.bash"
source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"

ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

Humbleでは`jazzy`を`humble`へ置き換えます。`monitoring /pdu/joint_states`に続いて`joint1`から`joint6`の値が繰り返し表示されればOKです。この端末は開いたままにします。

## 4. JointTrajectoryを送信する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | さらに新しい通常Host terminal。この操作後のattach shellが`docker-ros-control`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のRuntimeとROS 2 Bridge、受信中のmonitor |
| この作業のゴール | JointTrajectoryを送信し、Viewerとmonitorで関節動作を確認する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
bash docker/attach.bash jazzy
source "$HAKONIWA_ROS2_WS/activate.bash"
source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"

ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

`published 4 points for 6 joints`が表示され、monitorの関節値が変化すればOKです。Viewerありの場合はNova5の動作も確認します。`monitor`が表示する値と、`--amplitude`、`--duration`の意味は[ROS 2によるアーム操作](../ros2/arm-operations.md)を参照してください。

## 5. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-control`、`docker-ros-monitor`、`docker-ros-bridge`、最後に`host-hako` |
| 実行ディレクトリ | `host-hako`では`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 動作確認済みで起動中の全process |
| この作業のゴール | ROS 2 process、Nova5 Runtime、Containerがすべて終了する。 |

先にcontrol、monitor、ROS 2 BridgeをCtrl+Cで停止します。`host-hako`でRuntimeを停止します。

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`TERMINATED`を確認した後、attach shellを`exit`し、最後に`docker-ros-bridge`を`exit`します。最後の操作でContainerが削除されますが、`/workspace/ros2-work-<distro>`の成果物はHost側に残ります。
