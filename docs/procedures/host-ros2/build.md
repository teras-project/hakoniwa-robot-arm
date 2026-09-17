# Host ROS 2連携ビルド

[Host ROS 2連携セットアップ](setup.md)でNova5 MJCFを生成してから実行します。この手順では、箱庭RuntimeとROS 2をTCPで接続する構成を生成します。

## 1. ROS 2連携用Launcherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | `../work-host/model-forge/nova5/install/nova5.contact.xml` |
| この作業のゴール | ROS 2用Launcher、binding、4種類のROS端末profileが`../work-host`へ生成される。 |

`--ros2-tcp`を付けることで、ROS 2用Launcher、binding、4種類のROS端末profileを生成します。

```bash
python tools/recipe/nova5.py configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50

ls -l ../work-host/profiles/activate-host-ros-build.bash
ls -l ../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

正常時は末尾と`ls`に次の内容が表示されます。

```text
Profiles        : ...activate-host-ros-build.bash, ...activate-host-ros-bridge.bash, ...
ROS 2 TCP       : enabled
... /.../work-host/profiles/activate-host-ros-build.bash
... /.../work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

`ROS 2 TCP`が`enabled`で、profileとbindingの両方が表示されればOKです。`No such file or directory`なら先へ進まず、この手順の`configure --ros2-tcp`を再実行します。

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

続けてROS 2基盤環境をbuildします。

## 3. ROS 2 workspaceをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この作業で`host-ros-build`になる。`host-hako`では実行しない。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 手順1で生成した`activate-host-ros-build.bash`と、手順2でbuildしたNova5 Runtime |
| この作業のゴール | EndpointとROS Bridgeを含むROS 2基盤環境が`../work-host/ros2`へ生成され、doctorが成功する。 |

手順1のconfigureがROS 2成果物の配置先と端末profileを生成済みです。この手順では、その配置先へEndpointとROS Bridgeをbuildします。利用者がCMake option、Python環境、共有ライブラリの検索pathを個別に設定する必要はありません。

生成されるファイルの配置と、`ros2 run`からEndpoint共有ライブラリ、TCP、箱庭Runtimeまでの接続関係は、[ROS 2 Bridge基盤環境の成果物と接続関係](../../design/ros2-bridge-environment.md)を参照してください。

この手順へ進む前に、手順1の`ls`で`activate-host-ros-build.bash`が表示されたことを確認してください。未確認の場合は手順1へ戻ります。

新しい通常Host terminalで実行します。`/absolute/path/to/hakoniwa-robot-arm`は実際のclone先へ置き換えます。

```bash
cd /absolute/path/to/hakoniwa-robot-arm
ls -l ../work-host/profiles/activate-host-ros-build.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`ならprofileをsourceせず、手順1へ戻ります。

```bash
source ../work-host/profiles/activate-host-ros-build.bash

/usr/bin/python3 tools/recipe/ros2_workspace.py build \
  --ros-distro jazzy
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor
```

Ubuntu 22.04／Humbleでは`--ros-distro humble`を指定します。正常時はbuildログの末尾に次の形式で表示され、続くdoctorがerrorなく終了します。

```text
ROS workspace installed: /.../work-host/ros2
source /.../work-host/ros2/activate.bash
```

`error:`または`missing installed ROS executable`が表示された場合はNGです。

## 4. サンプルpackageを標準colconでbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-ros-build` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段でbuildした`../work-host/ros2/activate.bash`と、`ros2_packages/hakoniwa_arm_samples` |
| この作業のゴール | `monitor`と`control`を含むサンプル用ROS 2ワークスペースが`../work-host/ros2-samples`へ生成される。 |

サンプルは箱庭基盤ではなくROS 2アプリケーションなので、標準のcolconでbuildします。最初に箱庭ROS 2基盤環境をsourceします。

```bash
source ../work-host/ros2/activate.bash

colcon --log-base ../work-host/ros2-samples/log build \
  --base-paths ros2_packages/hakoniwa_arm_samples \
  --build-base ../work-host/ros2-samples/build \
  --install-base ../work-host/ros2-samples/install \
  --symlink-install \
  --packages-select hakoniwa_arm_samples

source ../work-host/ros2-samples/install/setup.bash
ros2 pkg executables hakoniwa_arm_samples
```

正常時はcolconのsummaryに`1 package finished`が表示され、最後に次の2 executableが表示されます。

```text
hakoniwa_arm_samples control
hakoniwa_arm_samples monitor
```

次は[Host ROS 2連携の起動・動作確認](operation.md)へ進みます。

## 応用：独自ROS 2 nodeを追加する

まず[Host ROS 2連携の起動・動作確認](operation.md)を最後まで実行し、付属の`monitor`と`control`でROS 2連携が成功することを確認してください。

標準動作確認の完了後、この基盤環境を利用して独自packageを作成できます。手順は[独自ROS 2 nodeの作成とbuild](../ros2/custom-nodes.md)を参照してください。
