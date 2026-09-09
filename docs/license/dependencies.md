# 依存コンポーネントのライセンス

この文書は、本リポジトリのForge、Foundation、Robot Arm Runtime、ROS 2 topic bridgeで利用する主要なリポジトリと外部OSSを整理したものです。

## Hakoniwa OSS

| Component | 主な役割 | 利用経路 | ライセンス確認結果 | revision／versionの管理元 |
| --- | --- | --- | --- | --- |
| [`hakoniwa-business-pack`](https://github.com/hakoniwalab/hakoniwa-business-pack) | Composer、Workspace、Foundation、Recipe | setupと全実行環境 | MIT | Runtime Recipeでは`main`。実際の構築結果は選択したComposerとFoundation receiptで確認 |
| [`hakoniwa-core-pro`](https://github.com/hakoniwalab/hakoniwa-core-pro) | Core、SHM、`hako-cmd`、`hakopy` | Foundation | MIT | Business PackのFoundation解決結果 |
| [`hakoniwa-core-cpp`](https://github.com/toppers/hakoniwa-core-cpp) | Core C/C++実装 | `hakoniwa-core-pro`のsubmodule | TOPPERS License | `hakoniwa-core-pro`が固定するsubmodule revision |
| [`hakoniwa-pdu-registry`](https://github.com/hakoniwalab/hakoniwa-pdu-registry) | PDU型とschema | `hakoniwa-core-pro`等のsubmodule | MIT | 親リポジトリが固定するsubmodule revision |
| [`hakoniwa-pdu-endpoint`](https://github.com/hakoniwalab/hakoniwa-pdu-endpoint) | SHM／TCP Endpoint、Python binding | FoundationとROS 2 workspace | MIT | Foundation receipt。ROS 2側は`tools/recipe/ros2_workspace.py`の`SOURCES` |
| [`hakoniwa-pdu-bridge-core`](https://github.com/hakoniwalab/hakoniwa-pdu-bridge-core) | SHMとTCPのBridge | Foundation | MIT | Business PackのFoundation解決結果 |
| [`hakoniwa-pdu-python`](https://github.com/hakoniwalab/hakoniwa-pdu-python) | Python PDU API、Launcher | FoundationとROS 2 workspace | MIT | Runtime Recipeは`>=1.6.5`、ROS 2 Recipeは`hakoniwa-pdu==1.6.9` |
| [`hakoniwa-robot-runtime`](https://github.com/hakoniwalab/hakoniwa-robot-runtime) | Manifest駆動Robot Runtime | C++ build | MIT | Nova5 Recipeの固定revision |
| [`hakoniwa-mujoco-robots`](https://github.com/hakoniwalab/hakoniwa-mujoco-robots) | MuJoCo共通実装とViewer | ForgeとC++ build | MIT | 各Model／Runtime Recipeの固定revision |
| [`hakoniwa-mbody-registry`](https://github.com/hakoniwalab/hakoniwa-mbody-registry) | URDF／MJCF変換ツール | Model Forge | MIT | Model Forge Recipeの固定revision |
| [`hakoniwa-pdu-ros`](https://github.com/hakoniwalab/hakoniwa-pdu-ros) | ROS 2 topicとPDUの変換 | ROS 2 workspace | MIT | `tools/recipe/ros2_workspace.py`の`SOURCES` |

表中のHakoniwa OSSには、記載したライセンスが適用されます。配布時に必要な著作権表示とライセンス本文は、実際に配布する各コンポーネントの対象revisionを正本としてください。

`hakoniwa-pdu-rpc`は`hakoniwa-pdu-ros`のService／Action機能で利用されますが、現在のNova5受入経路である`JointTrajectory`／`JointState`のtopic通信には使用せず、ROS 2 workspace Recipeもインストールしません。Service／Actionを追加する場合は、同リポジトリのMIT Licenseを含めて依存台帳を更新します。

## 主要な外部OSS

| Component | 主な役割 | 確認したライセンス | versionの管理元 |
| --- | --- | --- | --- |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | 物理シミュレーション | Apache License 2.0 | `hakoniwa-mujoco-robots/MUJOCO_VERSION.txt`。Nova5 Forge Python packageは`3.9.0` |
| [PyYAML](https://github.com/yaml/pyyaml) | Forge設定のYAML読込み | MIT | 各`recipes/<robot>/model-forge-requirements.txt` |
| [trimesh](https://github.com/mikedh/trimesh) | FR5のDAE mesh変換 | MIT | `recipes/fr5/model-forge-requirements.txt` |
| [pycollada](https://github.com/pycollada/pycollada) | trimeshのCOLLADA読込み | BSD | `recipes/fr5/model-forge-requirements.txt` |
| [nlohmann/json](https://github.com/nlohmann/json) | C++ JSON処理 | MIT | 利用元CMake projectの解決結果 |
| ROS 2とROS message packages | ROS 2実行環境、`JointTrajectory`、`JointState` | packageごとに異なる | Docker base imageと各ROS package metadata |
| Python build／FFI packages | `setuptools`、`wheel`、`cffi` | packageごとに異なる | `tools/recipe/ros2_workspace.py`のpip指定とインストール結果 |

Docker imageにはUbuntu／ROS 2のOS packageが追加されます。再配布するimageの完全なThird-party noticeを作る場合は、この概要表だけでなく、対象imageとPython環境から確定したpackage inventoryを生成してください。

## revisionの確認場所

- Model ForgeとRuntimeの固定revision: `recipes/<robot>/*.yaml`
- ROS 2側の固定revision: `tools/recipe/ros2_workspace.py`
- Foundationの実構築revision: `$HAKONIWA_WORK_DIR/foundation/install/share/hakoniwa/receipts/`
- Python packageの実version: 各workのPython環境で`python -m pip freeze`
