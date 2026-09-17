# ビルド手順

セットアップ時に選んだ利用構成と同じ行の手順を使用してください。

| 利用構成 | ビルド手順 |
| --- | --- |
| host-standalone | [箱庭単体ビルド](host-standalone/build.md) |
| host-ros2 | [Host ROS 2連携ビルド](host-ros2/build.md) |
| host+docker | [build-host-docker.md](host-docker/build.md) |
| docker-only | [build-docker-only.md](docker-only/build.md) |

## 共通ビルド契約

Nova5の実行ファイルは、ソースツリーではなく選択した箱庭workへ生成されます。

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
```

Viewerを利用するビルドは次です。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

CI、画面のない環境、macOS上のdocker-onlyではheadlessでビルドします。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

`build`はCMakeによる実行ファイルの構築を担当します。Viewer、ROS 2 TCP、周辺環境、realtime pacingなどの起動条件は`configure`がwork側のLauncher設定へ反映します。

ビルド後は、選択した利用構成の[起動・動作確認手順](operation.md)へ進んでください。
