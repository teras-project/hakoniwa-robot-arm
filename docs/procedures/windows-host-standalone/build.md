# Windows native箱庭単体ビルド

[Windows native箱庭単体セットアップ](setup.md)の完了後、PowerShellで実行します。実行ディレクトリは`hakoniwa-business-pack`のrepository rootです。

端末: Windows HostのPowerShell（`hakoniwa-business-pack`のrepository root）。`powershell`ブロックは実行コマンドです。表示結果は確認用で、コマンドとしてコピーしません。

[実行手順の索引](../README.md) | [セットアップ](setup.md) | [ビルド](build.md) | [起動・動作確認](operation.md)

## 1. Launcherと環境付きモデルを生成する

実行するコマンド（Windows Host PowerShell、作業ディレクトリの確認）:

```powershell
Get-Location
```

`hakoniwa-business-pack`のrepository rootであることを確認してから実行します。

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py configure `
  --environment --realtime-sync-cycle-msec 50
```

出力の`Mode`が`viewer`、`ROS 2 TCP`が`disabled`なら箱庭単体用の構成です。

## 2. Viewer付きRuntimeをbuildする

実行するコマンド（Windows Host PowerShell、`hakoniwa-business-pack`のrepository root）:

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py build

Test-Path .\work\recipes\nova5-joint-trajectory-control\build\bin\robot-arm-hakoniwa-asset.exe
```

初回buildではMuJoCo 3.16.0のWindows packageを取得します。最後に`True`が表示されればOKです。

## 3. 起動前検査を行う

実行するコマンド（Windows Host PowerShell、`hakoniwa-business-pack`のrepository root）:

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py doctor
```

全項目が`[OK]`なら[Windows native箱庭単体の起動・動作確認](operation.md)へ進みます。
