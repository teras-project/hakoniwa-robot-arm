# docker-onlyセットアップ

Nova5 Runtime、MuJoCo、箱庭 Core、TCP Bridge、Dobot Service / topic Bridge、monitor、control を同じ Ubuntu Container 内で実行する準備手順です。実機を使わず、箱庭で公式デモを確認します。Host の Foundation や ROS 2 は使用しません。公式 Dobot ソースとメッセージは[ビルド手順](build.md)で準備します。

手順: [一覧](../README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)

| 端末 | 実行場所・Python環境 |
| --- | --- |
| 通常のHost terminal | checkout、Docker image、Containerの起動。 |
| `docker-hako` | Container内の箱庭Workspace。初回のFoundation構築はCPython 3.12、構築後はFoundationの`python`を使用。 |
| `docker-ros-*` | 同じContainerの別のshell。箱庭Workspaceには入らず、ROS 2専用環境を使用。 |

端末が切り替わるコマンドは単独で実行します。[手順の読み方](../conventions.md#コードブロックと端末の読み方)も参照してください。

## 1. Hostの前提とDocker imageを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 利用者が選んだcheckout用ディレクトリから開始 |
| この作業の入力成果物 | GitとDocker Engine／Docker Desktopを使用できるHost |
| この作業のゴール | 2リポジトリが兄弟配置され、`hakoniwa-arm-dev:jazzy` imageが生成される。 |

checkout用workspaceをまだ作っていない場合だけ、利用者が選んだ親ディレクトリから次を実行します。クイックスタートでcheckout済みの場合は、このブロックを飛ばしてください。

実行するコマンド（通常のHost terminal。未checkoutの場合のみ）:
```bash
mkdir -p hakoniwa-robot-arm-workspace
cd hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
cd hakoniwa-robot-arm
```

新規・既存のcheckoutとも、通常のHost terminalで`hakoniwa-robot-arm`のrepository rootにいることを`pwd`で確認してから、次のimage作成コマンドを実行します。既存のcheckoutを使用する場合は、先にそのrepository rootへ移動してください。

実行するコマンド（通常のHost terminal。すべての利用者が実行）:
```bash
pwd
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

macOS Docker Desktop、CI、画面のない環境ではheadless用として起動します。いずれか一方のブロックだけを実行し、Container shellのプロンプトを待ってください。

実行するコマンド（通常のHost terminal、headless）:
```bash
HAKONIWA_DOCKER_GUI=off bash docker/run.bash jazzy
```

Linux HostでX11 Viewerを使用する場合だけ、Host側で接続を許可してGUIを有効にします。このブロックはheadlessの代わりに実行します。

実行するコマンド（通常のHost terminal、X11）:
```bash
xhost +si:localuser:root
HAKONIWA_DOCKER_GUI=on bash docker/run.bash jazzy
```

起動ログに次の内容が表示され、Container shellが開けばOKです。

```text
Mount: ... -> /workspace
Container: hakoniwa-arm-dev-jazzy; ...
Workdir: /workspace/work-docker-jazzy; Foundation mmap: tmpfs
```

このshellを終了するとContainerが削除されるため、以後`docker-hako`端末として最後まで開いたままにします。

標準の生成先（参照用。コマンドではない）:

```text
箱庭work:         /workspace/work-docker-jazzy
Dobot / ROS成果物: /workspace/work-docker-jazzy/ros2
```

どちらもHostへmountしたcheckout用ディレクトリ内に残ります。`docker/run.bash` の `HAKONIWA_ROS2_WS` も `/workspace/work-docker-jazzy/ros2` を指します。ただし、`foundation/runtime/mmap`だけはContainer内tmpfsであり、Container終了時に破棄されます。

## 3. 箱庭Workspaceへ入る

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako` |
| 実行ディレクトリ | `run.bash`が開いたContainer内の`hakoniwa-business-pack`リポジトリルート |
| この作業の入力成果物 | `run.bash`が設定した`HAKONIWA_COMPOSER`と`HAKONIWA_WORK_DIR` |
| この作業のゴール | Container内でFoundation、Forge、Runtimeを操作する箱庭Workspaceが開く。 |

実行するコマンド（Container shell `docker-hako`。新しいプロンプトを確認してから）:
```bash
python3.12 tools/workspace.py enter --workdir "$HAKONIWA_WORK_DIR"
```

child shellのpromptに`(hako)`が付いてから、別の入力として`pwd`を実行してください。`hakoniwa-business-pack`のパスが表示されればOKです。箱庭Workspaceへ入った後も作業ディレクトリはそのリポジトリルートのままです。

## 4. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-business-pack`リポジトリルート |
| この作業の入力成果物 | 前段で開いた箱庭Workspaceと、mount済みRobot Arm repository |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が準備され、doctorが成功する。 |

実行するコマンド（`docker-hako`の`(hako)` shell）:
```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python tools/workspace.py doctor
python tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

`plan`に`Recipe plan:`が表示されれば、構築予定を確認できています。初回の`plan`では、まだ存在しないFoundation成果物が`MISSING`と表示されても正常です。`configure`後に実行する2つのdoctorで`[OK]`と`SATISFIED`が表示され、ここでは`[NG]`、`MISSING`、`error:`がなければOKです。

## 5. Nova5 MJCFを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `docker-hako`の`(hako)` shell |
| 実行ディレクトリ | Container内の`hakoniwa-business-pack`リポジトリルートから開始 |
| この作業の入力成果物 | Nova5 Model Forge Recipeと、準備済みFoundation |
| この作業のゴール | `$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml`が生成される。 |

実行するコマンド（`docker-hako`の`(hako)` shell）:
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
