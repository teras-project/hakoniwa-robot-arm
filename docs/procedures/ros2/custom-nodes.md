# 独自ROS 2 nodeの作成とbuild

箱庭が生成する`../work-host/ros2`と公式 Dobot メッセージ overlay を基盤環境として利用し、利用者のROS 2 packageは別のcolcon workspaceへ置きます。ここではRobot Arm repositoryと同じ親ディレクトリに`ros2-user-ws`を作る Ubuntu Host の例を示します。

付属の`hakoniwa_arm_samples`も同じ考え方で、箱庭ROS 2基盤環境とは別の Dobot アプリケーション workspace へ標準colconでbuildしています。基盤環境の生成先と実行時の接続関係は[ROS 2 Bridge基盤環境の成果物と接続関係](../../design/ros2-bridge-environment.md)を参照してください。

`../work-host/ros2`はツールが管理する生成領域です。利用者のsource codeをその`src`として追加したり、`install`配下を直接編集したりしないでください。

[手順一覧](../README.md)に戻る。このページは、Ubuntu Hostで[Host ROS 2連携の動作確認](../host-ros2/operation.md)の手順4まで確認し、手順5で終了する前に続けてください。すでに終了した場合は、同じ動作確認手順の手順1と2に従ってRuntimeと Dobot launch を再起動し、独自nodeの実行中は起動したままにします。箱庭Workspaceの`host-hako`ではなく、通常のHost terminalからROS 2環境を有効にします。コマンドと出力例の区別は[手順の読み方](../conventions.md#コードブロックと端末の読み方)を参照してください。

## 1. 利用者用workspaceとpackageを作る

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みの`../work-host/ros2/activate.bash` |
| この作業のゴール | 利用者がGit管理できる`../ros2-user-ws/src/my_hakoniwa_arm`を作成する。 |

通常のHost terminalでRobot Arm repository rootへ移動し、`pwd`で確認してください。箱庭側のROS 2 workspaceを有効にしてから、通常のROS 2 packageとして作成します。

実行するコマンド（通常のHost terminal）:
```bash
source ../work-host/ros2/activate.bash
source ../work-host/dobot-ros/install/setup.bash
source ../work-host/dobot-types/activate.bash
source ../work-host/dobot-apps/install/setup.bash
mkdir -p ../ros2-user-ws/src
cd ../ros2-user-ws/src

ros2 pkg create my_hakoniwa_arm \
  --build-type ament_python \
  --dependencies rclpy sensor_msgs dobot_msgs_v4
```

`going to create a new package`に続いて`package name: my_hakoniwa_arm`と表示されれば作成できています。

package名と依存message typeは用途に合わせて変更できます。Robot Armとの基本的な接続点は次です。

| 用途 | ROS interface |
| --- | --- |
| 現在角を確認する | `/dobot_bringup_ros2/srv/GetAngle` に `dobot_msgs_v4/srv/GetAngle` を呼ぶ |
| 小さな関節動作を依頼する | 現在角から小さな目標を作り `/dobot_bringup_ros2/srv/MovJ` に `dobot_msgs_v4/srv/MovJ` を呼ぶ。実機では安全確認を先に行う |
| 現在の関節状態を読む | `/joint_states_robot` から `sensor_msgs/msg/JointState` を subscribe |

nodeの実装、`setup.py`の`console_scripts`、`package.xml`は通常のament Python packageと同じ方法で編集します。message内容の条件は[ROS 2によるアーム操作](arm-operations.md)を参照してください。

## 2. 利用者用workspaceをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | `ros2-user-ws`のroot |
| この作業の入力成果物 | `src/`配下へ作成・編集した利用者のROS 2 packageと、build済み箱庭ROS 2基盤環境 |
| この作業のゴール | 利用者のpackageが`ros2-user-ws/install`へinstallされる。 |

必ず箱庭ROS 2基盤環境を先にsourceしてからcolconを実行します。

前段のコマンドを実行済みなら`ros2-user-ws/src`にいます。次のコマンドでワークスペースのrootへ移動してbuildします。

実行するコマンド（通常のHost terminal）:
```bash
cd ..
source ../work-host/ros2/activate.bash
source ../work-host/dobot-ros/install/setup.bash
source ../work-host/dobot-types/activate.bash
source ../work-host/dobot-apps/install/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_hakoniwa_arm
```

`Summary: ... packages finished`が表示され、最後のコマンドに登録した実行ファイルが表示されればOKです。CMake／Python error、`packages failed`、実行ファイルが空の場合はNGです。

source codeを変更した後は、同じディレクトリで対象packageだけを再buildできます。

実行するコマンド（同じHost terminal、`ros2-user-ws`のroot）:
```bash
source ../work-host/ros2/activate.bash
source ../work-host/dobot-ros/install/setup.bash
source ../work-host/dobot-types/activate.bash
source ../work-host/dobot-apps/install/setup.bash
colcon build --symlink-install --packages-select my_hakoniwa_arm
```

## 3. 独自nodeを実行する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 軌道送信nodeは`host-ros-control`、状態監視nodeは`host-ros-monitor` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、build済みの利用者用ROS 2ワークスペース |
| この作業のゴール | 独自nodeが箱庭のROS topicへ接続し、送信または受信できる。 |

箱庭側のrole profile、公式 Dobot overlay、アプリケーション overlay の順に source し、その後に利用者用ワークスペースの`setup.bash`をsourceします。次はサービスを利用するnodeの例です。

新しい通常のHost terminalでRobot Arm repository rootへ移動し、`pwd`で確認してから実行してください。

実行するコマンド（`host-ros-control`にする通常のHost terminal）:
```bash
source ../work-host/profiles/activate-host-ros-control.bash
source ../work-host/ros2/activate.bash
source ../work-host/dobot-ros/install/setup.bash
source ../work-host/dobot-types/activate.bash
source ../work-host/dobot-apps/install/setup.bash
source ../ros2-user-ws/install/setup.bash

ros2 run my_hakoniwa_arm my_node
```

JointStateを読むnodeでは`activate-host-ros-monitor.bash`を使用します。sourceの順序は、常に箱庭ROS 2基盤環境、利用者用ROS 2ワークスペースの順です。

環境の読み込み順（参照用。コマンドではない）:
```text
箱庭ROS 2基盤環境: ../work-host/ros2/activate.bash
        ↓
公式 Dobot: ../work-host/dobot-ros/install/setup.bash
        ↓
Dobot PDU 型: ../work-host/dobot-types/activate.bash
        ↓
アプリ: ../work-host/dobot-apps/install/setup.bash
        ↓
利用者用ROS 2ワークスペース: ../ros2-user-ws/install/setup.bash
        ↓
ros2 run 利用者package 利用者node
```

動作確認は、既存サンプルと同様に Viewer、`/joint_states_robot`、`GetAngle` と node 自身のログを照合します。`both` では実機／箱庭の状態 topic を混ぜず、[実機向け安全上の警告](arm-operations.md)に従ってください。
