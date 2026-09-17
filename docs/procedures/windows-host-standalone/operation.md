# Windows native箱庭単体の起動・動作確認

[Windows native箱庭単体ビルド](build.md)の完了後、PowerShellで実行します。実行ディレクトリは`hakoniwa-business-pack`のrepository rootです。

## 1. Nova5とMuJoCo Viewerを起動する

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py start

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
```

次を確認します。

- `Nova5 demo is running in the background.`と表示される。
- `status`が`RUNNING`を返す。
- MuJoCo Viewerが開く。
- 自動送信される約9.5秒の5点軌道でNova5が動き、最後に初期姿勢へ戻る。

Viewerでは`p`でpause/resume、`r`でreset、`h`でhelpを表示できます。Launcher管理下で終了するため、通常はViewerだけを閉じず、次のstop操作を使用します。

ログは次にあります。

```text
work\recipes\nova5-joint-trajectory-control\logs\
work\recipes\nova5-joint-trajectory-control\runtime\launcher-session.json.log
```

`nova5-trajectory-sender.out`に`Successfully sent JointTrajectory PDU.`があり、`nova5-plant.out`と`nova5-plant.err`に`simulation is unstable`や`nan, inf or huge value`がなければ正常です。

## 2. 終了する

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py stop

python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\nova5.py status
```

`status`が`TERMINATED`を返せば停止完了です。Launcher sessionに記録されたプロセスだけを停止し、PythonやViewerプロセスを一括終了しないでください。
