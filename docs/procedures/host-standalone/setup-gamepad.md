# 箱庭単体・ゲームパッドセットアップ

Nova5 RuntimeとMuJoCo ViewerをHost上で実行し、PS5コントローラー（DualSense）から操作するための準備手順です。ROS 2は使用しません。

手順: [一覧](../README.md) → **ゲームパッドセットアップ** → [ビルド](build-gamepad.md) → [起動・操作](operation-gamepad.md)

通常のHost terminalで前提パッケージを準備し、[箱庭単体セットアップ](setup.md)に従って開く`host-hako`でForgeとRuntimeを操作します。Foundationの初期化にはCPython 3.12、構築後はFoundationの`python`を使用します。

## 検証状況

| Host環境 | 状態 |
| --- | --- |
| macOS（Apple Silicon） | 動作確認済み |
| Ubuntu 24.04 native | 対応プロファイル実装済み、実機動作は未確認 |
| WSL / Windows native | 未対応 |

`対応プロファイル実装済み`は実行可能性を示すものであり、実機での検証完了を意味しません。

## 1. Hostの前提と箱庭単体の基本セットアップを完了する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 同じ親ディレクトリへclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm` |
| この作業のゴール | Forge済みのNova5 MJCFが`../work-host/model-forge/nova5/install/nova5.contact.xml`に存在する。 |

Ubuntu／macOSとも[箱庭単体セットアップ](setup.md)の手順1から5までを実行します。手順1ではHost OSに対応する前提コマンドだけを選んでください。

`host-hako`のRobot Arm repository rootで、次のファイルが存在することを確認してください。

実行する確認コマンド（`host-hako`）:
```bash
ls -l ../work-host/model-forge/nova5/install/nova5.contact.xml
```

`nova5.contact.xml`が表示されればOK、`No such file or directory`ならNGです。

## 2. DualSenseをHostへ接続する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | Host OS |
| 実行ディレクトリ | なし |
| この作業の入力成果物 | PS5コントローラー（DualSense） |
| この作業のゴール | DualSenseがHost OSの入力デバイスとして認識される。 |

USBまたはBluetoothでDualSenseをHostへ接続し、Host OSの入力デバイス一覧に表示されることを確認します。最初の切り分けではUSB接続を推奨します。

ゲームパッド入力にはFoundation Python上の`pygame`を使用します。`pygame`は次のビルド手順で`configure --gamepad`を実行した際に、Foundation Pythonへ自動的に準備されます。system Pythonへ手動でインストールする必要はありません。

次は[箱庭単体・ゲームパッドビルド](build-gamepad.md)へ進みます。
