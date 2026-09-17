# ROS 2 Bridge基盤環境の成果物と接続関係

この文書は、ROS 2連携用Recipeがworkディレクトリへ生成する成果物と、`ros2 run`で起動するBridgeから箱庭Runtimeまでの接続関係を説明します。

EndpointのCMake option、Python環境、Python接続モジュールの生成手順を利用者が個別に設定する必要はありません。これらはRecipeと構成ツールの責務です。

## 1. configureとbuildの責務

`nova5.py configure --ros2-tcp`は、ROS 2連携で使用する配置先と接続構成を決定します。

- ROS 2成果物の配置先を`HAKONIWA_ROS2_WS`として決定する。
- Host側PDUとROS 2 topicを結ぶ接続設定を生成する。
- ROS 2用の各端末profileを生成する。
- 各profileから同じROS 2成果物と接続設定を参照できるようにする。

続く`ros2_workspace.py build`は、configureで決まった配置先へ次の実行物を生成します。

- 箱庭Coreを内包しない`hakoniwa-pdu-endpoint`共有ライブラリ
- EndpointをPythonから呼び出す接続モジュール
- ROS 2 package `hakoniwa_pdu_ros`
- 上記をまとめて有効化する`activate.bash`

利用者が個別の環境変数やCMake optionを設定するのではなく、configureで生成されたprofileとbuild済み成果物を使用します。

## 2. workディレクトリの構成

標準のhost-ros2構成では、すべての生成物を`../work-host`以下へ配置します。

Docker構成では、Runtime側のworkとROS 2成果物を分けます。

| 構成 | Runtime、接続設定 | ROS 2 Bridge | ROS 2サンプル |
| --- | --- | --- | --- |
| host+docker | Hostの`../work-host` | `/workspace/ros2-work-<distro>` | `/workspace/ros2-work-<distro>-samples` |
| docker-only | `/workspace/work-docker-<distro>` | `/workspace/ros2-work-<distro>` | `/workspace/ros2-work-<distro>-samples` |

host+dockerではHost側で生成した`ros2-tcp`ディレクトリをContainerへread-only mountします。docker-onlyでは同じContainer内の`HAKONIWA_WORK_DIR`から接続設定を読みます。ROS 2成果物は、ROS distributionとCPU architectureが同じ場合に2構成で共有できます。

### 2.1 configureが生成する接続設定

```text
../work-host/
├── profiles/
│   ├── activate-host-ros-build.bash
│   ├── activate-host-ros-bridge.bash
│   ├── activate-host-ros-monitor.bash
│   └── activate-host-ros-control.bash
└── recipes/nova5-joint-trajectory-control/config/ros2-tcp/
    ├── pdu/                 # PDU型とPDU名の定義
    ├── cache/               # PDUの保持方式
    ├── comm/                # SHM／TCPの通信設定
    ├── endpoint/            # Host側／ROS 2側Endpoint設定
    ├── bridge/bridge.json   # Host側PDU Bridgeの転送設定
    ├── ros/binding.json     # ROS 2 topicとPDUの対応
    └── metadata.json        # 生成条件の記録
```

`ros/binding.json`には、ROS 2 Bridgeが使用するEndpoint設定と、ROS 2 topic／PDUの対応が入ります。Nova5では主に次の対応を生成します。

| ROS 2 topic | ROS message | PDU方向 |
| --- | --- | --- |
| `/joint_trajectory` | `trajectory_msgs/msg/JointTrajectory` | ROS 2から箱庭Runtimeへ送信 |
| `/pdu/joint_states` | `sensor_msgs/msg/JointState` | 箱庭RuntimeからROS 2へ送信 |

### 2.2 buildが生成するROS 2実行物

```text
../work-host/ros2/
├── native/lib/
│   └── libhakoniwa_pdu_endpoint.so
├── venv/lib/python*/site-packages/
│   ├── hakoniwa_pdu/
│   └── hakoniwa_pdu_endpoint/
│       ├── c_endpoint.py
│       └── _c_endpoint_ffi*.so
├── install/
│   ├── setup.bash
│   └── hakoniwa_pdu_ros/lib/hakoniwa_pdu_ros/bridge
├── build/                   # 構成ツールが使用する中間生成物
├── log/                     # build log
├── activate.bash            # 上記の実行環境をまとめて有効化
└── ros-workspace.json       # ROS distributionとCPU architectureの記録
```

