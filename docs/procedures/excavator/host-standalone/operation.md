# Excavator 箱庭単体の起動・動作確認

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`ルート |
| この作業の入力成果物 | doctor済みheadless Runtime |
| この作業のゴール | 自動smokeを完了し、Launcher sessionを停止する。 |

```bash
python tools/recipe/excavator.py smoke
python tools/recipe/excavator.py stop
python tools/recipe/excavator.py status
```

次の実出力がすべて出て、最後のstatusが`TERMINATED`なら成功です。

```text
[OK] MathScavator9000 Excavator accepted the Launcher-managed command input.
[OK] MathScavator9000 Excavator completed the Launcher-managed Twist sequence.
[OK] MathScavator9000 Excavator applied non-zero crawler wheel controls.
[OK] MathScavator9000 Excavator moved without chassis jump or tip-over.
[OK] No MuJoCo numerical-instability marker was observed for MathScavator9000 Excavator during the smoke window.
```

いずれかの`[OK]`欠落、`simulation is unstable`、`nan, inf or huge value`、停止後の`RUNNING`はNGです。

## 任意: Viewer run（未確認）

Viewer構成をbuildした後に実行します。

```bash
python tools/recipe/excavator.py start
python tools/recipe/excavator.py status
python tools/recipe/excavator.py stop
python tools/recipe/excavator.py status
```

起動後が`RUNNING`、停止後が`TERMINATED`ならLifecycleは成功です。Viewer表示と動作は未確認です。
