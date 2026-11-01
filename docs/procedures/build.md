# ビルド手順

セットアップ時に選んだ利用構成と同じ行の手順を使用してください。

[手順一覧](README.md) → [セットアップ](setup.md) → **ビルド** → [起動・動作確認](operation.md)

| 利用構成 | ビルド手順 |
| --- | --- |
| host-standalone | [箱庭単体ビルド](host-standalone/build.md) |
| host-standalone + PS5 gamepad | [ゲームパッドビルド](host-standalone/build-gamepad.md) |
| windows-host-standalone | [Windows nativeビルド](windows-host-standalone/build.md) |
| windows-host-docker | [Windows host+Dockerビルド](windows-host-docker/build.md) |
| host-ros2 | [Host ROS 2連携ビルド](host-ros2/build.md) |
| host+docker | [build-host-docker.md](host-docker/build.md) |
| docker-only | [build-docker-only.md](docker-only/build.md) |

## 共通ビルド契約

以下の`bash`コマンド例はLinux/macOSの箱庭Workspace用です。Windowsでは上の表にあるWindows専用手順のPowerShellコマンドを使用してください。`text`ブロックは配置先の説明であり、実行しません。

Nova5の実行ファイルは、ソースツリーではなく選択した箱庭workへ生成されます。配置先（参照用。コマンドではない）:

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
```

実行するコマンド（選択した構成の箱庭Workspace、Viewerを利用する場合）:

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

実行するコマンド（選択した構成の箱庭Workspace、headlessの場合。上のブロックの代わり）:

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

`build`はCMakeによる実行ファイルの構築を担当します。Viewer、ROS 2 TCP、周辺環境、realtime pacingなどの起動条件は`configure`がwork側のLauncher設定へ反映します。

ビルド後は、選択した利用構成の[起動・動作確認手順](operation.md)へ進んでください。
