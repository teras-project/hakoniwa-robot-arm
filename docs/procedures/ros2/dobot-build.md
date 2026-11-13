# Dobot 仮想サービスの共通ビルド手順（Linux / macOS）

[host-ros2](../host-ros2/build.md)、[host+docker](../host-docker/build.md)、[docker-only](../docker-only/build.md)の各ページで端末・`DOBOT_WORK`・接続先を決めてから、**各ページで指定された端末で**手順1 → 2 → 3の順に実行します。1・2は ROS 端末、3は Native 端末へ切り替えて実行します。**ROS 端末は Ubuntu（Host または Container）の Bash、Native 端末は箱庭 Workspace の Bash** です。host+docker の Native 端末は Host 側の `host-hako` です。両方とも `hakoniwa-robot-arm` のルートで実行します。`DOBOT_WORK` は両端末から同じ生成物を見られるディレクトリの絶対パスにします。`ROS_DISTRO` は `jazzy` または `humble` です。Container と Host では同じディレクトリでも絶対パスが異なるため、各端末で指定し直します。Windows native Host にはこの Native ビルドを適用できません。

Ubuntu 22.04／Humble の Dobot 経路は、現行の RPC が Python 3.12 以上を要求し、ROS 側の Python 3.10 でビルドできません（[Issue #14](https://github.com/teras-project/hakoniwa-robot-arm/issues/14)）。Foundation 側の Python 3.12 と ROS 側の Python 3.10 は分離したまま、対応版の導入と結合検証を待ちます。

## 1. ROS 端末：公式ソース、メッセージ、RPC、PDU 型

Dobot 公式ソースは**変更せず**に取得します。既存 checkout がある場合は clone / checkout 行を省略し、手元の対応版であることを確認します。箱庭で公式 `dobot_demo/demo.py` を動かすため、メッセージとデモの2パッケージだけをビルドします。実機 driver は Ubuntu host-ros2 の[実機追加手順](../host-ros2/real.md)でビルドします。先に ROS の profile または `/opt/ros/$ROS_DISTRO/setup.bash` を source してください。

```bash
mkdir -p "$DOBOT_WORK/dobot-deps"
git clone https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4.git \
  "$DOBOT_WORK/dobot-deps/DOBOT_6Axis_ROS2_V4"
export DOBOT_SRC="$DOBOT_WORK/dobot-deps/DOBOT_6Axis_ROS2_V4"
git -C "$DOBOT_SRC" checkout --detach 89d47c66a6e0c654dbbe6819f2291132ad0ce979

colcon --log-base "$DOBOT_WORK/dobot-ros/log" build \
  --base-paths "$DOBOT_SRC/dobot_msgs_v4" "$DOBOT_SRC/dobot_demo" \
  --build-base "$DOBOT_WORK/dobot-ros/build" \
  --install-base "$DOBOT_WORK/dobot-ros/install" \
  --symlink-install --packages-select dobot_msgs_v4 dobot_demo
source "$DOBOT_WORK/dobot-ros/install/setup.bash"

/usr/bin/python3 tools/recipe/ros2_workspace.py build \
  --workdir "$DOBOT_WORK/ros2" --ros-distro "$ROS_DISTRO" --with-rpc
source "$DOBOT_WORK/ros2/activate.bash"
/usr/bin/python3 tools/recipe/ros2_workspace.py doctor --workdir "$DOBOT_WORK/ros2"
source "$DOBOT_WORK/dobot-ros/install/setup.bash"
python3 tools/dobot/generate_types.py \
  --dobot-src "$DOBOT_SRC" \
  --registry ../hakoniwa-pdu-registry \
  --output "$DOBOT_WORK/dobot-types"
source "$DOBOT_WORK/dobot-types/activate.bash"

colcon --log-base "$DOBOT_WORK/dobot-apps/log" build \
  --base-paths ros2_packages/hakoniwa_dobot ros2_packages/hakoniwa_arm_samples \
  --build-base "$DOBOT_WORK/dobot-apps/build" \
  --install-base "$DOBOT_WORK/dobot-apps/install" \
  --symlink-install --packages-select hakoniwa_dobot hakoniwa_arm_samples
source "$DOBOT_WORK/dobot-apps/install/setup.bash"
ros2 pkg executables hakoniwa_dobot
ros2 pkg executables dobot_demo
```

公式ソースは[対応リビジョン](../../../tools/dobot/versions.json)の commit に固定しています。既存 checkout を利用する場合は clone / checkout 行を飛ばし、`.srv` の互換性を確認してください。既存の PDU-ROS checkout が対応リビジョンを含まない場合、`ros2_workspace.py` は停止し、checkout を自動で変更しません。`--with-rpc` は隣接する `hakoniwa-pdu-rpc` と `hakoniwa-pdu-registry` がなければ取得し、既存の checkout は切り替えません。`dobot-types` は実機 driver 用ではなく、ROS サービスと箱庭 Native Asset 間の PDU-RPC 用です。型生成は公式 `.srv` をコピーして生成領域に出力し、公式ソースと registry は編集しません。`hakoniwa_dobot configure`、`hakoniwa_arm_samples control`、`dobot_demo demo` が表示されなければ次へ進まないでください。

## 2. ROS 端末：サービスと topic の binding

ROS 端末で同じ環境を source した状態で実行します。`DOBOT_RPC_ADDRESS` は **ROS 端末から Native Asset の Host へ接続する宛先**です。host-ros2 / docker-only / Linux host network は `127.0.0.1`、macOS Docker Desktop は `host.docker.internal` を使用します。サーバーは TCP 54020 を使用するため、macOS の Host Firewall などでも到達できる必要があります。

```bash
ros2 run hakoniwa_dobot configure \
  --output "$DOBOT_WORK/dobot-services" \
  --offset-dir "$DOBOT_WORK/dobot-types/pdu/offset" \
  --address "$DOBOT_RPC_ADDRESS"
ls -l "$DOBOT_WORK/dobot-services/dobot-services.json" \
  "$DOBOT_WORK/dobot-services/rpc/rpc-server-services.json" \
  "$DOBOT_WORK/dobot-services/rpc/endpoints/dobot_virtual.json"
```

`dobot-services.json` は公式サービスと PDU-RPC の対応、既存 `ros2-tcp/ros/binding.json` は仮想 JointState の topic binding です。`dobot.launch.py` に **両方**を渡します。後者を省略すると `/joint_states_robot` が得られません。

## 3. Native 端末：RPC を Foundation に接続し専用 Asset を作る

箱庭 Workspace の `python` が使える Native 端末で、各構成の `DOBOT_WORK` を設定します。ROS と Native の両生成物が見えていることを確認してください。`HAKONIWA_FOUNDATION_PREFIX` は `DOBOT_WORK/foundation/install` を使用します（`nova5.py build` が使用した Foundation prefix と同一）。Runtime と PDU-ROS は Dobot 対応版を使用します（[対応リビジョン](../../../tools/dobot/versions.json)）。古い checkout で CMake が失敗した場合、勝手に他の checkout を切り替えず対応版を準備してください。

```bash
export HAKONIWA_FOUNDATION_PREFIX="$DOBOT_WORK/foundation/install"
test -d "$HAKONIWA_FOUNDATION_PREFIX/include"
test -f "$DOBOT_WORK/dobot-types/pdu/types/dobot_msgs_v4_msgs/pdu_cpptype_conv_ServoJRequestPacket.hpp"
cmake -S ../hakoniwa-pdu-rpc -B "$DOBOT_WORK/dobot-rpc-build" \
  -DHAKO_PDU_ENDPOINT_PREFIX="$HAKONIWA_FOUNDATION_PREFIX" \
  -DHAKONIWA_PDU_REGISTRY_DIR="$PWD/../hakoniwa-pdu-registry" \
  -DCMAKE_INSTALL_PREFIX="$DOBOT_WORK/dobot-rpc-native" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DHAKO_PDU_RPC_BUILD_TESTS=OFF -DHAKO_PDU_RPC_BUILD_EXAMPLES=OFF
cmake --build "$DOBOT_WORK/dobot-rpc-build" --parallel 2
cmake --install "$DOBOT_WORK/dobot-rpc-build"

cmake -S . -B "$DOBOT_WORK/recipes/nova5-joint-trajectory-control/build" \
  -DHAKO_ARM_ENABLE_DOBOT=ON \
  -DHAKO_DOBOT_PDU_DIR="$DOBOT_WORK/dobot-types" \
  -Dhakoniwa_pdu_rpc_DIR="$DOBOT_WORK/dobot-rpc-native/lib/cmake/hakoniwa_pdu_rpc"
cmake --build "$DOBOT_WORK/recipes/nova5-joint-trajectory-control/build" \
  --target robot-arm-dobot-asset --parallel 2
```

各コマンドがエラーなく終了し、次の確認で専用 Asset が表示されてから Launcher を切り替えてください。リンクなどに失敗した場合、`adapt_launcher.py` は実行しません。

```bash
ls -l "$DOBOT_WORK/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-dobot-asset"
```

```bash
python3 tools/dobot/adapt_launcher.py \
  --launcher "$DOBOT_WORK/recipes/nova5-joint-trajectory-control/config/launcher.json" \
  --binary "$DOBOT_WORK/recipes/nova5-joint-trajectory-control/build/bin/robot-arm-dobot-asset" \
  --services "$DOBOT_WORK/dobot-services/rpc/rpc-server-services.json" \
  --endpoint "$DOBOT_WORK/dobot-services/rpc/endpoints/dobot_virtual.json"
```

`launcher.pre-dobot.json` に元設定が保存されます。`nova5.py configure` を再実行した場合は、Runtime を止めてから **再度 adapt_launcher.py** を実行してください。`robot-arm-hakoniwa-asset` の旧 topic 指令を起動しません。
