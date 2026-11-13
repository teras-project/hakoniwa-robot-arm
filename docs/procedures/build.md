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

以下の`bash`コマンド例はLinux/macOSの箱庭Workspaceでの **Nova5 Runtime 基礎ビルド**用です。ROS 利用構成では、対応する上表の手順に従い公式 Dobot ソース・ROS メッセージ・PDU-RPC・専用 Asset も追加ビルドしてください。Windows native の専用 Dobot Asset は[PowerShell手順](windows-host-docker/build.md)を使用しますが、ビルド・結合は未検証です。`text`ブロックは配置先の説明であり、実行しません。

Nova5の実行ファイルは、ソースツリーではなく選択した箱庭workへ生成されます。配置先（参照用。コマンドではない）:

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-dobot-asset  # ROS 用追加ビルド
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

## センサの実装を選ぶ準備

センサ（関節のエンコーダ、力覚、IMU、LiDAR、カメラなど）を使うときだけ必要です。センサの設定の `implementation` で、センサごとに実装を選びます（書き方は [hakoniwa-robot-runtime の設定](https://github.com/hakoniwalab/hakoniwa-robot-runtime/blob/main/docs/configuration.md#34-センサopt-in)）。選んだ実装を、アームのビルドに組み込んでおきます。

既定は `reference`（真の値だけを返す参照実装）です。ライブラリは要らず、[hakoniwa-sensor-adapter](https://github.com/hakoniwalab/hakoniwa-sensor-adapter) をアームのリポジトリと同じ階層に置くだけで、ソースから一緒にビルドされます。SO-101 の既定のセンサ（作業台の上の LiDAR、手首の力覚）は、これで動きます。

| 実装 | 対応するセンサ | 用意するもの |
| --- | --- | --- |
| `reference` | LiDAR（一瞬で撮る方式）、力覚、関節のエンコーダ。どれも真の値だけ（誤差なし） | [hakoniwa-sensor-adapter](https://github.com/hakoniwalab/hakoniwa-sensor-adapter) を同じ階層に置く。ライブラリは不要 |
| `hakoniwa` | 全種類 | 箱庭ラボが提供するライブラリです。[箱庭ラボにお問い合わせください](https://hakoniwa-lab.net/contact/)。 |
| `airsim` | IMU、地磁気、気圧、GPS | [hakoniwa-sensor-adapter-airsim](https://github.com/hakoniwalab/hakoniwa-sensor-adapter-airsim) をビルドします（C++17 と Boost のヘッダが必要）。 |
| `gazebo` | 関節のエンコーダ（真値）、力覚、IMU、地磁気、気圧、GPS | [hakoniwa-sensor-adapter-gazebo](https://github.com/hakoniwalab/hakoniwa-sensor-adapter-gazebo) をビルドします（gz-sensors が必要。pixi か Docker で入れる手順がその README にあります）。リンクには gz-sensors のライブラリも要ります。 |

`airsim` のライブラリを作るコマンド（アームのリポジトリと同じ階層で実行）:

```bash
git clone https://github.com/hakoniwalab/hakoniwa-sensor-adapter.git
git clone https://github.com/hakoniwalab/hakoniwa-sensor-adapter-airsim.git
cmake -S hakoniwa-sensor-adapter-airsim -B hakoniwa-sensor-adapter-airsim/build -DCMAKE_BUILD_TYPE=Release
cmake --build hakoniwa-sensor-adapter-airsim/build -j
```

レシピの `configure --sensors` と `build --sensors` は、次の環境変数から CMake に渡します。

| 変数 | 値 |
| --- | --- |
| `HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS` | 組み込む実装の名前をセミコロンで並べる。既定は `reference`（例：`hakoniwa;reference`） |
| `HAKO_ROBOT_ARM_SENSOR_LIBRARIES` | `reference` 以外の実装のライブラリ（`airsim` なら `hakoniwa-sensor-adapter-airsim/build/libhakoniwa_sensor_adapter_airsim.a`）。`reference` だけなら要らない |

- 設定で選んだ実装がリンクされていないと、起動時に理由を示して止まります。
- 定義ファイルの書き方は実装ごとに違います（`airsim` は Project AirSim のセンサの JSON、`gazebo` は SDFormat を JSON に写したもの）。
- SO-101 では、`configure --sensors` が既定のセンサの組（`recipes/so101/config/sensors/so101-sensors.json`、`reference`）を選びます。箱庭ラボの実装の組を使うときは、`configure --sensors --sensor-implementation hakoniwa`（`so101-sensors-hakoniwa.json`）にし、上の 2 つで `hakoniwa` とそのライブラリを渡します。

ビルド後は、選択した利用構成の[起動・動作確認手順](operation.md)へ進んでください。
