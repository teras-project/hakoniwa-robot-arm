# Host ROS 2連携の起動・動作確認

[Host ROS 2連携ビルド](build.md)の完了が前提です。基本経路は Dobot 仮想サービスです。この構成では4端末を同時に使用します。

手順: [一覧](../README.md) → [セットアップ](setup.md) → [ビルド](build.md) → **起動・動作確認**

`host-hako`はFoundationの`python`を使用します。各`host-ros-*`端末は別の通常Host terminalから開始し、それぞれのprofileでROS 2環境を有効にします。`host-hako`の中からROS 2 profileを読み込まないでください。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `host-hako` | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `host-ros-bridge` | Dobot Service Bridge と JointState topic Bridge をまとめる ROS launch | 起動したまま |
| `host-ros-monitor` | `/joint_states_robot` の monitor | 受信したまま |
| `host-ros-control` | Dobot 公式サービスによる dry-run / 安全な小動作 | 実行後に終了 |

## 1. RuntimeとHost TCP Bridgeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | Dobot 用に適用済みの`launcher.json`、build済み`robot-arm-dobot-asset`、生成済みROS service / topic binding |
| この作業のゴール | Nova5 Runtime、Viewer、Host TCP Bridgeが`RUNNING`になる。 |

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py doctor
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

doctorの全項目が`[OK]`で、start後に`Nova5 demo is running in the background.`、statusに`RUNNING`が表示されれば次へ進みます。このLauncherがHost TCP Bridgeを起動するため、`ros2_tcp.py start-host`を別途実行しません。

## 2. Dobot サービスと状態 topic を起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-bridge`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みROS 2 workspace、`activate-host-ros-bridge.bash`、生成済み`binding.json` |
| この作業のゴール | Dobot サービスと `/joint_states_robot` が使える。 |

新しい通常Host terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。

実行する確認コマンド（通常のHost terminal）:
```bash
ls -l ../work-host/profiles/activate-host-ros-bridge.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`なら実行を止め、[ROS 2連携用configure](build.md#1-ros-2連携用launcherを生成する)へ戻ります。

実行するコマンド（`host-ros-bridge`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-bridge.bash
export DOBOT_WORK="$(realpath ../work-host)"
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 launch hakoniwa_dobot dobot.launch.py \
  service_binding:="$DOBOT_WORK/dobot-services/dobot-services.json" \
  offset_dir:="$DOBOT_WORK/dobot-types/pdu/offset" \
  rpc_output:="$DOBOT_WORK/dobot-services/rpc" \
  topic_binding:="$DOBOT_WORK/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json"
```

この terminal を維持します。launch は PDU-RPC サービスと状態 topic binding の remap を同時に起動します。

## 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-monitor`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、`activate-host-ros-monitor.bash`、build済みのサンプル用ROS 2ワークスペース |
| この作業のゴール | `/joint_states_robot`から現在角度を継続受信する。 |

新しい通常Host terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。

実行するコマンド（`host-ros-monitor`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-monitor.bash
export DOBOT_WORK="$(realpath ../work-host)"
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 topic info /joint_states_robot
ros2 run hakoniwa_arm_samples monitor
```

6関節の値が約1 Hzで表示されればOKです。数値は実行ごとに変わります。

`monitoring`だけで関節値が表示されない場合はNGです。このterminalは観察のため開いたままにします。

## 4. Dobot サービスを確認し小動作を実行する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。profile適用後は`host-ros-control`。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、受信中のJointState monitor、`activate-host-ros-control.bash`、build済みのサンプル用ROS 2ワークスペース |
| この作業のゴール | `GetAngle` と dry-run で目標を点検し、明示的な小動作を Viewer / monitor で確認する。 |

新しい通常Host terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。`hakoniwa_arm_samples control` と公式 `dobot_demo demo` は同じ `/dobot_bringup_ros2/srv/*` を呼び、箱庭専用の宛先には固定されていません。dry-run の `GetAngle` も実機の同名サービスに届く可能性があり、`--execute` は実機を動かし得ます。**この箱庭手順では実機 driver を停止するか別の ROS domain に分離し、同名サービスの競合がないことを確認してから進んでください。** [操作と安全上の警告](../ros2/arm-operations.md)を参照してください。

実行するコマンド（`host-ros-control`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-control.bash
export DOBOT_WORK="$(realpath ../work-host)"
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 service type /dobot_bringup_ros2/srv/GetAngle
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 run hakoniwa_arm_samples control
```

dry-run で現在姿勢と J1 +3° の目標を確認してから、同じ `host-ros-control` 端末で小動作を実行します。

実行するコマンド（`host-ros-control`）:
```bash
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
```

Viewer と monitor の変化を確認します。続いて箱庭だけで公式デモを実行します。50° の絶対移動を含むため、[安全上の警告と API の制限](../ros2/arm-operations.md)を先に読み、同じ ROS domain に同名サービスを出す実機 driver がいないことを再確認してください。

実行するコマンド（`host-ros-control`）:
```bash
ros2 run dobot_demo demo
```

Viewer と monitor で連続する移動を確認します。

## 5. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-ros-control`、`host-ros-monitor`、`host-ros-bridge`、最後に`host-hako` |
| 実行ディレクトリ | `host-hako`では`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 動作確認済みで`RUNNING`のNova5 Runtimeと、起動中のROS process |
| この作業のゴール | ROS processとNova5 Runtimeがすべて停止し、Runtimeの状態が`TERMINATED`になる。 |

先に `host-ros-control` 端末で次のコマンドを実行します。

実行するコマンド（`host-ros-control`）:
```bash
ros2 service call /dobot_bringup_ros2/srv/DisableRobot dobot_msgs_v4/srv/DisableRobot '{}'
```

monitor と launch を Ctrl+C で停止します。最後に `host-hako` で実行します。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`status`が`TERMINATED`を返せば終了完了です。

## 次の段階：実機でも動かす

箱庭の確認を完了した Ubuntu host-ros2 環境からのみ、[実機 driver の追加と `real`／`both` への切り替え](real.md)へ進みます。公式デモの50°絶対移動は実機へ送らないでください。
