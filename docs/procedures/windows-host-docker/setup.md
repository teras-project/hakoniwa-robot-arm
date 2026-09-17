# Windows host+Dockerセットアップ

Nova5 RuntimeとMuJoCo ViewerをWindows 11 Host上でnative実行し、ROS 2 Jazzy Bridge、monitor、controlをDocker Desktop上で実行するための準備手順です。Host側はPowerShell、Container内はBashで操作します。

## 1. Windows native環境を準備する

[Windows native箱庭単体セットアップ](../windows-host-standalone/setup.md)の手順1から5までを完了してください。同じ手順で、次が準備されます。

- CPython 3.12、Ruby 3.3、CMake、Visual Studio 2022
- 書き込み可能な場所へcloneしたvcpkgと必要なpackage
- 同じ親ディレクトリにある`hakoniwa-business-pack`と`hakoniwa-robot-arm`
- Foundation toolchainとNova5のMJCF

以降の例では、両repositoryの親を`C:\work\hakoniwa-robot-arm-workspace`、Business Packのworkを`hakoniwa-business-pack\work`とします。

## 2. Docker Desktopを準備する

Docker DesktopをLinux container modeで起動し、PowerShellで確認します。

```powershell
docker version
docker info --format '{{.OSType}}/{{.Architecture}}'
```

ClientとServerのversion、および`linux/amd64`が表示されればOKです。Serverへ接続できない場合は、Docker Desktopの起動完了を待って再実行します。

## 3. FoundationとRecipeを検査する

`hakoniwa-business-pack`のrepository rootで実行します。

```powershell
python tools\workspace.py doctor

python tools\workspace.py run -- python tools\recipe.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml

python tools\workspace.py run -- python tools\foundation.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml
```

Workspace doctorに`[NG]`がなく、RecipeとFoundationが`SATISFIED`ならOKです。Nova5 RecipeはWindowsのcallback-backed Endpoint向けに共有callback assets runtimeを明示要求します。通常のCore buildは従来どおりstaticのままで、このRecipeにだけ実験的な構成が適用されます。

生成済みreceiptでも選択結果を確認できます。

```powershell
Select-String `
  -Path .\work\foundation\install\share\hakoniwa\receipts\hakoniwa-core-pro.yaml `
  -Pattern 'callback_assets_shared: true'
```

該当行が表示されればHost TCP Bridgeに必要なCore構成です。表示されない場合は、最新のBusiness Pack、Robot Arm、Coreを取得してRecipeを再configureしてください。

次は[Windows host+Dockerビルド](build.md)へ進んでください。
