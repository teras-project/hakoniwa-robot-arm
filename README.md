# hakoniwa-robot-arm

`hakoniwa-robot-arm` は、URDF / Xacro で記述されたROSロボットモデルをもとに、箱庭上でロボットアームシミュレータを構築・実行するためのシミュレーション開発基盤です。

ロボットモデルをMuJoCo形式へ変換し、[箱庭ロボットランタイム](https://github.com/hakoniwalab/hakoniwa-robot-runtime)と組み合わせることで、実機を使用せずに関節制御や状態取得を行えます。また、ROS 2からの `JointTrajectory` による制御と `JointState` の取得にも対応しています。

現在のサポート状況：

- DOBOT Nova5

## できること

- URDF / Xacroで記述されたロボットモデルをMuJoCo形式へ変換
- MuJoCoによるロボットアームの物理シミュレーション
- 箱庭ロボットランタイムによる関節制御
- ROS 2 `JointTrajectory` による関節軌道制御
- ROS 2 `JointState` による関節状態の取得
- Dockerを利用したROS 2実行環境
- Host上のMuJoCo Viewerを利用したシミュレーション可視化

## アーキテクチャ

シミュレータ側とROS 2側をTCPで分離し、ROS 2標準メッセージを用いてロボットアームを制御・観測します。

```mermaid
flowchart LR

  subgraph SIM["シミュレータ側<br/>Host / Docker"]

    SimApp["アームロボット<br/>シミュレータ<br/>(DOBOT Nova5)"]

    RobotRuntime["箱庭ロボットランタイム<br/>共通基盤"]

    Core["箱庭コア機能<br/>(SHM)"]

    PduBridge["箱庭PDU<br/>Bridge"]

    SimApp --> RobotRuntime

    RobotRuntime --> Core

    Core <--> PduBridge

  end

  subgraph ROS["ROS 2側(Humble / Jazzy)<br/>Ubuntu / Docker"]

    RosBridge["箱庭ROS<br/>Bridge"]

    RosNode["ROSノード<br/>サンプル制御<br/>プログラム"]

    RosBridge <--> RosNode

  end

  PduBridge <-->|"TCP : 54001"| RosBridge

  RobotRuntime -->|"JointState<br/>/pdu/joint_states"| Core

  Core -->|"JointState"| PduBridge

  RosBridge -->|"JointState"| RosNode

  RosNode -->|"JointTrajectory<br/>/joint_trajectory"| RosBridge

  PduBridge -->|"JointTrajectory"| Core

  Core -->|"JointTrajectory"| RobotRuntime
````

### シミュレータの構成

`hakoniwa-robot-arm` は、シミュレータ本体とROS 2環境を分離した構成を採用しています。

シミュレータ側では、箱庭ロボットランタイムがMuJoCoモデルと各種ロボット定義を読み込み、箱庭コアの共有メモリ（SHM）上でロボットアームの物理シミュレーション、制御入力の受付、状態出力を行います。

ROS 2側では、箱庭ROS Bridgeを介して箱庭PDUとROS 2メッセージを相互変換します。シミュレータ側とROS 2側はTCPで接続されるため、同一PC上だけでなく、HostとDocker Containerを分離した構成でも利用できます。

この構成により、シミュレータの実行環境とROS 2の実行環境を独立して構築できます。

#### シミュレータ側

シミュレータ側は、主に以下のコンポーネントで構成されます。

* アームロボットシミュレータ
* 箱庭ロボットランタイム
* 箱庭コア
* 箱庭PDU Bridge

箱庭ロボットランタイムは、ロボット定義に従ってMuJoCo上の関節を駆動し、関節状態を箱庭PDUとして出力します。

ROS 2から送信された `JointTrajectory` は、箱庭PDU Bridgeを経由して箱庭コアの共有メモリへ転送され、ロボットランタイムの関節軌道コントローラへ入力されます。

反対に、シミュレーション中の関節状態は `JointState` 相当の箱庭PDUとして出力され、箱庭PDU Bridgeを介してROS 2側へ転送されます。

MuJoCo Viewerを利用する場合はシミュレータ側で表示します。また、Viewerを使用しないheadless実行にも対応しています。

#### ROS側

ROS 2側は、主に以下のコンポーネントで構成されます。

* 箱庭ROS Bridge
* ROS 2ノード
* サンプル制御プログラム

箱庭ROS Bridgeは、TCPで受信した箱庭PDUとROS 2標準メッセージの間を変換します。

ロボットアームの制御には `trajectory_msgs/msg/JointTrajectory` を使用し、シミュレータからの関節状態取得には `sensor_msgs/msg/JointState` を使用します。

ROS 2ノードから送信された `JointTrajectory` は箱庭ROS BridgeによってTCPへ転送され、シミュレータ側へ届けられます。シミュレータ側から送信された関節状態は、逆方向に変換されてROS 2の `JointState` として利用できます。

ROS 2環境として、HumbleおよびJazzyを利用できます。

#### 箱庭ロボットランタイム

箱庭ロボットランタイムは、ロボットごとの挙動や通信構成を定義ファイルとして与えることで、共通のアプリケーションコードからロボットシミュレータを構築する仕組みです。

ロボットの構成は、主に以下の定義ファイルによって記述されます。

* 箱庭アセットマニフェスト
* MuJoCoモデル（MJCF）
* PDU定義
* PDU通信定義
* 各種アクチュエータ、コントローラ、センサ設定

これらの定義をロボットランタイムが読み込み、物理モデル、制御入力、状態出力、通信経路を組み立てます。

そのため、ロボットごとに専用のアプリケーションコードを作り込む必要がなく、共通のランタイム実装を利用したまま、定義ファイルを差し替えることで異なるロボットのシミュレータを構築できます。

この方式により、ロボット固有の差分をモデルと設定へ閉じ込め、シミュレータ本体のアプリケーションコードを共通化しています。


## 動作確認環境

| 項目           | 確認環境                                |
| ------------ | ----------------------------------- |
| Host OS      | macOS（Apple Silicon） / Ubuntu 24.04 |
| ROS 2        | Humble / Jazzy                      |
| MuJoCo       | 3.9.0                               |
| 箱庭側 Python   | 3.12                                |
| Build System | CMake / colcon                      |

HostがmacOSの場合、ROS 2環境をDocker Container上で実行し、Host上の箱庭ロボットアームシミュレータとTCP Bridgeを介して接続します。

## クイックスタート

TODO: リポジトリの取得、依存関係の準備、ロボットモデルのForge、ビルド、シミュレーション起動までの最短手順を記載する。
