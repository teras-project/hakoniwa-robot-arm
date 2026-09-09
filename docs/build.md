# ビルド手順

セットアップ時に選んだ利用構成と同じ行の手順を使用してください。

| 利用構成 | ビルド手順 |
| --- | --- |
| host-only | [build-host-only.md](build-host-only.md) |
| host+docker | [build-host-docker.md](build-host-docker.md) |
| docker-only | [build-docker-only.md](build-docker-only.md) |

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

