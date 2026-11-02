# Dobot 公式 ROS 2 API で Nova5 実機と箱庭を操作する初版

ユーザーは `dobot_msgs_v4/srv/*` をそのまま使います．実機は公式
`dobot_bringup_v4_node`，箱庭は Service Bridge → TCP/PDU-RPC → MuJoCo の経路です．
従来作成した `dobot_arm_samples bridge` はこの経路では起動しません．

この初版の到達目標は ServoJ による関節移動，途中停止，実測角度の観測と，同じ要求の実機・箱庭への配送です．
MoveIt の実行試験と完全な Dobot API 互換は次段階です．

## 実装範囲

| API | 箱庭の処理 |
|---|---|
| RequestControl | すでに TCP 相当モードとして受付成功 |
| EnableRobot | 現在姿勢を保持して動作許可 |
| DisableRobot | 軌道破棄・現在姿勢保持・動作指令禁止 |
| ServoJ | J1..J6 の絶対角 deg，`t=秒` を受理し，物理時刻で線形補間 |
| Stop | 軌道を破棄し，その時点の実測姿勢を保持．Asset 自体は終了しない |
| GetAngle | MuJoCo の現在関節角を deg の `{a,b,c,d,e,f}` 形式で返す |
| RobotMode | 無効4，待機5，動作中7 |
| ClearError | この初版では受付成功（実機のアラーム全体を再現しない） |
| GetErrorID | この初版では正常時の `{[]}` を返す |

`ServoJ` は受理応答を直ちに返し，目標到達まで待ちません．
`t` の対応範囲は0.004..120秒，省略時0.1秒です．その他の `param_value` は拒否します．
範囲外角度/NaN/Inf/不正なパラメータも拒否します．未有効時は `res=-3`，不正値は `res=-1`．
これらは初版の対応範囲のエラーであり，Dobot の全エラー体系の再現ではありません．

箱庭の内部角度と JointState は rad です．停止・無効時の姿勢保持はブレーキの近似で，
実機のブレーキ・衝突安全機能や加減速制約を再現するものではありません．

## 変更するリポジトリ

- `hakoniwa-robot-arm`: C++ サービス処理・専用 Asset，ROS launch / 同時配送，設定生成ツール．
- `hakoniwa-robot-runtime`: `ManifestFactoryConfig.configure_resources` という起動前の構成フック．
  専用 Asset が既存 Plant/Endpoint を使って Runtime を構成できるようにします．
  フック指定時は既定の入力購読を作らず，破棄した Controller へのコールバックを残しません．
- `hakoniwa-pdu-ros`: Service / Topic Bridge の CLI が ROS remapping 引数を受け付けるための修正．
- Dobot リポジトリは変更しません．

同梱パッチの基準は `tools/dobot/versions.json` を参照してください．
Runtime と PDU-ROS のパッチは各リポジトリで `git apply --check` 後に適用します．
ローカルで改修している場合は差分を確認して取り込んでください．

## 導入手順

以下は既存 Nova5 の host-ros2 環境が動いている前提です．
既存の Runtime / ドライバ / 独自 bridge は停止してから切り替えます．
`dobot_ws` とリポジトリのパスは手元に合わせてください．

### 1. ROS 側に PDU-RPC を準備

通常の ROS 端末（Foundation の activate をしていない端末）で:

```bash
cd ~/teras/hakoniwa-robot-arm
source /opt/ros/jazzy/setup.bash
source ~/teras/dobot_ws/install/setup.bash

python3 tools/recipe/ros2_workspace.py build \
  --workdir ../work-host/ros2 --ros-distro jazzy --with-rpc
source ../work-host/ros2/activate.bash
```

`--with-rpc` は opt-in です．PDU-RPC と registry は隣接 checkout を利用し，
無ければ取得します．既存 checkout のブランチやコミットは切り替えません．
Endpoint の共有ライブラリと RPC を ROS ワークスペース内でビルドします．
このオプションでは `hakoniwa-pdu==1.7.0` を利用します．

公式 `.srv` から PDU の C++ / Python / offset を生成します．
`DOBOT_SRC` は公式ソースがあるディレクトリに設定してください．

