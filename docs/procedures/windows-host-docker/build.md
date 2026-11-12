# Windows host+Docker：Dobot 仮想サービスのビルド

[セットアップ](setup.md)でWindows native Foundation／Nova5 MJCFとDocker Desktopを準備してから実行します。**ROS launch の既定は箱庭**です。Windows HostはPowerShell、ROS 2 Jazzy ContainerはBashです。WindowsでのNative PDU-RPC／専用AssetのCMakeビルドと結合は**未検証の手順**です。各段階の確認に失敗したら先へ進まず、旧topic経路を代わりに起動しないでください。

| 端末 | 作業ディレクトリ | 役割 |
| --- | --- | --- |
| Host PowerShell | `hakoniwa-business-pack`ルート | Host Launcher／Runtimeの構築 |
| 新しいHost PowerShell | `hakoniwa-robot-arm`ルート | Docker起動。開いたまま維持 |
| `docker-ros-bridge` | Containerの`/workspace/hakoniwa-robot-arm` | 公式Dobot ROS／PDU型／bindingの構築 |
| 別のHost PowerShell | `hakoniwa-robot-arm`ルート | Windows native RPC／専用Assetの構築 |

[実行手順の索引](../README.md) | [セットアップ](setup.md) | [起動・動作確認](operation.md)

## 1. Windows HostでLauncherと基礎Runtimeを構築

`hakoniwa-business-pack`ルートのPowerShellで実行します。`host.docker.internal`はContainerからWindows HostのTCP Bridgeに到達するための名前です。

```powershell
Get-Location
$env:HAKONIWA_ROS2_TCP_HOST = 'host.docker.internal'
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py configure `
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py build
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\ros2_tcp.py doctor --robot nova5
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py doctor
```

`Get-Location`がBusiness Packルート、`ROS 2 TCP`が`enabled`、doctorがすべて`[OK]`であることを確認します。現段階の基礎AssetはまだDobotサービスを処理しません。

## 2. Docker imageと共有mountを用意

別のPowerShellで`hakoniwa-robot-arm`ルートを開きます。checkout親（例`C:\work\hakoniwa-robot-arm-workspace`）を`/workspace`に、HostのROS TCP設定を`/ros2-tcp:ro`にmountします。Containerの`/workspace/hakoniwa-business-pack/work`はHostの`hakoniwa-business-pack\work`と**同じ共有ディレクトリ**です。Windows HostへLinuxの実行ファイルを移すことはしません。

```powershell
Get-Location
docker build --file .\docker\Dockerfile.jazzy `
  --tag hakoniwa-arm-dev:jazzy .\docker
docker image inspect hakoniwa-arm-dev:jazzy `
  --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'

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
  --env HAKONIWA_ROS2_WS=/workspace/hakoniwa-business-pack/work/ros2 `
  --env HAKONIWA_ROS2_TCP_CONFIG=/ros2-tcp `
  --env HAKONIWA_ROS_BINDING=/ros2-tcp/ros/binding.json `
  hakoniwa-arm-dev:jazzy bash
```

imageが`linux/amd64`で、ContainerのBash promptが表示されることを確認します。このPowerShellとContainerを最後まで開いたままにします。mountに失敗した場合はDocker Desktopのfile sharingを確認します。

## 3. Containerで公式メッセージ、PDU-RPC／型、bindingを生成

まず `docker-ros-bridge`（Container Bash）で次の設定を行います。

```bash
cd /workspace/hakoniwa-robot-arm
source /opt/ros/jazzy/setup.bash
export DOBOT_WORK=/workspace/hakoniwa-business-pack/work
export ROS_DISTRO=jazzy
export DOBOT_RPC_ADDRESS=host.docker.internal
```

次に、**同じ `docker-ros-bridge` 端末で**[Dobot共通ビルド手順の**1 → 2 のみ**](../ros2/dobot-build.md)を順に実行します。共通手順3はWindows Nativeには適用せず、以下の手順4・5でWindows HostのRPCとAssetをビルドします。実機 driver はビルドしません。

共通手順の最後に`ros2 pkg executables dobot_demo`で`dobot_demo demo`、`ros2 pkg executables hakoniwa_dobot`で`hakoniwa_dobot configure`が見え、`$DOBOT_WORK/dobot-types/pdu/offset`と`$DOBOT_WORK/dobot-services/rpc/endpoints/dobot_virtual.json`が生成されたことを確認します。公式checkoutとregistryを変更しません。生成されたRPC endpoint JSONの参照は相対パスなので、Hostでは同じ共有`work`をWindowsパスで指定します。

## 4. Windows HostでNative PDU-RPCをインストール

