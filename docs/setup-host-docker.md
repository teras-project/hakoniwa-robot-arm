# host+dockerセットアップ

Nova5 RuntimeとMuJoCo ViewerはHost、ROS 2 Bridge、monitor、controlはDocker Containerで実行します。macOSでROS 2を利用する場合の基本構成です。

## 1. 前提

[トップREADMEの前提ソフトウェア](../README.md#前提ソフトウェア)と[共通セットアップ](setup.md)を確認し、2つのリポジトリをcloneしてください。

macOSで必要なHostパッケージの例です。

```bash
brew install git ruby python@3.12 cmake glfw
python3.12 --version
docker --version
```

Ubuntu HostではC/C++ビルド環境、CPython 3.12、CMake、OpenGL／GLFW、Dockerを準備します。ROS 2はContainerで実行するため、HostへのROS 2インストールは不要です。

## 2. Host workとWorkspace

Host用の新しいworkを選び、Business PackのWorkspaceへ入ります。

```bash
export CHECKOUT_ROOT="$HOME/hakoniwa-robot-arm-workspace"
export ARM_PACK="$CHECKOUT_ROOT/hakoniwa-robot-arm"
export NOVA5_HOST_WORK="$CHECKOUT_ROOT/work-host-nova5"

cd "$CHECKOUT_ROOT/hakoniwa-business-pack"
python3.12 tools/workspace.py enter --workdir "$NOVA5_HOST_WORK"
```

以降のHost側コマンドは、プロンプトに`(hako)`が付いたWorkspaceで実行します。

## 3. FoundationとRecipe依存

```bash
python3.12 tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
python3.12 tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
```

FoundationとRecipe dependencyが`SATISFIED`になり、Workspace doctorが`[OK]`を表示することを確認します。

## 4. Nova5 Model Forge

```bash
python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python "$ARM_PACK/tools/recipe/nova5.py" forge

test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

詳細は[Nova5 Model Forge](model-forge.md)を参照してください。

## 5. ROS 2 Docker image

箱庭Workspaceとは別の通常Host terminalで、本リポジトリのルートへ移動してimageを作成します。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
bash docker/create-docker-image.bash jazzy
```

Humbleを使用する場合は`jazzy`を`humble`へ置き換えます。この構成のContainerではViewerを動かさないため、Container起動時は`HAKONIWA_DOCKER_GUI=off`を使用します。

次は[host+dockerビルド](build-host-docker.md)へ進んでください。

