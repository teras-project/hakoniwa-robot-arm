# 箱庭単体ビルド

[箱庭単体セットアップ](setup.md)でNova5 MJCFを生成してから実行します。この手順ではROS 2連携を構成しません。

PS5コントローラー（DualSense）で操作する場合は、このページの代わりに[箱庭単体・ゲームパッドビルド](build-gamepad.md)を使用してください。

## 1. 箱庭単体用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | `../work-host/model-forge/nova5/install/nova5.contact.xml` |
| この作業のゴール | ROS 2を使用しないLauncherと`host-hako` profileが`../work-host`へ生成される。 |

```bash
cd ../hakoniwa-robot-arm
python tools/recipe/nova5.py configure \
  --environment --realtime-sync-cycle-msec 50
```

正常時は末尾に次の形式で表示されます。

```text
Launcher        : /.../work-host/recipes/nova5-joint-trajectory-control/config/launcher.json
ROS 2 TCP       : disabled
```

`ROS 2 TCP`が`disabled`なら単体デモ用の構成生成は完了です。`error:`で終了した場合はNGです。

## 2. Nova5 Runtimeをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で生成した`launcher.json`と、Forge済みの`nova5.contact.xml` |
| この作業のゴール | MuJoCo上でNova5を動かす`robot-arm-hakoniwa-asset`が生成される。 |

MuJoCo Viewerを使用する通常ビルドです。

```bash
python tools/recipe/nova5.py build
ls -l ../work-host/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
```

画面のないHostやCIでは、最初のコマンドだけ`build --headless`へ置き換えます。最後の`ls`で`robot-arm-hakoniwa-asset`が表示されればOK、`No such file or directory`ならNGです。

次は[箱庭単体の起動・動作確認](operation.md)へ進みます。