```bash
DOBOT_SRC=~/teras/dobot_ws/src/DOBOT_6Axis_ROS2_V4
python3 tools/dobot/generate_types.py \
  --dobot-src "$DOBOT_SRC" \
  --registry ../hakoniwa-pdu-registry \
  --output ../work-host/dobot-types
source ../work-host/dobot-types/activate.bash
```

生成物は専用 overlay に出力し，公式 `.srv` や registry 本体を編集しません．
C++ の `string[]` 変換で既存 generator が使うヘルパー名の不整合は，
`apps/dobot/backend.hpp` 内の小さな互換関数で吸収しています．

### 2. ROS パッケージとサービス構成を準備

```bash
cd ~/teras/dobot_ws
colcon build --symlink-install \
  --base-paths ~/teras/hakoniwa-robot-arm/ros2_packages/hakoniwa_dobot \
  --packages-select hakoniwa_dobot
source install/setup.bash

ros2 run hakoniwa_dobot configure \
  --output ~/teras/work-host/dobot-services \
  --offset-dir "$HAKO_DOBOT_PDU_DIR/pdu/offset"
```

生成先には次が入ります．

- `dobot-services.json`: ROS service と PDU-RPC の対応．既定の ROS 接続先は `/hakoniwa/...`．
- `rpc/rpc-server-services.json`: Native Asset 用のサービス定義．
- `rpc/endpoints/dobot_virtual.json`: Native Asset の TCP Mux server 用 Endpoint．
- `rpc/endpoints.json`: ROS Bridge 側のクライアント用 Endpoint collection．

サーバーは既定 TCP 54020 を使います．別ホストは configure の `--address`，別ポートは `--port` を指定します．
RPC の応答期限は2秒です．TCP の無通信タイムアウトを0にして，待機中の正常接続を切断しないようにしています．

### 3. Native Asset をビルド

Runtime のパッチを適用した checkout が `HAKONIWA_ROBOT_RUNTIME_ROOT` で選ばれていることを確認します．
Foundation 側には，PDU-RPC を同じ Endpoint インストールに対してビルドして準備します．
Foundation の Endpoint が CMake パッケージを公開する版である必要があります．

```bash
# Foundation のビルド環境で実行．既存の Foundation prefix に合わせる．
cmake -S ../hakoniwa-pdu-rpc -B ../work-host/dobot-rpc-build \
  -DHAKO_PDU_ENDPOINT_PREFIX="$HAKONIWA_FOUNDATION_PREFIX" \
  -DHAKONIWA_PDU_REGISTRY_DIR="$PWD/../hakoniwa-pdu-registry" \
  -DCMAKE_INSTALL_PREFIX="$PWD/../work-host/dobot-rpc-native" \
  -DHAKO_PDU_RPC_BUILD_TESTS=OFF -DHAKO_PDU_RPC_BUILD_EXAMPLES=OFF
cmake --build ../work-host/dobot-rpc-build --parallel 2
cmake --install ../work-host/dobot-rpc-build
```

既存 Nova5 build ディレクトリの CMake 設定に追加します．既存キャッシュの
Foundation/Runtime/MuJoCo のパスは引き継ぎます．

```bash
cmake -S . -B ../work-host/recipes/nova5-joint-trajectory-control/build \
  -DHAKO_ARM_ENABLE_DOBOT=ON \
  -DHAKO_DOBOT_PDU_DIR="$PWD/../work-host/dobot-types" \
  -Dhakoniwa_pdu_rpc_DIR="$PWD/../work-host/dobot-rpc-native/lib/cmake/hakoniwa_pdu_rpc"
cmake --build ../work-host/recipes/nova5-joint-trajectory-control/build \
  --target robot-arm-dobot-asset --parallel 2
```

このビルドは opt-in で，従来の `robot-arm-hakoniwa-asset` も残ります．

### 4. 既存 Launcher を切り替える

通常の `nova5.py configure --ros2-tcp` 済みの `launcher.json` を対象にします．
次のツールは元設定を `launcher.pre-dobot.json` に保存し，plant の実行ファイルと引数を変更します．
既存の Host TCP Bridge は維持し，旧軌道送信/ゲームパッドは起動対象から外します．
新 Asset は専用サービス経由の指令だけを使います．