新しいHost PowerShellを`hakoniwa-robot-arm`ルートで開きます。手順3が取得した`hakoniwa-pdu-rpc`と`hakoniwa-pdu-registry`はRobot Armの兄弟checkoutです。Windows Foundation Endpoint **CMake package** が存在しなければここで停止します（そのFoundationではNative RPCをビルドできません）。Visual Studio 2022 x64でRPCをビルド・インストールします。Containerの`/workspace/...`パスをHostのCMakeへ渡してはいけません。

```powershell
$dobotWork = (Resolve-Path ..\hakoniwa-business-pack\work).Path
$foundation = Join-Path $dobotWork 'foundation\install'
$registry = (Resolve-Path ..\hakoniwa-pdu-registry).Path
if (-not (Test-Path (Join-Path $foundation 'lib\cmake\hakoniwa_pdu_endpoint'))) {
  throw 'Windows Foundation Endpoint CMake package not found; stop here'
}
if (-not (Test-Path (Join-Path $dobotWork 'dobot-types\pdu\offset'))) {
  throw 'Dobot PDU types missing; finish Container build first'
}
cmake -S ..\hakoniwa-pdu-rpc -B "$dobotWork\dobot-rpc-build" `
  -G "Visual Studio 17 2022" -A x64 `
  "-DHAKO_PDU_ENDPOINT_PREFIX=$foundation" `
  "-DHAKONIWA_PDU_REGISTRY_DIR=$registry" `
  "-DCMAKE_INSTALL_PREFIX=$dobotWork\dobot-rpc-native" `
  -DCMAKE_INSTALL_LIBDIR=lib `
  -DHAKO_PDU_RPC_BUILD_TESTS=OFF -DHAKO_PDU_RPC_BUILD_EXAMPLES=OFF
cmake --build "$dobotWork\dobot-rpc-build" --config Release --parallel 2
cmake --install "$dobotWork\dobot-rpc-build" --config Release
Test-Path "$dobotWork\dobot-rpc-native\lib\cmake\hakoniwa_pdu_rpc\hakoniwa_pdu_rpcConfig.cmake"
```

最後が`True`でなければ停止します。GeneratorやFoundation Endpointが非互換なら先へ進まないでください。

## 5. Windows Dobot AssetをビルドしLauncherを適用

同じHost PowerShell（Robot Armルート）です。基礎RuntimeのCMake cacheにあるFoundation／Runtime／MuJoCoの設定を引き継いで専用Assetをビルドします。Windowsでは依存DLLが必要です。`robot-arm-dobot-asset`のWindows post-build DLL copyが有効な版を使い、生成されたexeの隣に必要なDLLが存在することを確認します。

```powershell
$buildDir = Join-Path $dobotWork 'recipes\nova5-joint-trajectory-control\build'
cmake -S . -B "$buildDir" `
  -DHAKO_ARM_ENABLE_DOBOT=ON `
  "-DHAKO_DOBOT_PDU_DIR=$dobotWork\dobot-types" `
  "-Dhakoniwa_pdu_rpc_DIR=$dobotWork\dobot-rpc-native\lib\cmake\hakoniwa_pdu_rpc"
cmake --build "$buildDir" --target robot-arm-dobot-asset --config Release --parallel 2
```

ビルドが失敗したらここで停止し、Launcher は変更しません。実行ファイルとDLLを確認します。

```powershell
$binary = @("$buildDir\bin\robot-arm-dobot-asset.exe",
            "$buildDir\bin\Release\robot-arm-dobot-asset.exe") |
  Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $binary) { throw 'robot-arm-dobot-asset.exe not found; stop here' }
$binary = (Resolve-Path $binary).Path
Get-ChildItem (Split-Path $binary) -Filter '*.dll'
```

確認できた場合のみ、同じPowerShellでLauncherを切り替えます。

```powershell
python tools\dobot\adapt_launcher.py `
  --launcher "$dobotWork\recipes\nova5-joint-trajectory-control\config\launcher.json" `
  --binary "$binary" `
  --services "$dobotWork\dobot-services\rpc\rpc-server-services.json" `
  --endpoint "$dobotWork\dobot-services\rpc\endpoints\dobot_virtual.json"
Test-Path "$dobotWork\recipes\nova5-joint-trajectory-control\config\launcher.pre-dobot.json"
```

最後が`True`で、exeの隣に必要なEndpoint等のDLLが揃っていることを確認します。`adapt_launcher.py`はWindowsパスをLauncherへ書き込みます。`nova5.py configure`を再実行した場合は**停止してから**再度Launcherを適用します。成功した場合のみ[起動・動作確認](operation.md)へ進んでください。
