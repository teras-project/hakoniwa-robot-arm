# host+docker起動・動作確認

[host+dockerビルド](build-host-docker.md)の完了が前提です。Nova5とMuJoCoはHost、ROS 2はDocker Containerで動かします。

## 1. HostのNova5を起動

HostのComposer `(hako)` shellで実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`status`が`RUNNING`になることを確認します。Viewerありで構築した場合はHost画面にNova5と周辺環境が表示されます。LauncherはNova5 RuntimeとHost側SHM/TCP Bridgeを一緒に起動します。

## 2. ROS Bridge

`docker/run.bash`で開いたContainer shellで実行し、このshellを開いたままにします。

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" doctor
test -f "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

## 3. monitor

通常Host terminalで同じContainerへattachします。標準外配置のComposerでは、`run.bash`と同じ`HAKONIWA_COMPOSER`を事前に設定してください。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
bash docker/attach.bash jazzy
source "$HAKONIWA_ROS2_WS/activate.bash"

ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

## 4. control

さらに別の通常Host terminalから同じContainerへattachします。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
bash docker/attach.bash jazzy
source "$HAKONIWA_ROS2_WS/activate.bash"

ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

Viewerありの場合はNova5の動作を確認します。Viewerの有無にかかわらず、monitorの`joint1`から`joint6`が変化すればROS 2からの軌道制御と状態取得が成立しています。

## 5. 終了

control、monitor、ROS BridgeをCtrl+Cで停止します。HostのComposer `(hako)` shellでNova5を停止します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

`TERMINATED`になったことを確認し、attach shellを閉じ、最後にrun shellを`exit`します。

