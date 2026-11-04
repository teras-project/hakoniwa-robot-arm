# Windows host+Docker：Dobot 仮想サービスの起動・動作確認

[ビルド](build.md)のWindows Native PDU-RPC／専用Asset、Container内の公式ROSメッセージ・PDU型・service/topic binding、Launcherの切り替えが**すべて成功した場合のみ**実行します。**Windows Host + DockerのDobot結合は未検証です。** 基本経路は`backend:=virtual`です。`real`／`both`は実機の安全対策を伴う発展構成であり、未検証のWindows接続が動くと仮定しないでください。

| 端末 | 環境・実行するもの |
| --- | --- |
| `host-hako` | Windows PowerShell、`hakoniwa-business-pack`ルート：Windows Native AssetとHost TCP Bridge |
| `docker-ros-bridge` | [ビルド](build.md)から開いたContainer Bash：Dobot service/topic launch |
| `docker-ros-monitor` | 別のHost PowerShellから`docker exec`したContainer Bash：JointState |
| `docker-ros-control` | 別のHost PowerShellから`docker exec`したContainer Bash：安全なdry-run／小動作 |

[実行手順の索引](../README.md) | [セットアップ](setup.md) | [ビルド](build.md) | [安全上の警告](../ros2/arm-operations.md)

## 1. Windows HostでDobot Assetを起動

`hakoniwa-business-pack`ルートのHost PowerShellで、Windows用に適用済みの`launcher.json`と`robot-arm-dobot-asset.exe`を確認してから起動します。

```powershell
Get-Location
Test-Path .\work\recipes\nova5-joint-trajectory-control\config\launcher.pre-dobot.json
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py doctor
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py start
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
Test-NetConnection 127.0.0.1 -Port 54020
```

`launcher.pre-dobot.json`が存在し、doctorが`[OK]`、statusが`RUNNING`、`TcpTestSucceeded: True`となることを確認します。Viewerを使う場合はNova5も確認します。TCP 54020に接続できなければ、Native Assetの起動ログ、DLLの配置、Windows Defender Firewall、Host TCP Bridgeのログを調べて停止します。`Test-NetConnection`の接続成功だけではサービス機能の成功を意味しません。

## 2. DockerでDobot service/topic launchを起動

開いたままの`docker-ros-bridge`（Container Bash、`/workspace/hakoniwa-robot-arm`）で実行します。`/ros2-tcp/ros/binding.json`はWindows Hostが生成しread-only mountしたtopic binding、`/workspace/hakoniwa-business-pack/work/dobot-services`はContainerで生成したservice bindingです。両方を**同じlaunch**へ渡します。

```bash
cd /workspace/hakoniwa-robot-arm
export DOBOT_WORK=/workspace/hakoniwa-business-pack/work
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
test -f "$HAKONIWA_ROS_BINDING"
ros2 launch hakoniwa_dobot dobot.launch.py backend:=virtual \
  service_binding:="$DOBOT_WORK/dobot-services/dobot-services.json" \
  offset_dir:="$DOBOT_WORK/dobot-types/pdu/offset" \
  rpc_output:="$DOBOT_WORK/dobot-services/rpc" \
  topic_binding:="$HAKONIWA_ROS_BINDING"
```

Service Bridgeとtopic Bridgeが終了せず起動し、RPCサーバーへ接続できることを次の端末から確認します。ContainerとHostでROSの`ROS_DOMAIN_ID`を混在させず、Containerの各ROS端末で同じ`activate.bash`をsourceしてください（既定73）。

## 3. JointStateを監視

新しいHost PowerShellから追加Container shellを開きます。**PowerShellのブロックとContainer Bashのブロックは別々に実行**してください。

```powershell
docker exec -it `
  --workdir /workspace/hakoniwa-robot-arm `
  hakoniwa-arm-dev-jazzy `
  /ros_entrypoint.sh bash
```

Container Bash（`docker-ros-monitor`）:

```bash
export DOBOT_WORK=/workspace/hakoniwa-business-pack/work
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 topic info /joint_states_robot
ros2 run hakoniwa_arm_samples monitor
```

`/joint_states_robot`の6軸が約1 Hzで表示されることを確認します。JointStateの角度はrad、Dobot `GetAngle`はdegです。topicがない場合はHost TCP Bridgeのstatus、read-only mountの`HAKONIWA_ROS_BINDING`、Docker launchを調べます。

## 4. サービスでdry-run後に小動作を確認

別のHost PowerShellから手順3と同じ`docker exec -it ... /ros_entrypoint.sh bash`で`docker-ros-control`を開きます。Container Bashで実行します。

```bash
export DOBOT_WORK=/workspace/hakoniwa-business-pack/work
source "$DOBOT_WORK/ros2/activate.bash"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 service type /dobot_bringup_ros2/srv/GetAngle
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 run hakoniwa_arm_samples control
```

`GetAngle`の応答とdry-runの現在角・J1 +3°目標を点検します。**`backend:=virtual`であることと、実機driverがこのROS domainにいないことを確認**してから、小動作を明示的に実行します。

```bash
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
```

`control`は`EnableRobot`、`SpeedFactor=10%`、`MovJ`を使用します。応答`res=0`は受理であって到達ではありません。monitorの値とViewerの動きを確認してください。公式`dobot_demo/demo.py`は未変更で`ros2 run dobot_demo demo`から**virtualのみ**で実行できますが、J1 50°／J2 -8°への絶対角移動を含みます。[安全上の警告と仮想MovL／DOの制限](../ros2/arm-operations.md)を読んでから実行してください。**real／bothでは公式demoを実行しないでください。**

## 5. 停止

ROS control端末で`ros2 service call /dobot_bringup_ros2/srv/DisableRobot dobot_msgs_v4/srv/DisableRobot '{}'`を実行します。monitorとlaunchをCtrl+Cで止めてからHost PowerShell（Business Packルート）で実行します。

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py stop
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
```

`TERMINATED`を確認後、追加Container shellを`exit`し、最後に`docker-ros-bridge`を`exit`します。`--rm`でContainerは削除されますが、Host共有`work`内の生成物は残ります。

## 発展：real／both（実機・Windowsネットワーク未検証）

実機IP、Containerから実機への到達性、初期姿勢合わせ、安全監督と非常停止手段を確認した場合に限ります。`real`は箱庭Assetを起動せず、ROS側で`ros2 launch hakoniwa_dobot dobot.launch.py backend:=real robot_ip:=192.168.5.1`を使用します。`both`は手順2のlaunchを`backend:=both robot_ip:=192.168.5.1`に変更し、monitorは`/real/joint_states_robot`と`/hakoniwa/joint_states_robot`を別端末で観察します。IPは実機のものに置き換えます。どちらもWindows Dockerネットワークでの動作は未検証で、指令の配送・到達の一致は保証しません。**公式demoはreal／bothで実行禁止**、通常の`Stop`サービスは非常停止の代わりになりません。
