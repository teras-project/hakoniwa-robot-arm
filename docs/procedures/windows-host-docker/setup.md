# Windows host+Dockerセットアップ

Nova5 RuntimeとMuJoCo ViewerをWindows 11 Host上でnative実行し、Dobot 公式 ROS 2サービスとJointState BridgeをDocker Desktop上で実行する準備手順です。Host側はPowerShell、Container内はBashで操作します。実機を使わず、箱庭で公式デモを確認します。**以下のWindows Dobot Native Asset / PDU-RPC手順は未検証**です。失敗した段階で止め、成功済みとして扱わないでください。

端末: 手順1はWindows nativeセットアップに従い、手順2～3はWindows HostのPowerShell（`hakoniwa-business-pack`のrepository root）を使用します。ContainerのBashは[ビルド](build.md)から使用します。`powershell`ブロックは実行コマンド、表示結果は手順の成功条件を確認するためのものです。

[実行手順の索引](../README.md) | [セットアップ](setup.md) | [ビルド](build.md) | [起動・動作確認](operation.md)

## 1. Windows native環境を準備する

[Windows native箱庭単体セットアップ](../windows-host-standalone/setup.md)の手順1から5までを完了してください。同じ手順で、次が準備されます。

- CPython 3.12、Ruby 3.3、CMake、Visual Studio 2022
- 書き込み可能な場所へcloneしたvcpkgと必要なpackage
- 同じ親ディレクトリにある`hakoniwa-business-pack`と`hakoniwa-robot-arm`
- Foundation toolchainとNova5のMJCF

Native PDU-RPCのビルドにはWindows Foundation prefixにインストールされたEndpoint CMake package、MSVC x64のCMakeツールチェーン、Gitが必要です。Docker内で生成するDobot型・service設定はWindows Hostから読める共有`work`へ置きます。公式Dobot checkoutとパッケージ、PDU-RPC/registry checkoutは[ビルド](build.md)で準備します。`dobot_demo/demo.py`は変更しません。

以降の例では、両repositoryの親を`C:\work\hakoniwa-robot-arm-workspace`、Business Packのworkを`hakoniwa-business-pack\work`とします。

## 2. Docker Desktopを準備する

Docker DesktopをLinux container modeで起動し、PowerShellで確認します。

```powershell
docker version
docker info --format '{{.OSType}}/{{.Architecture}}'
```

ClientとServerのversion、および`linux/amd64`が表示されればOKです。Serverへ接続できない場合は、Docker Desktopの起動完了を待って再実行します。

Docker Desktopでcheckoutの親ディレクトリのfile sharingを許可してください。ContainerからHostへの接続名は`host.docker.internal`です。TCP 54001（状態Bridge）と54020（Dobot PDU-RPC）を使用するため、Windows Defender Firewallは組織のポリシーに従い必要なPrivate networkだけを許可し、Public network全体を安易に許可しないでください。

## 3. FoundationとRecipeを検査する

`hakoniwa-business-pack`のrepository rootで実行します。

```powershell
Get-Location
```

`hakoniwa-business-pack`のrepository rootであることを確認してから実行します。

```powershell
python tools\workspace.py doctor

python tools\workspace.py run -- python tools\recipe.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml

python tools\workspace.py run -- python tools\foundation.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml
```

Workspace doctorに`[NG]`がなく、RecipeとFoundationが`SATISFIED`ならOKです。Nova5 RecipeはWindowsのcallback-backed Endpoint向けに、共有callback assets runtimeと、Core本体を1つの`hako.dll`にする構成を明示要求します。Core本体をstaticのまま共有callback assetsだけを使うと、Core本体の写しがDLLごとにでき、buildが重複定義で失敗します。この構成はこのRecipeにだけ適用され、Linux/macOSでは無視されます。

生成済みreceiptでも選択結果を確認できます。

```powershell
Select-String `
  -Path .\work\foundation\install\share\hakoniwa\receipts\hakoniwa-core-pro.yaml `
  -Pattern 'callback_assets_shared: true', 'core_shared: true'
```

2行とも表示されればHost TCP Bridgeに必要なCore構成です。表示されない場合は、最新のBusiness Pack、Robot Arm、Coreを取得してRecipeを再configureしてください。

次は[Windows host+Dockerビルド](build.md)へ進んでください。Windows native Dobotビルド・結合はまだ検証していません。
