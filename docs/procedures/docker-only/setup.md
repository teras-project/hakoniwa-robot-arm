# docker-onlyセットアップ

Nova5 Runtime、MuJoCo、箱庭Core、TCP Bridge、ROS 2 Bridge、monitor、controlを同じUbuntu Container内で実行するための準備手順です。HostのFoundationやROS 2は使用しません。

## 1. Hostの前提とDocker imageを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 利用者が選んだcheckout用ディレクトリから開始 |
| この作業の入力成果物 | GitとDocker Engine／Docker Desktopを使用できるHost |
| この作業のゴール | 2リポジトリが兄弟配置され、`hakoniwa-arm-dev:jazzy` imageが生成される。 |

```bash
mkdir -p hakoniwa-robot-arm-workspace
cd hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git

cd hakoniwa-robot-arm
docker --version
bash docker/create-docker-image.bash jazzy
docker image inspect hakoniwa-arm-dev:jazzy --format '{{.RepoTags}}'
```

Dockerのversionと`hakoniwa-arm-dev:jazzy`が表示されればOKです。Humbleでは`jazzy`を`humble`へ置き換えます。imageとContainerはHostのnative architectureを使用し、Apple Siliconではarm64として動作します。

## 2. Containerを起動する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 前段の通常Host terminal。このコマンド後のContainer shellを維持する。 |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 作成済みDocker imageと、兄弟配置された2リポジトリ |
| この作業のゴール | Hostのcheckout用ディレクトリを`/workspace`へmountしたContainerが起動する。 |

macOS Docker Desktop、CI、画面のない環境ではheadless用として起動します。

```bash
HAKONIWA_DOCKER_GUI=off bash docker/run.bash jazzy
```

Linux HostでX11 Viewerを使用する場合だけ、Host側で接続を許可してGUIを有効にします。

```bash
xhost +si:localuser:root
HAKONIWA_DOCKER_GUI=on bash docker/run.bash jazzy
```

起動ログに次が表示され、Container shellが開けばOKです。

```text
Mount: ... -> /workspace
Container: hakoniwa-arm-dev-jazzy; ...
Workdir: /workspace/work-docker-jazzy; Foundation mmap: tmpfs
```

このshellを終了するとContainerが削除されるため、以後`docker-hako`端末として最後まで開いたままにします。

標準の生成先は次です。

```text
箱庭work:     /workspace/work-docker-jazzy
ROS 2成果物: /workspace/ros2-work-jazzy
```

どちらもHostへmountしたcheckout用ディレクトリ内に残ります。ただし、`foundation/runtime/mmap`だけはContainer内tmpfsであり、Container終了時に破棄されます。

## 3. 箱庭Workspaceへ入る

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako` |
| 実行ディレクトリ | `run.bash`が開いたContainer内のComposer repository root |
| この作業の入力成果物 | `run.bash`が設定した`HAKONIWA_COMPOSER`と`HAKONIWA_WORK_DIR` |
| この作業のゴール | Container内でFoundation、Forge、Runtimeを操作する箱庭Workspaceが開く。 |

```bash
python3.12 tools/workspace.py enter --workdir "$HAKONIWA_WORK_DIR"
```

child shellのpromptに`(hako)`が付き、`pwd`の末尾がComposer repository名ならOKです。

## 4. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内のComposer repository root |
| この作業の入力成果物 | 前段で開いた箱庭Workspaceと、mount済みRobot Arm repository |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が準備され、doctorが成功する。 |

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

`plan`に`Recipe plan:`が表示されれば、構築予定を確認できています。初回の`plan`では、まだ存在しないFoundation成果物が`MISSING`と表示されても正常です。`configure`後に実行する2つのdoctorで`[OK]`と`SATISFIED`が表示され、ここでは`[NG]`、`MISSING`、`error:`がなければOKです。

## 5. Nova5 MJCFを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内のComposer repository rootから開始 |
| この作業の入力成果物 | Nova5 Model Forge Recipeと、準備済みFoundation |
| この作業のゴール | `$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml`が生成される。 |

```bash
python tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml

cd ../hakoniwa-robot-arm
python tools/recipe/nova5.py forge
ls -l "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

最後の`ls`で`nova5.contact.xml`が表示されればOKです。

次は、Containerを終了せず[docker-onlyビルド](build.md)へ進んでください。
