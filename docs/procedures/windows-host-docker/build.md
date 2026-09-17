# Windows host+Dockerビルド

[Windows host+Dockerセットアップ](setup.md)の完了後に実行します。Host側はPowerShell、Container内はBashを使用します。ROS 2 distributionは動作確認済みのJazzyを使用します。

## 1. Host側のROS 2 TCP構成を生成する

`hakoniwa-business-pack`のrepository rootで実行します。

```powershell
$env:HAKONIWA_ROS2_TCP_HOST = 'host.docker.internal'

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py configure `
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

出力の`Mode`が`viewer`、`ROS 2 TCP`が`enabled`ならOKです。`host.docker.internal`はContainerからWindows Hostへ到達するためのDocker Desktopの名前です。

## 2. Host側Runtimeをbuild・検査する

同じPowerShellで実行します。

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py build

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\ros2_tcp.py doctor --robot nova5

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py doctor
```

doctorの全項目が`[OK]`ならHost側は完了です。

## 3. ROS 2 Jazzy imageを作成する

新しいPowerShellを開き、`hakoniwa-robot-arm`のrepository rootで実行します。Bash wrapperを介さずDocker CLIを直接使用します。

```powershell
docker build `
  --file .\docker\Dockerfile.jazzy `
  --tag hakoniwa-arm-dev:jazzy `
  .\docker

docker image inspect hakoniwa-arm-dev:jazzy `
  --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'
```

`hakoniwa-arm-dev:jazzy`と`linux/amd64`が表示されればOKです。

## 4. ROS 2 Containerを起動する

同じPowerShellで、checkoutの親と生成済みTCP設定を絶対パスへ解決してContainerを起動します。この端末を以後`docker-ros-bridge`として使用します。

```powershell
$workspaceRoot = (Resolve-Path ..).Path
$ros2TcpConfig = (Resolve-Path `
  ..\hakoniwa-business-pack\work\recipes\nova5-joint-trajectory-control\config\ros2-tcp).Path

docker run --rm -it `
  --name hakoniwa-arm-dev-jazzy `
  --network bridge `
  --volume "${workspaceRoot}:/workspace" `
  --volume "${ros2TcpConfig}:/ros2-tcp:ro" `
  --workdir /workspace/hakoniwa-business-pack `
  --env HAKONIWA_COMPOSER=/workspace/hakoniwa-business-pack `
  --env HAKONIWA_BUSINESS_PACK_ROOT=/workspace/hakoniwa-business-pack `
  --env ARM_PACK=/workspace/hakoniwa-robot-arm `
  --env HAKONIWA_WORK_DIR=/workspace/work-docker-jazzy `
  --env HAKONIWA_ROS2_WS=/workspace/ros2-work-jazzy `
  --env HAKONIWA_ROS2_TCP_CONFIG=/ros2-tcp `
  --env HAKONIWA_ROS_BINDING=/ros2-tcp/ros/binding.json `
  hakoniwa-arm-dev:jazzy bash
```

Containerのpromptが表示されればOKです。このshellを終了するとContainerは削除されるため、動作確認が終わるまで開いたままにします。

## 5. ROS 2 Bridgeとサンプルをbuildする

`docker-ros-bridge`のContainer shellで実行します。

```bash
cd /workspace/hakoniwa-robot-arm
/usr/bin/python3 tools/recipe/ros2_workspace.py build
source "$HAKONIWA_ROS2_WS/activate.bash"
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor

colcon --log-base "${HAKONIWA_ROS2_WS}-samples/log" build \
  --base-paths ros2_packages/hakoniwa_arm_samples \
  --build-base "${HAKONIWA_ROS2_WS}-samples/build" \
  --install-base "${HAKONIWA_ROS2_WS}-samples/install" \
  --symlink-install \
  --packages-select hakoniwa_arm_samples

source "${HAKONIWA_ROS2_WS}-samples/install/setup.bash"
ros2 pkg executables hakoniwa_arm_samples
```

ROS workspace doctorが成功し、最後に`hakoniwa_arm_samples control`と`hakoniwa_arm_samples monitor`が表示されればbuild完了です。次は[Windows host+Docker起動・動作確認](operation.md)へ進んでください。