```bash
python3 tools/dobot/adapt_launcher.py \
  --launcher ../work-host/recipes/nova5-joint-trajectory-control/config/launcher.json \
  --binary ../work-host/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-dobot-asset \
  --services ../work-host/dobot-services/rpc/rpc-server-services.json \
  --endpoint ../work-host/dobot-services/rpc/endpoints/dobot_virtual.json
python tools/recipe/nova5.py start
```

通常 configure を再実行した場合は，その後に adapt_launcher を再実行します．
元に戻す場合は Runtime を停止してバックアップを復元します．

### 5. ROS サービスを起動

各 ROS 端末では ROS，Dobot，ROS Bridge，型 overlay，hakoniwa_dobot の環境を読み込みます．
同じ `ROS_DOMAIN_ID` を使います（箱庭 profile は既定73を設定するので注意）．

箱庭のみの場合:

```bash
ros2 launch hakoniwa_dobot dobot.launch.py backend:=virtual \
  service_binding:=~/teras/work-host/dobot-services/dobot-services.json \
  offset_dir:=~/teras/work-host/dobot-types/pdu/offset \
  rpc_output:=~/teras/work-host/dobot-services/rpc \
  topic_binding:=~/teras/work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

実機のみの場合（Native Asset は不要）:

```bash
ros2 launch hakoniwa_dobot dobot.launch.py backend:=real robot_ip:=192.168.5.1
```

実機と箱庭の場合:

```bash
ros2 launch hakoniwa_dobot dobot.launch.py backend:=both robot_ip:=192.168.5.1 \
  service_binding:=~/teras/work-host/dobot-services/dobot-services.json \
  offset_dir:=~/teras/work-host/dobot-types/pdu/offset \
  rpc_output:=~/teras/work-host/dobot-services/rpc \
  topic_binding:=~/teras/work-host/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json
