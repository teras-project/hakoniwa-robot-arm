# Host ROS 2連携の起動・動作確認

[Host ROS 2連携ビルド](build.md)の完了が前提です。この構成では4端末を同時に使用します。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `host-hako` | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `host-ros-bridge` | 箱庭PDUとROS topicを接続するROS Bridge | 起動したまま |
| `host-ros-monitor` | `/pdu/joint_states`のmonitor | 受信したまま |
| `host-ros-control` | `/joint_trajectory`への軌道送信 | 送信後に終了 |

## 1. RuntimeとHost TCP Bridgeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | ROS 2用`launcher.json`、build済み`robot-arm-hakoniwa-asset`、生成済みROS binding |
| この作業のゴール | Nova5 Runtime、Viewer、Host TCP Bridgeが`RUNNING`になる。 |

```bash
python tools/recipe/nova5.py doctor
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

doctorの全項目が`[OK]`で、start後に`Nova5 demo is running in the background.`、statusに`RUNNING`が表示されれば次へ進みます。このLauncherがHost TCP Bridgeを起動するため、`ros2_tcp.py start-host`を別途実行しません。

## 2. ROS Bridgeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-bridge`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みROS 2 workspace、`activate-host-ros-bridge.bash`、生成済み`binding.json` |
| この作業のゴール | ROS Bridgeが起動し、箱庭PDUとROS topicの変換を継続する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
ls -l ../work-host/profiles/activate-host-ros-bridge.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`なら実行を止め、[ROS 2連携用configure](build.md#1-ros-2連携用launcherを生成する)へ戻ります。

```bash
source ../work-host/profiles/activate-host-ros-bridge.bash
ls -l ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
ros2 run hakoniwa_pdu_ros bridge \
  --config ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

`ls`でbindingが表示され、Bridgeがerrorなく起動を継続すればOKです。このterminalは開いたままにします。

## 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-monitor`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、`activate-host-ros-monitor.bash`、build済みのサンプル用ROS 2ワークスペース |
| この作業のゴール | `/pdu/joint_states`から`joint1`〜`joint6`の現在角度を継続受信する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source ../work-host/profiles/activate-host-ros-monitor.bash
source ../work-host/ros2-samples/install/setup.bash

ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

OKの場合は、次の形式のログが繰り返し表示されます。数値は実行ごとに変わります。

```text
[INFO] [...] [hakoniwa_arm_joint_state_monitor]: monitoring /pdu/joint_states
[INFO] [...] [hakoniwa_arm_joint_state_monitor]: joint1=..., joint2=..., joint3=..., joint4=..., joint5=..., joint6=...
```

`monitoring`だけで関節値が表示されない場合はNGです。このterminalは観察のため開いたままにします。

## 4. JointTrajectoryを送信する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-control`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、受信中のJointState monitor、`activate-host-ros-control.bash`、build済みのサンプル用ROS 2ワークスペース |
| この作業のゴール | 6関節・4点のJointTrajectoryを送信し、Viewerとmonitorの両方で関節動作を確認する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source ../work-host/profiles/activate-host-ros-control.bash
source ../work-host/ros2-samples/install/setup.bash

ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

送信に成功すると、次の形式のログが表示されます。

```text
[INFO] [...] [hakoniwa_arm_trajectory_sample]: published 4 points for 6 joints to /joint_trajectory
```

このログに加え、Viewer上でNova5が動き、`host-ros-monitor`の6関節値が変化すればOKです。`--amplitude`と`--duration`の意味は[ROS 2によるアーム操作](../ros2/arm-operations.md)を参照してください。

## 5. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-ros-control`、`host-ros-monitor`、`host-ros-bridge`、最後に`host-hako` |
| 実行ディレクトリ | `host-hako`では`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 動作確認済みで`RUNNING`のNova5 Runtimeと、起動中のROS process |
| この作業のゴール | ROS processとNova5 Runtimeがすべて停止し、Runtimeの状態が`TERMINATED`になる。 |

先に`host-ros-control`、`host-ros-monitor`、`host-ros-bridge`をCtrl+Cで停止します。最後に`host-hako`で実行します。

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`status`が`TERMINATED`を返せば終了完了です。
