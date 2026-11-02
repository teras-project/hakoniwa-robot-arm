# Excavator Windows native箱庭単体の起動・動作確認

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Windows Host PowerShell |
| 実行ディレクトリ | `hakoniwa-business-pack`ルート |
| この作業の入力成果物 | doctor済みheadless Excavator Runtime |
| この作業のゴール | smoke完了後にLauncher sessionを停止する。 |

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py smoke
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py stop
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py status
```

smokeが次の5行をすべて表示し、stop後のstatusが`TERMINATED`なら成功です。`[NG]`または`error:`が表示された場合はNGです。

```text
[OK] MathScavator9000 Excavator accepted the Launcher-managed command input.
[OK] MathScavator9000 Excavator completed the Launcher-managed Twist sequence.
[OK] MathScavator9000 Excavator applied non-zero crawler wheel controls.
[OK] MathScavator9000 Excavator moved without chassis jump or tip-over.
[OK] No MuJoCo numerical-instability marker was observed for MathScavator9000 Excavator during the smoke window.
```

## 任意: Viewer run（未確認）

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py start
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py status
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py stop
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py status
```

起動後`RUNNING`、停止後`TERMINATED`がLifecycleの成功条件です。Viewer表示は未確認です。
