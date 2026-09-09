# docker-onlyセットアップ

Nova5 Runtime、MuJoCo、箱庭コア、TCP Bridge、ROS 2 Bridge、monitor、controlを、`docker/run.bash`で起動する同じ1つのUbuntu Container内で実行します。HostのFoundationやROS 2は使用しません。

## 1. Hostの前提とclone

HostにはGitとDocker EngineまたはDocker Desktopが必要です。[共通セットアップ](setup.md)に従い、空のcheckout用workspaceへBusiness Packと本リポジトリをcloneしてください。

```bash
mkdir -p ~/hakoniwa-robot-arm-workspace
cd ~/hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git

cd hakoniwa-robot-arm
docker --version
bash docker/create-docker-image.bash jazzy
```

imageとContainerはHostのnative architectureを使用します。Apple Silicon macOSではarm64となり、amd64 emulationは使用しません。

## 2. Viewerの選択

native Linux HostでViewerを使用する場合は、HostのX11 `DISPLAY`をContainerへ渡します。Containerがrootで動く既定構成では、必要に応じてHost側で接続を許可します。

```bash
echo "$DISPLAY"
xhost +si:localuser:root
export HAKONIWA_DOCKER_GUI=on
```

macOS Docker Desktop、CI、画面のない環境ではViewerを使用しません。XQuartzは不要です。

```bash
export HAKONIWA_DOCKER_GUI=off
```

## 3. 1つのContainerを起動

Hostの本リポジトリルートで実行します。

```bash
cd "$HOME/hakoniwa-robot-arm-workspace/hakoniwa-robot-arm"
export HAKONIWA_DOCKER_WORK_DIR=/workspace/work-docker-nova5-jazzy
bash docker/run.bash jazzy
```

標準外配置または改名したComposerを使う場合は、`run.bash`より前に`HAKONIWA_COMPOSER`を設定します。

ContainerとHostから見える生成先は次のとおりです。

```text
箱庭work:
  Container  /workspace/work-docker-nova5-jazzy
  Host       ~/hakoniwa-robot-arm-workspace/work-docker-nova5-jazzy

ROS 2 work:
  Container  /workspace/ros2-work-jazzy
  Host       ~/hakoniwa-robot-arm-workspace/ros2-work-jazzy
```

箱庭コアの`foundation/runtime/mmap`だけはContainer内tmpfsです。Docker Desktopのbind mountを介したmmap／file lockの不整合を避けるためで、Container終了時に破棄されます。他の生成物はHostに残ります。

## 4. Container内のFoundationとRecipe依存

`run.bash`で開いたContainer shellで実行します。

```bash
cd "$HAKONIWA_COMPOSER"
python3.12 tools/workspace.py enter --workdir "$HAKONIWA_WORK_DIR"
```

以降は、同じContainer内の`(hako)` shellで実行します。

```bash
python3.12 tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
python3.12 tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
```

## 5. Nova5 Model Forge

同じ`(hako)` shellで実行します。

```bash
python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python "$ARM_PACK/tools/recipe/nova5.py" forge

test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

次は、Containerを終了せず[docker-onlyビルド](build-docker-only.md)へ進んでください。

