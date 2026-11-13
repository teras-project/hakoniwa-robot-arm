# Windows host+Docker：Dobot 仮想サービスの起動・動作確認

[ビルド](build.md)のWindows Native PDU-RPC／専用Asset、Container内の公式ROSメッセージ・PDU型・service/topic binding、Launcherの切り替えが**すべて成功した場合のみ**実行します。**Windows Host + DockerのDobot結合は未検証です。** ROS launch は既定で箱庭だけに接続します。この手順では実機に接続しません。

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
ros2 launch hakoniwa_dobot dobot.launch.py \
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

別のHost PowerShellから手順3と同じ`docker exec -it ... /ros_entrypoint.sh bash`で`docker-ros-control`を開きます。`hakoniwa_arm_samples control` と公式 `dobot_demo demo` は同じ `/dobot_bringup_ros2/srv/*` を呼び、箱庭専用の宛先には固定されていません。dry-run の `GetAngle` も実機の同名サービスに届く可能性があり、`--execute` は実機を動かし得ます。**この箱庭手順では実機 driver を停止するか別の ROS domain に分離し、同名サービスの競合がないことを確認してから** Container Bash で実行します。[安全上の警告](../ros2/arm-operations.md)も参照してください。

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

`GetAngle`の応答とdry-runの現在角・J1 +3°目標を点検します。**同じ ROS domain に同名サービスを出す実機 driver がいないことを再確認**してから、小動作を明示的に実行します。

```bash
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
```

`control`は`EnableRobot`、`SpeedFactor=10%`、`MovJ`を使用します。応答`res=0`は受理であって到達ではありません。monitorの値とViewerの動きを確認してください。次に箱庭だけで公式デモを実行します。J1 50°／J2 -8°への絶対角移動を含むため、[安全上の警告と仮想MovL／DOの制限](../ros2/arm-operations.md)を読んでから実行してください。**実機に公式デモを送らないでください。**

実行するコマンド（`docker-ros-control`）:
```bash
ros2 run dobot_demo demo
```

monitor で連続する移動を確認します。

## 5. 停止

`docker-ros-control` 端末で次のコマンドを実行します。

実行するコマンド（`docker-ros-control`）:
```bash
ros2 service call /dobot_bringup_ros2/srv/DisableRobot dobot_msgs_v4/srv/DisableRobot '{}'
```

monitorとlaunchをCtrl+Cで止めてからHost PowerShell（Business Packルート）で実行します。

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
| Host TCP Bridgeが`0xc0000005`で終了する | 古いFoundation成果物が残っている可能性がある。最新revisionを取得してRecipeを再configureし、Core receiptの`callback_assets_shared: true`と`core_shared: true`を確認してから再buildする。 |
| `ros2 topic info`にtopicがない | Host TCP Bridge、Container側ROS 2 Bridgeの順で起動しているか、`HAKONIWA_ROS_BINDING`が`/ros2-tcp/ros/binding.json`を指しているか確認する。 |

調査時は、Hostの`work\recipes\nova5-joint-trajectory-control\logs\`と、各ROS 2端末の標準出力をセットで確認してください。
