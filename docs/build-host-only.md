# host-onlyビルド

[host-onlyセットアップ](setup-host-only.md)の完了が前提です。`host-hako`でRuntimeをbuildし、ROS 2連携を使う場合だけ通常Host terminalでROS 2 workspaceをbuildします。

## 1. Runtime構成とrole profileを生成する

**実行場所:** activeな`host-hako`。作業ディレクトリは`$HAKONIWA_COMPOSER`です。

**入力:** Forge済みの`nova5.contact.xml`を持つ`host-hako`。

**ゴール:** 利用する起動構成をLauncherへ反映し、work配下のrole profileを生成する。

ROS 2を使わない単体デモでは、`host-hako`で実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --environment --realtime-sync-cycle-msec 50
```

ROS 2連携を行う場合は、次を実行します。`configure`の出力に`Profiles`として`$HAKONIWA_WORK_DIR/profiles/`配下のファイルが表示されます。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
```

**成功判定:** `Launcher`と`Profiles`の出力先が選択した`HAKONIWA_WORK_DIR`配下である。

**次段への出力:** 選択済みのLauncher設定とrole profile。

## 2. Nova5 Runtimeをbuildする

**実行場所:** activeな`host-hako`。作業ディレクトリは`$HAKONIWA_COMPOSER`です。

**入力:** 構成済みの`host-hako`。

**ゴール:** MuJoCo Runtime実行ファイルをworkへ生成する。

Viewerを利用する場合は通常ビルドを実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build
```

画面のないHostや自動確認ではheadlessを指定します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" build --headless
```

```bash
test -x "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-hakoniwa-asset"
```

**成功判定:** `robot-arm-hakoniwa-asset`が存在する。

**次段への出力:** 起動可能なNova5 Runtime。ROS 2を使わない場合は[host-only起動・動作確認](operation-host-only.md#A-箱庭シミュレーション単体)へ進みます。

## 3. ROS 2 workspaceをbuildする（ROS 2連携する場合）

**実行場所:** 通常のHost terminalの`$ARM_PACK`。`host-hako`では実行しません。

**入力:** `--ros2-tcp`でconfigure済みのworkと、前段で生成された`activate-host-ros-build.bash`。

**ゴール:** Bridge、monitor、controlを含むROS 2 workspaceをbuildする。

通常のHost terminalで、Robot Arm repositoryへ移動してprofileをsourceします。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source "$HAKOBASE_DIR/work-host/profiles/activate-host-ros-build.bash"

/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" build --ros-distro jazzy
/usr/bin/python3 "$ARM_PACK/tools/recipe/ros2_workspace.py" doctor
```

**成功判定:** `doctor`が`hakoniwa_pdu_ros`の`bridge`と、`hakoniwa_arm_samples`の`monitor`、`control`を検出する。

**次段への出力:** `host-ros-bridge`、`host-ros-monitor`、`host-ros-control` profileが利用できるROS 2 workspace。

次は[host-only起動・動作確認](operation-host-only.md)へ進んでください。
