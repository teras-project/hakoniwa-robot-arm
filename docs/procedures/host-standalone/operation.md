# 箱庭単体の起動・動作確認

[箱庭単体ビルド](build.md)の完了が前提です。この構成ではROS 2を使用せず、箱庭Runtime、PDU、MuJoCo Viewer、自動デモ軌道を確認します。

## 1. 箱庭単体デモを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 単体デモ用`launcher.json`、build済み`robot-arm-hakoniwa-asset`、Forge済み`nova5.contact.xml` |
| この作業のゴール | Runtime、PDU、MuJoCo Viewer、自動デモ軌道が一連で動作する。 |

この構成では`start`直後に自動デモ軌道が送信され、Nova5が動きます。これはROS 2制御ではなく、箱庭シミュレーション単体の動作確認です。

```bash
python tools/recipe/nova5.py doctor
```

すべての行が`[OK]`なら起動します。`[NG]`が一つでもあれば起動しません。

```bash
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

次の状態を確認します。

- terminalに`Nova5 demo is running in the background.`が表示される。
- `status`が`RUNNING`を返す。
- MuJoCo Viewer上でNova5が自動軌道を動く。

一つでも満たさなければNGです。

## 2. 終了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 動作確認済みで`RUNNING`のNova5 Runtime |
| この作業のゴール | Nova5 Runtimeが停止し、状態が`TERMINATED`になる。 |

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py status
```

`status`が`TERMINATED`を返せば停止完了です。
