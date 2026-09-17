# host-only起動・動作確認

[host-onlyビルド](build-host-only.md)で選択した構成に合わせて、AまたはBへ進みます。

- 単体デモ用にconfigureした場合: A
- `configure --ros2-tcp`を実行し、ROS 2 workspaceもbuildした場合: B

## A. 箱庭シミュレーション単体

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 単体デモ用`launcher.json`、build済み`robot-arm-hakoniwa-asset`、Forge済み`nova5.contact.xml` |
| この作業のゴール | ROS 2を使わず、Runtime、PDU、MuJoCo Viewer、自動デモ軌道が一連で動作する。 |

この構成では`start`直後に自動デモ軌道が送信され、Nova5が動きます。これはROS 2制御ではなく、箱庭シミュレーション単体の動作確認です。

```bash
python tools/recipe/nova5.py doctor
```

すべての行が`[OK]`なら起動します。`[NG]`が一つでもあれば起動しません。

```bash
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

次の状態を確認します。

- terminalに`Nova5 demo is running in the background.`が表示される。
- `status`が`RUNNING`を返す。
- MuJoCo Viewer上でNova5が自動軌道を動く。

一つでも満たさなければNGです。確認後に停止します。

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`status`が`TERMINATED`を返せば停止完了です。

## B. Ubuntu Host上のROS 2連携

この構成では4端末を同時に使用します。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `host-hako` | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `host-ros-bridge` | 箱庭PDUとROS topicを接続するROS Bridge | 起動したまま |
| `host-ros-monitor` | `/pdu/joint_states`のmonitor | 受信したまま |
| `host-ros-control` | `/joint_trajectory`への軌道送信 | 送信後に終了 |

### 1. RuntimeとHost TCP Bridgeを起動する

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

### 2. ROS Bridgeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-bridge`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みROS 2 workspace、`activate-host-ros-bridge.bash`、生成済み`binding.json` |
| この作業のゴール | ROS Bridgeが起動し、箱庭PDUとROS topicの変換を継続する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
ls -l ../work-host/profiles/activate-host-ros-bridge.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`なら実行を止め、[ROS 2連携用configure](build-host-only.md#b-ros-2連携)へ戻ります。

```bash
source ../work-host/profiles/activate-host-ros-bridge.bash
ls -l ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
ros2 run hakoniwa_pdu_ros bridge \
  --config ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

`ls`でbindingが表示され、Bridgeがerrorなく起動を継続すればOKです。このterminalは開いたままにします。

### 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-monitor`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、`activate-host-ros-monitor.bash` |
| この作業のゴール | `/pdu/joint_states`から`joint1`〜`joint6`の現在角度を継続受信する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source ../work-host/profiles/activate-host-ros-monitor.bash

ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

OKの場合は、次の形式のログが繰り返し表示されます。数値は実行ごとに変わります。

```text
[INFO] [...] [hakoniwa_arm_joint_state_monitor]: monitoring /pdu/joint_states
[INFO] [...] [hakoniwa_arm_joint_state_monitor]: joint1=..., joint2=..., joint3=..., joint4=..., joint5=..., joint6=...
```

`monitoring`だけで関節値が表示されない場合はNGです。このterminalは観察のため開いたままにします。

### 4. JointTrajectoryを送信する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-control`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、受信中のJointState monitor、`activate-host-ros-control.bash` |
| この作業のゴール | 6関節・4点のJointTrajectoryを送信し、Viewerとmonitorの両方で関節動作を確認する。 |

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source ../work-host/profiles/activate-host-ros-control.bash

ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

送信に成功すると、次の形式のログが表示されます。

```text
[INFO] [...] [hakoniwa_arm_trajectory_sample]: published 4 points for 6 joints to /joint_trajectory
```

このログに加え、Viewer上でNova5が動き、`host-ros-monitor`の6関節値が変化すればOKです。`--amplitude`と`--duration`の意味は[ROS 2によるアーム操作](ros2-arm-operations.md)を参照してください。

### 5. 終了する

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
