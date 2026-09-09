# host-onlyセットアップ

Nova5 RuntimeをHost上で実行します。箱庭シミュレーション単体はmacOSまたはUbuntuで実行できます。ROS 2連携までHostだけで完結させる場合は、ROS 2 HumbleまたはJazzyを導入したUbuntuを使用します。Dockerは使用しません。

## 1. 前提

[トップREADMEの前提ソフトウェア](../README.md#前提ソフトウェア)と[共通セットアップ](setup.md)を確認し、2つのリポジトリをcloneしてください。

Ubuntu 24.04／ROS 2 Jazzyで必要となるHostパッケージの例です。

```bash
sudo apt update
sudo apt install -y \
  git ruby python3.12 python3.12-venv \
  build-essential cmake libboost-dev libglfw3 libopengl0

test -f /opt/ros/jazzy/setup.bash
python3.12 --version
```

ROS 2を使わず箱庭シミュレーション単体だけを実行する場合、ROS 2のインストールと`/opt/ros/...`の確認は不要です。

## 2. Host workとWorkspace

Host用の生成物を置く新しいディレクトリを選び、Business PackのWorkspaceへ入ります。

```bash
export CHECKOUT_ROOT="$HOME/hakoniwa-robot-arm-workspace"
export ARM_PACK="$CHECKOUT_ROOT/hakoniwa-robot-arm"
export NOVA5_HOST_WORK="$CHECKOUT_ROOT/work-host-nova5"

cd "$CHECKOUT_ROOT/hakoniwa-business-pack"
python3.12 tools/workspace.py enter --workdir "$NOVA5_HOST_WORK"
```

以降のこのページのコマンドは、プロンプトに`(hako)`が付いた箱庭Workspaceで実行します。`enter`に指定したパスは`HAKONIWA_WORK_DIR`へ設定されます。

## 3. FoundationとRecipe依存

最初に予定を確認してから、Runtime Recipeを構築します。

```bash
python3.12 tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
```

Foundationと各Recipe dependencyが`SATISFIED`になり、Workspace doctorが`[OK]`を表示することを確認します。

## 4. Nova5 Model Forge

Forge用の依存とPythonパッケージを準備し、Nova5モデルを生成します。

```bash
python tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python "$ARM_PACK/tools/recipe/nova5.py" forge

test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

詳細は[Nova5 Model Forge](model-forge.md)を参照してください。

## 5. ROS 2側の通常shell

ROS 2連携を利用する場合だけ、箱庭Workspaceへ入っていない別のHost terminalを開き、次を設定します。Jazzyの例です。

```bash
source /opt/ros/jazzy/setup.bash
export CHECKOUT_ROOT="$HOME/hakoniwa-robot-arm-workspace"
export ARM_PACK="$CHECKOUT_ROOT/hakoniwa-robot-arm"
export HAKONIWA_WORK_DIR="$CHECKOUT_ROOT/work-host-nova5"
export HAKONIWA_ROS2_WS="$CHECKOUT_ROOT/ros2-work-host-jazzy"
```

箱庭WorkspaceとROS 2 workspaceは共有しません。これらの値は、後続のROS 2用terminalでも同じ値を使用します。

次は[host-onlyビルド](build-host-only.md)へ進んでください。

