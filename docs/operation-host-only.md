# host-only起動・動作確認

[host-onlyビルド](build-host-only.md)の完了が前提です。単体デモは`host-hako`だけで確認できます。ROS 2連携では、[端末ロール](terminal-roles.md)で定義した4端末を使用します。monitorとcontrolの意味、パラメータ、カスタマイズは[ROS 2によるアーム操作](ros2-arm-operations.md)を参照してください。

## A. 箱庭シミュレーション単体

**実行場所:** activeな`host-hako`。作業ディレクトリは`$HAKONIWA_COMPOSER`です。

**入力:** 単体デモ構成でconfigure・build済みのNova5 Runtimeと、activeな`host-hako`。

**ゴール:** ROS 2を使わず、Runtime、Launcher、PDU、MuJoCo Viewerの経路が単体で成立することを確認する。

このモードでは、`start`がRuntimeとViewerに加えて自動デモ軌道送信を起動します。`start`直後にNova5が動くのは正常な期待挙動です。

`host-hako`で実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

**成功判定:** `doctor`の必須項目がすべて`[OK]`であり、`status`が`RUNNING`となる。Viewerありの構成では、Nova5が自動デモ軌道を安全に完走する。

**次段への出力:** 単体動作が確認済みのRuntime。ROS 2連携を行う場合は、単体モードを停止してからBへ進む。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

停止後の成功判定は`TERMINATED`です。

## B. Ubuntu Host上のROS 2連携

**実行場所:** 下表の4端末。`host-hako`は`$HAKONIWA_COMPOSER`、残りの3端末はprofileをsourceする前に`$ARM_PACK`へ移動します。

**入力:** `--ros2-tcp`でconfigure・build済みのRuntimeと、ROS 2 workspace build済みのwork。

**ゴール:** `JointTrajectory`でアームを動かし、`JointState`で結果を観察する。

ROS 2連携では、最初に4端末を用意します。

| 端末 | 使うprofile | 操作 |
| --- | --- | --- |
| `host-hako` | activeな箱庭Workspace | Runtime、Viewer、Host TCP Bridgeを起動する。 |
| `host-ros-bridge` | `activate-host-ros-bridge.bash` | ROS Bridgeを起動したままにする。 |
| `host-ros-monitor` | `activate-host-ros-monitor.bash` | JointStateを監視する。 |
| `host-ros-control` | `activate-host-ros-control.bash` | JointTrajectoryを送信する。 |

### 1. RuntimeとHost TCP Bridgeを起動する

**実行場所:** activeな`host-hako`の`$HAKONIWA_COMPOSER`。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
python "$ARM_PACK/tools/recipe/nova5.py" status
```

**成功判定:** `doctor`の必須項目がすべて`[OK]`であり、`status`が`RUNNING`となる。LauncherがRuntimeとHost側SHM/TCP Bridgeを一緒に起動するため、`ros2_tcp.py start-host`は実行しません。

### 2. ROS Bridgeを起動する

**実行場所:** 新しい通常Host terminalの`$ARM_PACK`。profileをsource後、この端末は`host-ros-bridge`になります。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source "$HAKOBASE_DIR/work-host/profiles/activate-host-ros-bridge.bash"

test -f "$HAKONIWA_ROS_BINDING"
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

**成功判定:** promptが`(host-ros-bridge)`で始まり、Bridgeがerrorなく起動している。このterminalは終了まで開いたままにします。

### 3. JointStateを観察する

**実行場所:** 別の通常Host terminalの`$ARM_PACK`。profileをsource後、この端末は`host-ros-monitor`になります。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source "$HAKOBASE_DIR/work-host/profiles/activate-host-ros-monitor.bash"

ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

**成功判定:** promptが`(host-ros-monitor)`で始まり、`joint1`から`joint6`の位置が表示される。このterminalは観察のため開いたままにします。

### 4. JointTrajectoryを送信する

**実行場所:** さらに別の通常Host terminalの`$ARM_PACK`。profileをsource後、この端末は`host-ros-control`になります。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/activate.bash
source "$HAKOBASE_DIR/work-host/profiles/activate-host-ros-control.bash"

ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

**成功判定:** promptが`(host-ros-control)`で始まり、controlが軌道をpublishする。Viewer上でNova5が動き、`host-ros-monitor`の関節位置も変化する。

**次段への出力:** ROS 2からの軌道制御と状態取得が確認済みのRuntime。

### 5. 終了する

**実行場所:** `host-hako`の`$HAKONIWA_COMPOSER`。ほかの3端末は先にCtrl+Cで停止します。

`host-ros-control`、`host-ros-monitor`、`host-ros-bridge`をCtrl+Cで停止します。最後に`host-hako`でRuntimeを停止します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" status
```

**成功判定:** `TERMINATED`となる。
