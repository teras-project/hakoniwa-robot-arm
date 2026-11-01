# 箱庭単体・ゲームパッドビルド

[箱庭単体・ゲームパッドセットアップ](setup-gamepad.md)の完了後に実行します。この手順では、自動デモ軌道の代わりにPS5コントローラー（DualSense）入力を使用するLauncherを生成します。

手順: [一覧](../README.md) → [ゲームパッドセットアップ](setup-gamepad.md) → **ビルド** → [起動・操作](operation-gamepad.md)

すべてのコマンドを`host-hako`のRobot Arm repository rootで実行し、Foundationの`python`を使用します。

## 1. ゲームパッド用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | Forge済みのNova5 MJCF、Hostへ接続済みのDualSense |
| この作業のゴール | ゲームパッド入力を含むLauncherとHost OS用DualSenseプロファイルが`../work-host`へ生成される。 |

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py configure \
  --environment \
  --gamepad \
  --realtime-sync-cycle-msec 50
```

初回はFoundation Pythonへ`pygame==2.6.1`を導入します。`[OK] Gamepad Python dependency: pygame==2.6.1`が表示されたら依存関係の準備は完了です。続けて`ROS 2 TCP: disabled`、`Gamepad: enabled`、Host OSに対応するprofile pathが表示されることを確認してください。

macOSでは`macos-pygame.json`、native Ubuntuでは`ubuntu-pygame.json`が選択されます。`Gamepad`が`enabled`で、Host OSに対応するプロファイルが表示されればOKです。`error:`または`[NG]`で終了した場合はNGです。

このconfigureは自動デモ用Launcherをゲームパッド用Launcherで置き換えます。自動デモへ戻す場合は、[箱庭単体ビルド](build.md)のconfigureを再実行してください。

## 2. Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | ゲームパッド用`launcher.json`とForge済みのNova5 MJCF |
| この作業のゴール | MuJoCo Viewer上でNova5を動かす`robot-arm-hakoniwa-asset`が生成される。 |

実行するコマンド（`host-hako`）:
```bash
python tools/recipe/nova5.py build
ls -l ../work-host/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
```

最後の`ls`で`robot-arm-hakoniwa-asset`が表示されればOK、`No such file or directory`ならNGです。

次は[箱庭単体・ゲームパッドの起動・操作](operation-gamepad.md)へ進みます。