```

IP は判明済みの実機IPへ変更してください．実機 driver は1つだけ起動します．
ラッパーは公式 executable を公開パラメータで起動し，公式ソースを編集しません．

| backend | ユーザーの API | 実機 API | 箱庭 API | 実測 JointState |
|---|---|---|---|---|
| real | `/dobot_bringup_ros2/srv/*` | 同左 | なし | `/joint_states_robot` |
| virtual | 同上 | なし | 同左 | `/joint_states_robot` |
| both | 同上（router） | `/real/dobot_bringup_ros2/srv/*` | `/hakoniwa/dobot_bringup_ros2/srv/*` | `/real/joint_states_robot` と `/hakoniwa/joint_states_robot` |

`topic_binding` を省略すると関節状態 topic の接続は別起動になります．
状態の PDU 出力自体は Native Asset が継続します．

### 6. 同じ CLI で操作

```bash
ros2 service call /dobot_bringup_ros2/srv/EnableRobot dobot_msgs_v4/srv/EnableRobot '{}'
ros2 service call /dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 service call /dobot_bringup_ros2/srv/RobotMode dobot_msgs_v4/srv/RobotMode '{}'
```

付属の小動作サンプルも，公式 GetAngle / RobotMode / ServoJ だけを使います．
現在角度を読み，J1 だけ +5°の目標を作ります．残り5軸をゼロで上書きしません．

```bash
# 読み取りと目標表示だけ
ros2 run hakoniwa_dobot jog --joint 1 --delta-deg 5 --duration 3
# 既に有効・待機状態であることを確認してから実行
ros2 run hakoniwa_dobot jog --joint 1 --delta-deg 5 --duration 3 --execute
```

サンプルは有効化を自動実行しません．`--execute` は実際に実機へ指令を送る指定です．
同じ指令を繰り返すたび，その時の現在角度からさらに+5°になります．

動作中に別端末から停止:

```bash
ros2 service call /dobot_bringup_ros2/srv/Stop dobot_msgs_v4/srv/Stop '{}'
```

両者の角度比較（both）:

```bash
ros2 service call /real/dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
ros2 service call /hakoniwa/dobot_bringup_ros2/srv/GetAngle dobot_msgs_v4/srv/GetAngle '{}'
```

始動前に実機と箱庭の姿勢を合わせてください．まず箱庭だけの API に対し，実機の現在角度を
目標とする十分長い `ServoJ` を送り，状態を確認する方法で揃えられます．
本実装は初期姿勢を自動変更しません．

## 同時配送の仕様と制限

- 9サービスのうち GetAngle/RobotMode/GetErrorID は実機だけへ問い合わせます．
- 他の6サービスは，同じ Request を実機と箱庭へそれぞれ `call_async()` します．
- ROS 上で両サービスが準備できていることを送信前に確認します．
- 通常の成功応答は実機の内容です．いずれかが失敗した場合は失敗を返します．
- 結果は `dobot_twin/status` に出します．timeout 時には結果不明であることをログへ出します．
- 原子的な同時実行・ロールバックはありません．実機だけが受理した場合もあり得ます．
  別プロセス・RPC を通るので開始時刻の一致も保証しません．
- 停止は通常の Dobot Stop 要求です．通信経路が使えない場合の非常停止の代わりにはなりません．
- 初版は1台の Nova5 とその箱庭モデル向け．9サービス以外の公式サービスは同時配送の対象外です．
- Native Asset のポーズ変更・物理計算は simulation thread で行います．
- Viewer pause 中は物理ステップが止まるため，サービスも期限切れになる場合があります．
- 正常/動作中の簡易状態を実装し，Dobot 全アラーム，安全機構，I/O，MovJ/MovL，運動学，
  任意ツール/負荷モデル，ServoJ のベンダー固有 gain 等は未対応です．
- MoveIt は公式 action_move_server をこのAPIへ接続できる構造ですが，まだ実行検証していません．
  both では公式 joint state relay の入力を実機側へ remap し，箱庭の状態を混ぜない設定が必要です．

## 検証済みと未検証

検証済み:

- 公式 .srv から9サービスの PDU型・offset を生成．C++ converter のコンパイル．
- 本番 `ServoController` / `RpcBoundary` と本物の MuJoCo を使う headless 試験．
  TCP/PDU-RPC 経由で無効時の拒否，5°移動，途中停止，姿勢保持，次の移動，無効化を確認．
- 実測例: 途中 1.960°，Stop直後 1.963°，0.7秒後 1.965°，次指令で 5.000°．
- C++ の補間・入力検査・取消，Python の設定と配送を試験．
- Native main と Runtime factory 変更の C++ 構文検査．
- 既存の ROS 接続設定/軌道ファイルテスト5件．

未検証:

- この環境には ROS 2 と Foundation がないため，colcon，実ROS launch/CLI，
  完成した Nova5 Asset と Foundation/Launcher の結合，Nova5 の実機同時運転．
- headless 試験は独立した6軸ヒンジモデルを使っており，Nova5 のモデル精度検証ではありません．

Python の試験:

```bash
PYTHONPATH=ros2_packages/hakoniwa_dobot python3 -m pytest -q tools/dobot/test
```

`tools/dobot/native_smoke.cpp` と `test/native_roundtrip.py` は headless TCP試験の本体です．
前者を generated types，Runtime headers，PDU-RPC/Endpoint，MuJoCo に対してビルドし，
後者を generated Python overlay と同じ RPC config で実行します．

Native テストを独立ビルドする場合（Foundation 不要，PDU-RPC/Endpoint の CMake package は必要）:

```bash
python3 -m pip install mujoco
MJROOT="$(python3 -c 'import mujoco; print(mujoco.__path__[0])')"
cmake -S tools/dobot -B /tmp/dobot-native-test \
  -DHAKONIWA_ROBOT_RUNTIME_ROOT="$PWD/../hakoniwa-robot-runtime" \
  -DHAKO_DOBOT_PDU_DIR="$HAKO_DOBOT_PDU_DIR" -DMUJOCO_ROOT="$MJROOT" \
  -DCMAKE_PREFIX_PATH=/path/to/pdu-rpc/install
cmake --build /tmp/dobot-native-test --parallel 2
ctest --test-dir /tmp/dobot-native-test --output-on-failure
python3 tools/dobot/run_native_test.py --server /tmp/dobot-native-test/dobot-native-smoke \
  --config-root ../work-host/dobot-services/rpc --library "$HAKO_PDU_RPC_LIBRARY"
```
