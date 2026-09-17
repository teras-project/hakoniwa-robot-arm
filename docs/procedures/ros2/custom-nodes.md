# 独自ROS 2 nodeの作成とbuild

箱庭が生成する`../work-host/ros2`を基盤環境として利用し、利用者のROS 2 packageは別のcolcon workspaceへ置きます。ここではRobot Arm repositoryと同じ親ディレクトリに`ros2-user-ws`を作る例を示します。

付属の`hakoniwa_arm_samples`も同じ考え方で、箱庭ROS 2基盤環境とは別のワークスペースへ標準colconでbuildしています。基盤環境の生成先と実行時の接続関係は[ROS 2 Bridge基盤環境の成果物と接続関係](../../design/ros2-bridge-environment.md)を参照してください。

`../work-host/ros2`はツールが管理する生成領域です。利用者のsource codeをその`src`として追加したり、`install`配下を直接編集したりしないでください。

## 1. 利用者用workspaceとpackageを作る

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | build済みの`../work-host/ros2/activate.bash` |
| この作業のゴール | 利用者がGit管理できる`../ros2-user-ws/src/my_hakoniwa_arm`を作成する。 |

箱庭側のROS 2 workspaceを有効にしてから、通常のROS 2 packageとして作成します。

```bash
source ../work-host/ros2/activate.bash
mkdir -p ../ros2-user-ws/src
cd ../ros2-user-ws/src

ros2 pkg create my_hakoniwa_arm \
  --build-type ament_python \
  --dependencies rclpy sensor_msgs trajectory_msgs
```

正常時は次の形式で表示されます。

```text
going to create a new package
package name: my_hakoniwa_arm
...
```

package名と依存message typeは用途に合わせて変更できます。Robot Armとの基本的な接続点は次です。

| 用途 | ROS interface |
| --- | --- |
| 目標関節軌道を送る | `/joint_trajectory`へ`trajectory_msgs/msg/JointTrajectory`をpublish |
| 現在の関節状態を読む | `/pdu/joint_states`から`sensor_msgs/msg/JointState`をsubscribe |

nodeの実装、`setup.py`の`console_scripts`、`package.xml`は通常のament Python packageと同じ方法で編集します。message内容の条件は[ROS 2によるアーム操作](arm-operations.md)を参照してください。

## 2. 利用者用workspaceをbuildする

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | `ros2-user-ws`のroot |
| この作業の入力成果物 | `src/`配下へ作成・編集した利用者のROS 2 packageと、build済み箱庭ROS 2基盤環境 |
| この作業のゴール | 利用者のpackageが`ros2-user-ws/install`へinstallされる。 |

必ず箱庭ROS 2基盤環境を先にsourceしてからcolconを実行します。

```bash
cd /absolute/path/to/ros2-user-ws
source ../work-host/ros2/activate.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_hakoniwa_arm
```

`Summary: ... packages finished`が表示され、最後のコマンドに登録した実行ファイルが表示されればOKです。CMake／Python error、`packages failed`、実行ファイルが空の場合はNGです。

source codeを変更した後は、同じディレクトリで対象packageだけを再buildできます。

```bash
source ../work-host/ros2/activate.bash
colcon build --symlink-install --packages-select my_hakoniwa_arm
```

## 3. 独自nodeを実行する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 軌道送信nodeは`host-ros-control`、状態監視nodeは`host-ros-monitor` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動中のRuntimeとROS Bridge、build済みの利用者用ROS 2ワークスペース |
| この作業のゴール | 独自nodeが箱庭のROS topicへ接続し、送信または受信できる。 |

箱庭側のrole profileを先にsourceし、その後に利用者用ワークスペースの`setup.bash`をsourceします。次は軌道送信nodeの例です。

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source ../work-host/profiles/activate-host-ros-control.bash
source ../ros2-user-ws/install/setup.bash

ros2 run my_hakoniwa_arm my_node
```

JointStateを読むnodeでは`activate-host-ros-monitor.bash`を使用します。sourceの順序は、常に箱庭ROS 2基盤環境、利用者用ROS 2ワークスペースの順です。

```text
箱庭ROS 2基盤環境: ../work-host/ros2/activate.bash
        ↓
利用者用ROS 2ワークスペース: ../ros2-user-ws/install/setup.bash
        ↓
ros2 run 利用者package 利用者node
```

動作確認は、既存サンプルと同様にViewer、`/pdu/joint_states`、node自身のログを照合します。
