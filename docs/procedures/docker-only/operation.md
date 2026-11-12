# docker-only起動・動作確認

[docker-onlyビルド](build.md)の完了が前提です。基本経路は Dobot 仮想サービスです。同じContainer内に4つのshellを開きます。

手順: [一覧](../README.md) → [セットアップ](setup.md) → [ビルド](build.md) → **起動・動作確認**

`docker-hako`はFoundationの`python`、追加の`docker-ros-*` shellはROS 2専用環境を使います。Hostでattachを実行したらContainerのプロンプトを待ってから次のブロックを実行してください。

| 端末 | 実行するもの | 維持する状態 |
| --- | --- | --- |
| `docker-hako` | Nova5 Runtime、必要に応じてMuJoCo Viewer、Host TCP Bridge | `RUNNING` |
| `docker-ros-bridge` | Dobot service / topic launch。追加attach shell | 起動したまま |
| `docker-ros-monitor` | `/joint_states_robot` の monitor。追加attach shell | 受信したまま |
| `docker-ros-control` | Dobot 公式サービスによる dry-run / 小動作。追加attach shell | 実行後に終了 |

TCP設定は同じContainer内の`HAKONIWA_WORK_DIR`へ生成済みです。host+dockerで使用する`HAKONIWA_ROS2_TCP_CONFIG` mountは必要ありません。

## 1. Nova5 Runtimeを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | Dobot に適用済み Launcher、専用 Asset、TCP Bridge 設定 |
| この作業のゴール | Nova5 RuntimeとHost TCP Bridgeが`RUNNING`になる。 |

実行するコマンド（`docker-hako`の`(hako)` shell）:
```bash
python tools/recipe/nova5.py doctor
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

doctorの全項目が`[OK]`で、statusが`RUNNING`ならOKです。X11 Viewerを有効にした構成では、Nova5と周辺環境がHost画面に表示されることも確認します。

## 2. Dobot サービスと状態 topic を起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この操作後のattach shellが`docker-ros-bridge`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のContainer、Runtime、build済みROS 2 Bridge |
| この作業のゴール | ROS 2 Bridgeが起動し、同じContainer内のTCP Bridgeへの接続を維持する。 |

新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認します。次のブロックだけを実行します。

実行するコマンド（通常のHost terminal。Containerに入る）:
```bash
bash docker/attach.bash jazzy
```

Containerのプロンプトが出てから、次を実行します。

実行するコマンド（`docker-ros-bridge`）:
```bash
cd ../hakoniwa-robot-arm
export DOBOT_WORK="$HAKONIWA_WORK_DIR"
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

Humbleでは`jazzy`を`humble`へ置き換えます。Service Bridge と topic Bridge が終了せず動作を継続すればOKです。この端末は開いたままにします。

## 3. JointStateを観察する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この操作後のattach shellが`docker-ros-monitor`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のRuntimeとROS 2 Bridge、build済みサンプル |
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
export DOBOT_WORK="$HAKONIWA_WORK_DIR"
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 topic info /joint_states_robot
ros2 run hakoniwa_arm_samples monitor
```

6関節の値が繰り返し表示されればOKです。この端末は開いたままにします。

## 4. Dobot サービスを確認し小動作を実行する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | さらに新しい通常Host terminal。この操作後のattach shellが`docker-ros-control`になる。 |
| 実行ディレクトリ | Host上の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 起動中のRuntimeとROS 2 Bridge、受信中のmonitor |
| この作業のゴール | `GetAngle` と dry-run で目標を点検し、明示的な小動作を Viewer / monitor で確認する。 |

新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認します。次のブロックだけを実行します。

実行するコマンド（通常のHost terminal。Containerに入る）:
```bash
bash docker/attach.bash jazzy
```

Containerのプロンプトが出てから、次を実行します。`hakoniwa_arm_samples control` と公式 `dobot_demo demo` は同じ `/dobot_bringup_ros2/srv/*` を呼び、箱庭専用の宛先には固定されていません。dry-run の `GetAngle` も実機の同名サービスに届く可能性があり、`--execute` は実機を動かし得ます。**この箱庭手順では実機 driver を停止するか別の ROS domain に分離し、同名サービスの競合がないことを確認してから進んでください。** [安全上の警告](../ros2/arm-operations.md)を参照してください。

実行するコマンド（`docker-ros-control`）:
```bash
cd ../hakoniwa-robot-arm
export DOBOT_WORK="$HAKONIWA_WORK_DIR"
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 service type /dobot_bringup_ros2/srv/GetAngle
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 run hakoniwa_arm_samples control
```

dry-run で J1 +3° の目標を点検後、同じ `docker-ros-control` 端末で小動作を実行します。

実行するコマンド（`docker-ros-control`）:
```bash
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
```

monitor と（有効な場合）Viewer で位置の変化を確認します。続いて箱庭だけで公式デモを実行します。50° の絶対移動を含むため、[安全上の警告](../ros2/arm-operations.md)を先に読み、同じ ROS domain に同名サービスを出す実機 driver がいないことを再確認してください。

実行するコマンド（`docker-ros-control`）:
```bash
ros2 run dobot_demo demo
```

monitor で連続する移動を確認します。

## 5. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-ros-control`、`docker-ros-monitor`、`docker-ros-bridge`、最後に`docker-hako` |
| 実行ディレクトリ | `docker-hako`ではContainer内の`hakoniwa-robot-arm` repository root |
| この作業の入力成果物 | 動作確認済みで起動中の全process |
| この作業のゴール | ROS 2 process、Nova5 Runtime、Containerがすべて終了する。 |

先に `docker-ros-control` 端末で次のコマンドを実行します。

実行するコマンド（`docker-ros-control`）:
```bash
ros2 service call /dobot_bringup_ros2/srv/DisableRobot dobot_msgs_v4/srv/DisableRobot '{}'
```

monitor と launch を Ctrl+C で停止します。`docker-hako`でRuntimeを停止します。

実行するコマンド（`docker-hako`の`(hako)` shell）:
```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`TERMINATED`を確認した後、attach shellを`exit`し、最後に`docker-hako`のchild shellと親Container shellを順に`exit`します。Containerは削除されますが、Host mount上のbuild、設定、ログは残ります。

Linux HostでX11接続を許可した場合は、Host側で許可を戻します。

```bash
xhost -si:localuser:root
```
