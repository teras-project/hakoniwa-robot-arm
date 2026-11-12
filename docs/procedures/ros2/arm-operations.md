# ROS 2によるアーム操作

この文書は Nova5 の Dobot 公式 ROS 2 API を使う操作を説明します。[host-ros2](../host-ros2/operation.md)、[host+docker](../host-docker/operation.md)、[docker-only](../docker-only/operation.md)、[Windows host+Docker](../windows-host-docker/operation.md) のいずれかの起動手順を先に完了してください。これらの箱庭手順では launch の既定モードを使い、モード選択は不要です。実機への追加手順は [Ubuntu host-ros2](../host-ros2/real.md) に限ります。Windows native Host の Dobot Asset はビルド・結合が未検証です。

[手順一覧](../README.md)に戻る。各 ROS 端末では `/opt/ros/<distro>/setup.bash`、`$DOBOT_WORK/ros2/activate.bash`、`$DOBOT_WORK/dobot-ros/install/setup.bash`、`$DOBOT_WORK/dobot-types/activate.bash`、`$DOBOT_WORK/dobot-apps/install/setup.bash` を順に source し、同じ `ROS_DOMAIN_ID`（既定 73）を使います。

## 入力とゴール

- **入力**: Dobot Asset が `RUNNING`、`backend:=virtual` の `dobot.launch.py` が service binding と topic binding の両方を使って起動していること。
- **ゴール**: `GetAngle` から現在角を読み、小さな相対目標を `MovJ` で送り、`/joint_states_robot` でも状態を観察すること。
- **成功判定**: サービス応答 `res=0`（受理）に加え、十分な時間をおいて `GetAngle` と JointState の両方で位置の変化を確認すること。受理応答だけでは到達を意味しません。

## monitor: 関節状態を観察する

`monitor` は `/joint_states_robot` から `sensor_msgs/msg/JointState` を受信します。`both` では `/real/joint_states_robot` と `/hakoniwa/joint_states_robot` を別々の端末で観察します。ROS JointState の角度は rad、`GetAngle`、`MovJ` と `ServoJ` の関節角は deg です。

実行するコマンド（ROS 2 monitor端末）:
```bash
ros2 topic info /joint_states_robot
ros2 run hakoniwa_arm_samples monitor --topic /joint_states_robot
```

終了するまで表示を続けます。最初の1メッセージだけ確認したい場合は `--once` を指定します。

## 小動作：現在位置を確認してから動かす

周囲・姿勢・可動域・非常停止手段を確認します。`both` では実機と箱庭の初期姿勢を事前に合わせ、実機に送る指令が鏡像にも届くことを確認します。実機へは無人で指令を送らないでください。`Stop` サービスは非常停止の代わりになりません。通信 timeout 時は受理済みか不明なので自動再送せず、両方の状態を点検してください。

`hakoniwa_arm_samples control` と公式 `dobot_demo demo` は、どちらも `/dobot_bringup_ros2/srv/*` を呼びます。プログラム自体は箱庭専用ではありません。`virtual` で起動していても、同じ ROS domain で実機 driver が同名サービスを提供していると宛先が競合します。`ros2 service type` だけでは提供元を区別できません。まず実機 driver を停止するか別の ROS domain に分離し、箱庭のサービスだけがこの名前を提供する状態で確認してください。`both` では公開サービスが実機と箱庭に動作指令を同時配送します。

付属 `hakoniwa_arm_samples control` は既定の **dry-run** では `GetAngle` だけを呼び、目標を表示します。サービスが競合していれば、取得した角度も実機のものかもしれません。`--execute` を付けると `EnableRobot`、`SpeedFactor=10%`、`MovJ` を呼び、J1 を現在角から +3° 動かします。実機が同名サービスを提供している場合や `real`／`both` の場合、実機も動き得ます。monitor は `/joint_states_robot` を既定で購読し、1 Hz で表示します。

実行するコマンド（ROS 2 control端末）:
```bash
ros2 service type /dobot_bringup_ros2/srv/GetAngle
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 run hakoniwa_arm_samples control
```

現在角と目標を確認し、指令先での動作を許可できる場合だけ明示的に実行します。

```bash
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
```

`both` の場合は `/dobot_bringup_ros2/srv/*` が同時配送、個別の観測には `/real/dobot_bringup_ros2/srv/GetAngle` と `/hakoniwa/dobot_bringup_ros2/srv/GetAngle` を使用します。`--execute` は **real／both でも実機を動かします**。初期姿勢合わせ、安全監督と明示的なリスク評価なしには付けないでください。必要に応じて別端末から `ros2 service call /dobot_bringup_ros2/srv/Stop dobot_msgs_v4/srv/Stop '{}'` で通常停止します。終了時は `DisableRobot` を呼びます。

## 公式デモ（箱庭環境でのみ実行）

公式 `dobot_demo/demo.py` は変更しません。`control` と同じ公開サービスに、`--execute` のような確認オプションなしで `EnableRobot`、`SpeedFactor=10`、`MovJ` を送り、**(J1,J2)=(50°,-8°) へ移動し、(0°,-8°) に移動**します。仮想 `MovJ` は関節モード（`mode=true`）の関節目標をキューに受け付け、10% の補間速度は 6 deg/s です。受理応答は到達を意味しません。箱庭だけで、可動域と周辺に問題がないことを確認した後に実行してください。

```bash
ros2 run dobot_demo demo
```

**real／both では公式デモを実行しないでください。** 50° の絶対角目標は現在姿勢から大きく動く可能性があり、実機に安全とは限りません。実機の確認は上記の現在角取得・dry-run・少量の `MovJ` の順で、安全責任者の立会いのもと行ってください。実機・箱庭の API 範囲と同時配送の制約は[Dobot の説明](../../../ros2_packages/hakoniwa_dobot/README.md)を参照してください。

仮想 `MovL` も `mode=true` の関節目標のみで、**関節空間補間の近似**です。Cartesian の直線運動は保証しません。`mode=false` は `MovJ`／`MovL` とも拒否します。仮想 `SpeedFactor=10%` での補間速度は `MovL` が 3 deg/s、`MovJ` が 6 deg/s です。仮想 `DO` は 1～24 の状態／パルスをシミュレートしますが、物理グリッパーはありません。実機・both に箱庭近似の安全性や等価性を適用しないでください。
