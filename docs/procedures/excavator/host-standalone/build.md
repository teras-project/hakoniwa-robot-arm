# Excavator 箱庭単体ビルド

[セットアップ](setup.md)の続きとして、headless Runtimeをbuildします。

`host-hako`端末を閉じた場合は、通常のHost terminalで`hakoniwa-robot-arm`ルートへ移動し、`source ../work-host/profiles/activate-host-hako.bash`で開き直してから`cd ../hakoniwa-robot-arm`で戻ります。

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`ルート |
| この作業の入力成果物 | Forge済みMJCFとRuntime Recipe |
| この作業のゴール | headless実行ファイルとLauncherを生成し、doctorを通す。 |

```bash
python tools/recipe/excavator.py configure --headless
python tools/recipe/excavator.py build --headless
python tools/recipe/excavator.py doctor
```

`Mode            : headless`が表示され、doctorに`[NG]`、`MISSING`、`error:`がなければ成功です。build errorまたはdoctorのNGは次へ進めない条件です。[起動・動作確認](operation.md)へ進みます。

## 任意: Viewer build（未確認）

```bash
python tools/recipe/excavator.py configure
python tools/recipe/excavator.py build
python tools/recipe/excavator.py doctor
```

この経路は未確認です。`Mode            : viewer`とdoctor成功を確認してください。
