# Excavator Windows native箱庭単体ビルド

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Windows Host PowerShell |
| 実行ディレクトリ | `hakoniwa-business-pack`ルート |
| この作業の入力成果物 | [セットアップ](setup.md)済みRecipeとMJCF |
| この作業のゴール | headless Excavator exeを生成しdoctorを通す。 |

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py configure --headless
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py build --headless
Test-Path .\work\recipes\excavator-joint-trajectory-control\build\bin\robot-excavator-hakoniwa-asset.exe
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py doctor
```

`Mode            : headless`、`True`が表示され、doctorにNGがなければ成功です。

## 任意: Viewer build（未確認）

```powershell
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py configure
python tools\workspace.py run -- python `
  ..\hakoniwa-robot-arm\tools\recipe\excavator.py build
```
