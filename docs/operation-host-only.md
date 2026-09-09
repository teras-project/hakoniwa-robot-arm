# host-only起動・動作確認

[host-onlyビルド](build-host-only.md)の完了が前提です。箱庭シミュレーション単体と、Ubuntu Host上のROS 2連携を分けて説明します。

## A. 箱庭シミュレーション単体

Composerの`(hako)` shellで実行します。Viewerを使う場合は`--headless`を付けません。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

LauncherがNova5 Runtimeとデモ軌道送信を起動します。`RUNNING`になり、Viewerありの場合はNova5が動作することを確認します。headlessでビルドした場合は、`configure`にも`--headless`を追加します。

確認後に停止します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

## B. Ubuntu Host上のROS 2連携

### 1. Nova5とHost TCP Bridge

Composerの`(hako)` shellで実行します。先に単体モードを起動した場合は停止してから再configureしてください。

```bash
export HAKONIWA_ROS2_TCP_HOST=127.0.0.1
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/ros2_tcp.py" doctor --robot nova5
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`status`が`RUNNING`になることを確認します。LauncherがNova5 RuntimeとHost側のSHM/TCP Bridgeを一緒に起動するため、`ros2_tcp.py start-host`は実行しません。

### 2. ROS Bridge

箱庭Workspaceへ入っていないROS 2 shellで実行し、開いたままにします。

```bash
source /opt/ros/jazzy/setup.bash
source "$HAKONIWA_ROS2_WS/activate.bash"
export HAKONIWA_ROS_BINDING="$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json"

test -f "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

### 3. monitorとcontrol

さらに2つの通常ROS 2 shellを開きます。新しいROS 2 shellごとに、最初に次の共通初期化を実行します。

```bash
source /opt/ros/jazzy/setup.bash
export CHECKOUT_ROOT="$HOME/hakoniwa-robot-arm-workspace"
export ARM_PACK="$CHECKOUT_ROOT/hakoniwa-robot-arm"
export HAKONIWA_WORK_DIR="$CHECKOUT_ROOT/work-host-nova5"
export HAKONIWA_ROS2_WS="$CHECKOUT_ROOT/ros2-work-host-jazzy"
source "$HAKONIWA_ROS2_WS/activate.bash"
```

monitor shell:

```bash
ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

control shell:

```bash
ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

Viewer上の動作と、monitorに表示される`joint1`から`joint6`の変化を確認します。

### 4. 終了

control、monitor、ROS BridgeをCtrl+Cで停止し、Composerの`(hako)` shellでNova5を停止します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`TERMINATED`になったことを確認してください。