利用者が直接使用するのは、主に`activate.bash`とinstall済みの`bridge`です。`build/`、`native/`、`venv/`を個別に編集しません。

付属サンプルは別の場所へ標準colconでbuildします。

```text
../work-host/ros2-samples/
└── install/
    ├── setup.bash
    └── hakoniwa_arm_samples/lib/hakoniwa_arm_samples/
        ├── monitor
        └── control
```

## 3. ROS 2 Bridgeから共有ライブラリまでの接続

`ros2 run hakoniwa_pdu_ros bridge`を実行したときの呼び出し関係は次のとおりです。

```text
ros2 run hakoniwa_pdu_ros bridge
        ↓ install済みのROS 2実行ファイルを検索
../work-host/ros2/install/.../hakoniwa_pdu_ros/bridge
        ↓ Python moduleを読み込み
hakoniwa_pdu_ros
        ↓
hakoniwa_pdu_endpoint.c_endpoint
        ↓ Python接続モジュール
hakoniwa_pdu_endpoint/_c_endpoint_ffi*.so
        ↓ 共有ライブラリを呼び出し
../work-host/ros2/native/lib/libhakoniwa_pdu_endpoint.so
```

ROS 2 Bridgeの実行ファイルが、Endpoint共有ライブラリを直接呼ぶ構成ではありません。BridgeはPython packageとPython接続モジュールを経由して、Endpoint共有ライブラリを実行時に読み込みます。

`activate-host-ros-bridge.bash`は内部で`../work-host/ros2/activate.bash`を読み込みます。これにより、ROS 2 package、Python package、Python接続モジュール、Endpoint共有ライブラリが同じ端末から参照可能になります。利用者が`PYTHONPATH`や`LD_LIBRARY_PATH`を個別に設定する必要はありません。

## 4. ROS 2 topicから箱庭Runtimeまでのデータ経路

Bridge起動時に渡す`binding.json`が、ROS 2 topicとPDUの対応、およびROS 2側Endpoint設定を指定します。

```text
ROS 2 node
  `/joint_trajectory` または `/pdu/joint_states`
        ⇅
hakoniwa_pdu_ros bridge
        ⇅  ros/binding.json
ROS 2側Endpoint
        ⇅  TCP
Host側PDU Bridge
        ⇅  SHM
箱庭Runtime
```

ROS 2側Bridgeは次の設定を参照します。

```text
ros/binding.json
  └── endpoint_config
      └── endpoint/docker-tcp.json
          └── comm/tcp-client.json
```

Host側PDU Bridgeは次の設定を参照し、TCPと箱庭共有メモリを中継します。

```text
bridge/bridge.json
  └── endpoint/endpoint_container.json
      ├── endpoint/host-tcp.json → comm/tcp-server.json
      └── endpoint/host-shm.json → comm/shm.json
```

したがって、ROS 2実行ファイルそのものへロボット固有の接続先を埋め込んでいません。Recipeが生成した`binding.json`とEndpoint設定を差し替えることで、同じBridge実行ファイルを別のRobot Modelや接続構成にも使用できます。

## 5. 利用者が実行する範囲

ROS 2 Bridge端末では、configureで生成されたprofileを読み込み、Bridgeを起動します。

```bash
source ../work-host/profiles/activate-host-ros-bridge.bash
ros2 run hakoniwa_pdu_ros bridge --config "$HAKONIWA_ROS_BINDING"
```

`HAKONIWA_ROS_BINDING`はprofile内で生成済み`ros/binding.json`へ設定されます。利用者がEndpoint共有ライブラリやCFFI moduleの場所を指定する必要はありません。

構成が揃っているかは、手動で各ライブラリを調べるのではなくdoctorで確認します。

```bash
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor
```

付属サンプルと独自ROS 2 nodeのbuild方法は[独自ROS 2 nodeの作成とbuild](../procedures/ros2/custom-nodes.md)を参照してください。
