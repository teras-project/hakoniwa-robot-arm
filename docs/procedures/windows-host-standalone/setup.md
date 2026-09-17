# Windows native箱庭単体セットアップ

Nova5 RuntimeとMuJoCo ViewerをWindows Host上でnative実行し、ROS 2を使わずに箱庭単体で動作確認するための準備手順です。PowerShellで実行します。

Windows共通の前提とvcpkgの準備は、hakoniwa-business-packの
[Getting Started「4.2 Windows 11（x64）」](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/docs/getting-started-ja.md#42-windows-11x64)
を正とします。この文書では、その手順をNova5用のRecipe IDと実行順へ具体化します。

## 1. Hostの前提を準備する

次を用意します。

- Git
- CPython 3.12（`python`で起動できること）
- Ruby 3.3（`ruby`で起動できること）
- CMake 3.27以上
- Visual Studio 2022の「C++によるデスクトップ開発」
- 自分でcloneしたvcpkg
- vcpkgの`boost-asio:x64-windows`、`boost-beast:x64-windows`、`glfw3:x64-windows`

Visual Studioに同梱されたProgram Files配下のvcpkgではなく、書き込み可能な場所へcloneしたvcpkgを使用します。以下は`C:\hakoniwa\vcpkg`へ準備済みの場合の例です。

```powershell
$vcpkgRoot = 'C:\hakoniwa\vcpkg'
& "$vcpkgRoot\vcpkg.exe" install `
  boost-asio:x64-windows `
  boost-beast:x64-windows `
  glfw3:x64-windows

python --version
ruby --version
cmake --version
git --version
```

BoostはEndpointとBridge、GLFWはMuJoCo Viewerのbuildに必要です。RubyはRecipe YAMLの読み込みに使用します。Python 3.12、Ruby 3.3、CMake、Gitのversionが表示され、vcpkgが正常終了すれば前提はOKです。

## 2. checkoutを準備する

同じ親ディレクトリへBusiness Packと本リポジトリをcloneします。以降のコマンド例では、両者の親を`C:\work\hakoniwa-robot-arm-workspace`とします。

```powershell
Set-Location C:\work\hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
Set-Location .\hakoniwa-business-pack
```

その他の依存リポジトリはRecipeが必要に応じて取得します。

## 3. vcpkgをFoundationへ登録する

以降は`hakoniwa-business-pack`のrepository rootで実行します。`recipe.py configure`より前に、Nova5 Recipe用のFoundation toolchainとしてvcpkgを保存します。

```powershell
$vcpkgRoot = 'C:\hakoniwa\vcpkg'

python tools\foundation.py toolchain `
  --recipe-id nova5-joint-trajectory-control `
  --vcpkg-root $vcpkgRoot

Get-Content .\work\foundation\config\toolchain.json
```

出力の`vcpkg_root`が指定した絶対パスなら登録完了です。この設定からEndpoint、Bridge、Nova5 RuntimeのCMakeへ`vcpkg.cmake`と`x64-windows` tripletが渡されます。親PowerShellの`VCPKG_ROOT`設定には依存しません。

## 4. FoundationとRuntime Recipeを準備する

PowerShellでは対話Bash profileを使用せず、Workspaceの非対話`run`操作を使用します。

```powershell
python tools\workspace.py run -- python tools\recipe.py plan `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml

python tools\workspace.py run -- python tools\recipe.py configure `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml

python tools\workspace.py doctor
python tools\workspace.py run -- python tools\recipe.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-joint-trajectory-control.yaml
```

Foundationと各依存が`SATISFIED`になればOKです。生成物は既定で`hakoniwa-business-pack\work\`以下へ配置されます。

## 5. Model Forge Recipeを準備する

```powershell
python tools\workspace.py run -- python tools\recipe.py configure `
  --recipe ..\hakoniwa-robot-arm\recipes\nova5\nova5-model-forge.yaml

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py forge

Test-Path .\work\model-forge\nova5\install\nova5.contact.xml
```

最後に`True`が表示されればMJCF生成は完了です。次は[Windows native箱庭単体ビルド](build.md)へ進みます。
