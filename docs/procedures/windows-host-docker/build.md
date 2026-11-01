# Windows host+Dockerビルド

[Windows host+Dockerセットアップ](setup.md)の完了後に実行します。Host側はPowerShell、Container内はBashを使用します。ROS 2 distributionは動作確認済みのJazzyを使用します。

| 端末 | 環境・実行ディレクトリ | 手順 |
| --- | --- | --- |
| Host PowerShell | `hakoniwa-business-pack`のrepository root | 1～2 |
| 新しいHost PowerShell（`docker-ros-bridge`を起動） | `hakoniwa-robot-arm`のrepository root | 3～4 |
| `docker-ros-bridge` | Container Bash、`/workspace/hakoniwa-robot-arm` | 5 |

`powershell`・`bash`ブロックはそれぞれの端末で実行するコマンドです。表示結果は各段階の成功条件を確認するために使います。

[実行手順の索引](../README.md) | [セットアップ](setup.md) | [ビルド](build.md) | [起動・動作確認](operation.md)

## 1. Host側のROS 2 TCP構成を生成する

`hakoniwa-business-pack`のrepository rootで`Get-Location`を確認してから実行します。

```powershell
Get-Location
```

`hakoniwa-business-pack`のrepository rootであることを確認してから実行します。

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

新しいPowerShellを`hakoniwa-robot-arm`のrepository rootで開き、`Get-Location`を確認してから実行します。Bash wrapperを介さずDocker CLIを直接使用します。

```powershell
Get-Location
```

`hakoniwa-robot-arm`のrepository rootであることを確認してから実行します。

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

同じHost PowerShellで、checkoutの親と生成済みTCP設定を絶対パスへ解決してContainerを起動します。この端末を以後`docker-ros-bridge`として使用します。

Host PowerShellで実行:

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

ContainerのBash promptが表示されるまで待ってください。このshellを終了するとContainerは削除されるため、動作確認が終わるまで開いたままにします。

## 5. ROS 2 Bridgeとサンプルをbuildする

promptが表示された`docker-ros-bridge`のContainer Bashで実行:

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
