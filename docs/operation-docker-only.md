# docker-only起動・動作確認

[docker-onlyビルド](build-docker-only.md)の完了が前提です。Nova5とROS 2を、セットアップで起動した同じ1つのContainer内で動かします。

`HAKONIWA_ROS2_TCP_CONFIG`は使用しません。TCP設定はContainer内の同じ`HAKONIWA_WORK_DIR`へ生成し、各attach shellから直接参照します。

## 1. Nova5を起動

`run.bash`からWorkspaceへenterした`(hako)` shellで実行します。

native Linux HostでViewerを使用する場合:

```bash
export HAKONIWA_ROS2_TCP_HOST=127.0.0.1
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/ros2_tcp.py" doctor --robot nova5
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

macOS Docker Desktop、CI、画面のない環境ではheadlessを指定します。

```bash
export HAKONIWA_ROS2_TCP_HOST=127.0.0.1
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --headless --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/ros2_tcp.py" doctor --robot nova5
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`status`が`RUNNING`になることを確認します。Viewerありの場合は、Nova5と周辺環境がHost画面に表示されることも確認します。

## 2. ROS Bridge

通常Host terminalから同じContainerへattachし、Bridgeを起動したままにします。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
bash docker/attach.bash jazzy
source "$HAKONIWA_ROS2_WS/activate.bash"

export HAKONIWA_ROS_BINDING="$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json"
test -f "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

## 3. monitor

もう1つattach shellを開きます。

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

## 4. control

さらにもう1つattach shellを開きます。

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

Viewerありの場合はNova5の動作を確認します。Viewerの有無にかかわらず、monitorの`joint1`から`joint6`が変化することを確認します。

## 5. 終了

control、monitor、ROS BridgeをCtrl+Cで停止します。最初の`(hako)` shellで実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`TERMINATED`になったことを確認します。attach shellを閉じ、最後にrun shellを`exit`します。Containerは削除されますが、Host mount上のビルド、設定、ログは残ります。

Linux HostでX11接続を追加した場合は、Host側で許可を戻します。

```bash
xhost -si:localuser:root
```
