# host+docker起動・動作確認

[host+dockerビルド](build.md)の完了が前提です。基本経路は Dobot 仮想サービスです。動作確認では4端末を使用します。

手順: [一覧](../README.md) → [セットアップ](setup.md) → [ビルド](build.md) → **起動・動作確認**

各`docker-ros-*`端末はContainer内のROS 2環境です。通常のHost terminalからattachした後、Containerのプロンプトが表示されたことを確認してからContainer側のコマンドを実行してください。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `host-hako` | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `docker-ros-bridge` | Dobot service / topic launch。`docker/run.bash`で開いたContainer shell | 起動したまま |
| `docker-ros-monitor` | `/joint_states_robot` の monitor。追加attach shell | 受信したまま |
| `docker-ros-control` | Dobot 公式サービスによる dry-run / 小動作。追加attach shell | 実行後に終了 |

## 1. Host側Nova5を起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | Dobot に適用済み Launcher、build済み専用 Asset、Host TCP Bridge 設定 |
| この作業のゴール | Nova5 Runtime、Viewer、Host TCP Bridgeが`RUNNING`になる。 |

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py doctor
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

doctorの全項目が`[OK]`で、statusが`RUNNING`ならOKです。Viewerありの場合は、Host画面にNova5と周辺環境が表示されることも確認します。

## 2. Dobot サービスと状態 topic を起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-bridge` |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | build済みROS 2 Bridgeと、Containerへmount済みの`binding.json` |
| この作業のゴール | ROS 2 Bridgeが起動し、Host TCP Bridgeへの接続を維持する。 |

実行するコマンド（`docker-ros-bridge`）:
```bash
export DOBOT_WORK=/workspace/work-host
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 launch hakoniwa_dobot dobot.launch.py backend:=virtual \
  service_binding:="$DOBOT_WORK/dobot-services/dobot-services.json" \
  offset_dir:="$DOBOT_WORK/dobot-types/pdu/offset" \
  rpc_output:="$DOBOT_WORK/dobot-services/rpc" \
  topic_binding:="$HAKONIWA_ROS_BINDING"
```

service と topic の両 binding が有効になり、Bridge が終了せず動作を継続すればOKです。

## 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この操作後のattach shellが`docker-ros-monitor`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainer、Runtime、ROS 2 Bridge、build済みサンプル |
| この作業のゴール | `/joint_states_robot`から6関節の状態を約1 Hzで表示する。 |

新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認します。次のブロックだけを実行します。

実行するコマンド（通常のHost terminal。Containerに入る）:
```bash
bash docker/attach.bash jazzy
```

Containerのプロンプトが出てから、次を実行します。

実行するコマンド（`docker-ros-monitor`）:
```bash
cd ../hakoniwa-robot-arm
export DOBOT_WORK=/workspace/work-host
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 topic info /joint_states_robot
ros2 run hakoniwa_arm_samples monitor
```

Humbleでは`jazzy`を`humble`へ置き換えます。6関節の値が繰り返し表示されればOKです。この端末は開いたままにします。

## 4. Dobot サービスを確認し小動作を実行する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | さらに新しい通常Host terminal。この操作後のattach shellが`docker-ros-control`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のRuntimeとROS 2 Bridge、受信中のmonitor |
| この作業のゴール | `GetAngle` と dry-run で目標を点検し、明示的な小動作を Viewer / monitor で確認する。 |

さらに新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認します。次のブロックだけを実行します。

実行するコマンド（通常のHost terminal。Containerに入る）:
```bash
bash docker/attach.bash jazzy
```

Containerのプロンプトが出てから、次を実行します。

実行するコマンド（`docker-ros-control`）:
```bash
cd ../hakoniwa-robot-arm
export DOBOT_WORK=/workspace/work-host
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 service type /dobot_bringup_ros2/srv/GetAngle
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 run hakoniwa_arm_samples control
```

dry-run で目標 J1 +3° を点検し、virtual のみで `ros2 run hakoniwa_arm_samples control --execute --delta-deg 3` を実行します。monitor と Viewer で位置の変化を確認します。公式 `ros2 run dobot_demo demo` は **virtual 専用**で実行できますが、50° の動作を含みます。[安全上の警告](../ros2/arm-operations.md)を先に読んでください。

## 5. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-control`、`docker-ros-monitor`、`docker-ros-bridge`、最後に`host-hako` |
| 実行ディレクトリ | `host-hako`では`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 動作確認済みで起動中の全process |
| この作業のゴール | ROS 2 process、Nova5 Runtime、Containerがすべて終了する。 |

先に control 端末から `ros2 service call /dobot_bringup_ros2/srv/DisableRobot dobot_msgs_v4/srv/DisableRobot '{}'` を実行し、monitor と launch を Ctrl+C で停止します。`host-hako`でRuntimeを停止します。

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`TERMINATED`を確認した後、attach shellを`exit`し、最後に`docker-ros-bridge`を`exit`します。成果物は Host の `../work-host` に残ります。

## 発展：real／both

実機 IP を確認後、`real` は箱庭 Asset を起動せず `ros2 launch hakoniwa_dobot dobot.launch.py backend:=real robot_ip:=192.168.5.1` を使用します。`both` は手順2の launch で `backend:=both robot_ip:=192.168.5.1` に変更し、実機と箱庭の初期姿勢を事前に合わせます。`both` の monitor は `/real/joint_states_robot` と `/hakoniwa/joint_states_robot` を別端末で観測します。**公式 demo は real／both で実行禁止**。指令の受理は到達を意味せず、Stop は非常停止の代わりになりません。[安全上の警告と制限](../ros2/arm-operations.md)を参照してください。
