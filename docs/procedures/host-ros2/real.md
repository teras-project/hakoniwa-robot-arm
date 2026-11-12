# 発展：Ubuntu host-ros2 で実機にも接続する

[箱庭のセットアップ](setup.md)・[ビルド](build.md)・[起動と公式デモの確認](operation.md)を完了した環境への**追加手順**です。`dobot_msgs_v4`、`dobot_demo`、`dobot-types`、箱庭 Asset を作り直す必要はありません。Ubuntu Native で `real`／`both` の実機動作を確認済みです。ただし、ロボットの周囲、可動域、初期姿勢、実機の非常停止手段は毎回確認し、安全監督者のもとで進めてください。ROS サービスの `Stop` は非常停止ではありません。

**無改変の公式 `dobot_demo demo` を実機へ送らないでください。** デモは J1=50°・J2=-8°への絶対移動を含みます。箱庭で同じ公式サービスを使えることと、その軌道を実機で安全に実行できることは別です。実機では現在角を確認してから安全な小動作だけを検討します。

## 1. ROS 端末で公式実機 driver を追加ビルドする

箱庭 Runtime と ROS launch を停止してから、`host-hako` ではない通常の Ubuntu ROS 端末で `hakoniwa-robot-arm` ルートへ移動します。箱庭用の公式 checkout と ROS overlay を再利用します。Ubuntu 22.04 では `jazzy` を `humble` に替えてください。

```bash
export DOBOT_WORK="$(realpath ../work-host)"
export DOBOT_SRC="$DOBOT_WORK/dobot-deps/DOBOT_6Axis_ROS2_V4"
source /opt/ros/jazzy/setup.bash
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
test -f "$DOBOT_SRC/dobot_bringup_v4/package.xml"
colcon --log-base "$DOBOT_WORK/dobot-ros/log" build \
  --base-paths "$DOBOT_SRC/dobot_bringup_v4" \
  --build-base "$DOBOT_WORK/dobot-ros/build" \
  --install-base "$DOBOT_WORK/dobot-ros/install" \
  --symlink-install --packages-select dobot_bringup_v4
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
ros2 pkg executables dobot_bringup_v4
```

`dobot_bringup_v4_node` が表示されなければ接続へ進まないでください。ドライバの追加は箱庭用の PDU-RPC／Native Asset の再ビルドを必要としません。

## 2. 実機接続とモードを選ぶ

実機の IP アドレスを確認し、ROS 端末の network から到達できるよう準備します。`192.168.5.1` は以下の例であり、実際の IP を確認せず使用しないでください。`hakoniwa-robot-arm` ルートの新しい通常 Host terminal で[箱庭手順の bridge 端末](operation.md#2-dobot-サービスと状態-topic-を起動する)と同じ環境を読み込み、**追加ビルドした driver の overlay も読み直します**。

```bash
source ../work-host/profiles/activate-host-ros-bridge.bash
export DOBOT_WORK="$(realpath ../work-host)"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
source "$DOBOT_WORK/dobot-types/activate.bash"
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
```

箱庭の launch は止めてから、**いずれか一方**を起動します。同じ ROS domain に古い driver や bridge を二重起動しないでください。

- **`real`**：箱庭 Runtime を停止したまま公式 driver のみ起動します。

  ```bash
  ros2 launch hakoniwa_dobot dobot.launch.py backend:=real robot_ip:=192.168.5.1
  ```

- **`both`**：箱庭 Runtime を[箱庭手順](operation.md#1-runtimeとhost-tcp-bridgeを起動する)どおり起動し、実機と箱庭の初期姿勢を事前に合わせます。service/topic binding は段階2のビルドで生成済みのものを再利用します。

  ```bash
  ros2 launch hakoniwa_dobot dobot.launch.py backend:=both robot_ip:=192.168.5.1 \
    service_binding:="$DOBOT_WORK/dobot-services/dobot-services.json" \
    offset_dir:="$DOBOT_WORK/dobot-types/pdu/offset" \
    rpc_output:="$DOBOT_WORK/dobot-services/rpc" \
    topic_binding:="$DOBOT_WORK/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json"
  ```

`both` の状態は `/real/joint_states_robot` と `/hakoniwa/joint_states_robot` を別々に監視します。サービスの `res=0` は指令の受理で、到達や両者の同時成功を保証しません。実機で動かす前に、[操作と安全上の警告](../ros2/arm-operations.md)を確認し、`GetAngle` と dry-run で目標を点検してください。`hakoniwa_arm_samples control --execute` も実機を動かします。無改変の公式デモは `real`／`both` で実行しません。
