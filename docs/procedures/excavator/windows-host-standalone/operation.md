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

host手順に列挙した5つの`[OK]`と`TERMINATED`が成功条件です。Windows nativeの実行は未確認です。

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
