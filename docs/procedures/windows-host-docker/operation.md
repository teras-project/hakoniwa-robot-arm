# Windows host+Docker起動・動作確認

[Windows host+Dockerビルド](build.md)の完了後、4端末でMuJoCo Viewer、ROS 2 Bridge、JointState、JointTrajectoryを確認します。

| 端末 | 環境 | 実行するもの |
| --- | --- | --- |
| `host-hako` | Windows PowerShell | Nova5 Runtime、MuJoCo Viewer、Host TCP Bridge |
| `docker-ros-bridge` | 起動済みContainer | ROS 2 Bridge |
| `docker-ros-monitor` | 追加Container shell | JointState monitor |
| `docker-ros-control` | 追加Container shell | JointTrajectory control |

## 1. Host側Nova5を起動する

`hakoniwa-business-pack`のrepository rootを開いたPowerShellで実行します。

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py doctor

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py start

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
```

次を確認します。

- `status`が`RUNNING`
- MuJoCo ViewerにNova5と周辺環境が表示される
- `work\recipes\nova5-joint-trajectory-control\logs\nova5-ros2-tcp-bridge.out`に`bridge_time_source=hakoniwa_callback`がある
- Bridgeが`0xc0000005`で終了しない

初回起動時にWindows Defender Firewallの許可画面が表示される場合があります。Docker DesktopからHost TCP Bridgeへの通信に必要なため、所属組織のポリシーに従って必要なネットワークだけを許可してください。安易にPublic network全体を許可しないでください。拒否した場合、Container側BridgeがHostへ接続できないことがあります。

## 2. ROS 2 Bridgeを起動する

build時から開いている`docker-ros-bridge`で実行し、この端末を維持します。

```bash
cd /workspace/hakoniwa-robot-arm
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor
test -f "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

doctorが成功し、Bridgeが終了せずHostとの接続を維持すればOKです。

## 3. JointStateを観察する

新しいPowerShellで追加shellを開きます。

```powershell
docker exec -it `
  --workdir /workspace/hakoniwa-robot-arm `
  hakoniwa-arm-dev-jazzy `
  /ros_entrypoint.sh bash
```

開いた`docker-ros-monitor`で実行します。

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"
ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

`monitoring /pdu/joint_states`に続いて、`joint1`から`joint6`の値が繰り返し表示されればOKです。この端末は開いたままにします。

## 4. JointTrajectoryを送信する

さらに新しいPowerShellで、手順3と同じ`docker exec`を実行して`docker-ros-control`を開きます。

```bash
source "$HAKONIWA_ROS2_WS/activate.bash"
source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"
ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

次を確認します。

- `published 4 points for 6 joints`と表示される
- monitorに表示される6関節の値が変化する
- MuJoCo Viewer上のNova5が軌道に従って動く

## 5. 終了する

次の順序で終了します。

1. `docker-ros-control`を終了する。
2. `docker-ros-monitor`と`docker-ros-bridge`のROS 2 processをCtrl+Cで停止する。
3. Windows HostのRuntimeを停止する。

`host-hako`のPowerShellで実行します。

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py stop

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
```

`TERMINATED`を確認後、追加Container shellを`exit`し、最後に`docker-ros-bridge`を`exit`します。`--rm`で起動しているためContainerは削除されますが、`ros2-work-jazzy`の成果物はWindows Host側に残ります。

## 6. トラブルシューティング

| 症状 | 確認と対処 |
| --- | --- |
| `docker run`がHost pathをmountできない | Docker Desktopが起動済みか、checkoutを置いたdrive／directoryへのfile sharingが許可されているか確認する。 |
| ROS 2 BridgeがHostへ接続できない | Hostの`status`が`RUNNING`か、設定が`host.docker.internal`か、Windows Defender Firewallで必要な通信を拒否していないか確認する。 |
| Host TCP Bridgeが`0xc0000005`で終了する | 古いFoundation成果物が残っている可能性がある。最新revisionを取得してRecipeを再configureし、Core receiptの`callback_assets_shared: true`を確認してから再buildする。 |
| `ros2 topic info`にtopicがない | Host TCP Bridge、Container側ROS 2 Bridgeの順で起動しているか、`HAKONIWA_ROS_BINDING`が`/ros2-tcp/ros/binding.json`を指しているか確認する。 |

調査時は、Hostの`work\recipes\nova5-joint-trajectory-control\logs\`と、各ROS 2端末の標準出力をセットで確認してください。
