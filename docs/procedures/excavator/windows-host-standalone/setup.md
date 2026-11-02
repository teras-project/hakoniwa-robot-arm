# Excavator Windows native箱庭単体セットアップ

Windows HostのPowerShellで実行します。Windows共通前提はBusiness Packの[Getting Started「4.2 Windows 11（x64）」](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/docs/getting-started-ja.md#42-windows-11x64)を正とします。

[手順一覧](../../README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)

## 1. checkoutとvcpkg

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Windows Host PowerShell |
| 実行ディレクトリ | `C:\work\hakoniwa-robot-arm-workspace` |
| この作業の入力成果物 | Python 3.12、Ruby 3.3、CMake、VS 2022、Git、書込可能なvcpkg |
| この作業のゴール | 2リポジトリをcloneし、Excavator Foundationへvcpkgを登録する。 |

Nova5手順と同じ例`C:\hakoniwa\vcpkg`を使います。

```powershell
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
cd .\hakoniwa-business-pack
$vcpkgRoot = 'C:\hakoniwa\vcpkg'
& "$vcpkgRoot\vcpkg.exe" install `
  boost-asio:x64-windows `
  boost-beast:x64-windows `
  glfw3:x64-windows
python tools\foundation.py toolchain `
  --recipe-id excavator-joint-trajectory-control `
  --vcpkg-root $vcpkgRoot
Get-Content .\work\foundation\config\toolchain.json
```

`vcpkg_root`が指定した絶対パスなら成功です。vcpkg installまたはtoolchain登録の失敗はNGです。

## 2. Foundation、Runtime、Forge

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Windows Host PowerShell |
| 実行ディレクトリ | `hakoniwa-business-pack`ルート |
| この作業の入力成果物 | cloneとtoolchain設定 |
| この作業のゴール | 両Recipe、bucket-proxy venv、Excavator MJCFを準備する。 |

```powershell
python tools\workspace.py run -- python tools\recipe.py plan `
  --recipe ..\hakoniwa-robot-arm\recipes\excavator\excavator-joint-trajectory-control.yaml
python tools\workspace.py run -- python tools\recipe.py configure `
  --recipe ..\hakoniwa-robot-arm\recipes\excavator\excavator-joint-trajectory-control.yaml
python tools\workspace.py doctor
python tools\workspace.py run -- python tools\recipe.py doctor `
  --recipe ..\hakoniwa-robot-arm\recipes\excavator\excavator-joint-trajectory-control.yaml
python tools\workspace.py run -- python tools\recipe.py configure `
  --recipe ..\hakoniwa-robot-arm\recipes\excavator\excavator-model-forge.yaml
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\install_excavator_bucket_proxy_tools.py
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py forge
Test-Path .\work\model-forge\excavator\install\excavator.mobile.xml
```

doctorにNGがなく、`Excavator forge complete.`と最後に`True`が表示されれば成功です。
