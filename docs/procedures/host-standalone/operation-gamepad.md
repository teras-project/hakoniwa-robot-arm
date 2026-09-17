# 箱庭単体・ゲームパッドの起動・操作

[箱庭単体・ゲームパッドビルド](build-gamepad.md)の完了が前提です。この構成ではROS 2や自動デモ軌道を使用せず、PS5コントローラー（DualSense）からNova5を操作します。

## 1. DualSenseと実行環境を確認する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | ゲームパッド用Launcher、build済みRuntime、Hostへ接続済みのDualSense |
| この作業のゴール | Foundation Pythonからゲームパッド依存を利用でき、Runtimeの前提が満たされている。 |

DualSenseをHostへ接続した状態で実行します。

```bash
python tools/recipe/nova5.py doctor
```

すべての行が`[OK]`で、次の行が表示されればOKです。

```text
[OK] Gamepad Python dependency: pygame is importable by ...
```

`doctor`はPython依存を検査します。接続したDualSenseの名前、軸数、ボタン数は次の`start`で検証されます。

## 2. ゲームパッド構成を起動する

```bash
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

次の状態を確認します。

- terminalに`Nova5 demo is running in the background.`が表示される。
- `status`が`RUNNING`を返す。
- MuJoCo ViewerにNova5が表示される。
- ゲームパッドのログに`pygame controller:`が記録される。

ログは`../work-host/recipes/nova5-joint-trajectory-control/logs/`にあります。起動に失敗した場合は、`nova5-gamepad-controller.out`と`nova5-gamepad-controller.err`を確認してください。

## 3. Nova5を操作する

`L1`はManual Enableです。`L1`を押している間だけスティック入力が関節目標へ反映されます。`L1`を離すと手動指令の更新を停止します。

| 操作 | 対象関節 |
| --- | --- |
| `L1`を押しながら右スティック左右 | `joint1` |
| `L1`を押しながら右スティック上下 | `joint2` |
| `L1 + R1`を押しながら右スティック上下 | `joint3` |
| `L1 + R1`を押しながら右スティック左右 | `joint4` |
| `L1 + △`を押しながら左スティック上下 | `joint5` |
| `L1 + △`を押しながら左スティック左右 | `joint6` |

`R1`と`△`を同時に押すと複数の操作バンクが選択されるため、同時には押さないでください。

`Options`を押すとゲームパッド入力プロセスが終了します。これはNova5 Runtime全体の停止操作ではありません。

## 4. 終了する

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`status`が`TERMINATED`を返せば停止完了です。
