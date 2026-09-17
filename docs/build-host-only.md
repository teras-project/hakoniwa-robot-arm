# host-onlyビルド

[host-onlyセットアップ](setup-host-only.md)でNova5 MJCFを生成してから実行します。このページでは、最初に「単体デモ」または「ROS 2連携」のどちらか一方を選びます。

## 1. 起動構成を選んでLauncherを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | `../work-host/model-forge/nova5/install/nova5.contact.xml` |
| この作業のゴール | 選択した構成のLauncherとrole profileが`../work-host`へ生成される。 |

次のAまたはBを一つだけ選びます。ROS 2連携を試す場合は、必ずBを実行してください。

### A. ROS 2を使わない単体デモ

```bash
python tools/recipe/nova5.py configure \
  --environment --realtime-sync-cycle-msec 50
```

正常時は末尾に次の形式で表示されます。

```text
Launcher        : /.../work-host/recipes/nova5-joint-trajectory-control/config/launcher.json
ROS 2 TCP       : disabled
```

`ROS 2 TCP`が`disabled`なら単体デモ用の構成生成は完了です。`error:`で終了した場合はNGです。

### B. ROS 2連携

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

`ROS 2 TCP`が`enabled`で、profileとbindingの両方が表示されればOKです。`No such file or directory`なら先へ進まず、このBの`configure --ros2-tcp`を再実行します。

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

単体デモを選択した場合は、[箱庭シミュレーション単体](operation-host-only.md#a-箱庭シミュレーション単体)へ進みます。ROS 2連携を選択した場合は、次の手順3を続けます。

## 3. ROS 2 workspaceをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。この作業で`host-ros-build`になる。`host-hako`では実行しない。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 手順1-Bで生成した`activate-host-ros-build.bash`と、手順2でbuildしたNova5 Runtime |
| この作業のゴール | ROS Bridge、`monitor`、`control`を含むROS 2 workspaceが`../work-host/ros2`へ生成され、doctorが成功する。 |

この手順へ進む前に、手順1-Bの`ls`で`activate-host-ros-build.bash`が表示されたことを確認してください。未確認の場合は手順1-Bへ戻ります。

新しい通常Host terminalで実行します。`/absolute/path/to/hakoniwa-robot-arm`は実際のclone先へ置き換えます。

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
ls -l ../work-host/profiles/activate-host-ros-build.bash
```

profileのファイル情報が表示されれば続けます。`No such file or directory`ならprofileをsourceせず、手順1-Bへ戻ります。

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

次は[host-only起動・動作確認](operation-host-only.md#b-ubuntu-host上のros-2連携)へ進みます。
