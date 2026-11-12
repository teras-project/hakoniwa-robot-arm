# host+dockerセットアップ

Nova5 RuntimeとMuJoCo ViewerをHost、Dobot 公式サービス用 ROS 2 Bridge、monitor、controlをDocker Containerで実行する準備手順です。macOS＋ROS 2 Jazzyを主な対象とします。実機を使わず、箱庭で公式デモを確認します。公式 Dobot ソースとメッセージは[ビルド手順](build.md)で準備します。

手順: [一覧](../README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)

| 端末 | 実行場所・Python環境 |
| --- | --- |
| 通常のHost terminal | パッケージとDocker imageの準備。箱庭Workspaceは有効にしない。 |
| `host-hako` | Hostの箱庭Workspace。初回のFoundation構築はCPython 3.12、構築後はFoundationの`python`を使用。 |
| DockerのROS 2端末 | Container内のROS 2専用環境。箱庭Workspaceには入らない。 |

コードブロックは[手順の読み方](../conventions.md#コードブロックと端末の読み方)に従い、シェルが切り替わるコマンドは単独で実行します。

## 1. Hostの前提を準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 任意 |
| この作業の入力成果物 | 同じ親ディレクトリへclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm` |
| この作業のゴール | HostでNova5 Runtimeをbuildでき、Dockerを実行できる。 |

macOSでは次のHost packageを準備します。Foundationの初期化にはCPython 3.12が必要です。

実行するコマンド（通常のHost terminal）:
```bash
brew install git ruby python@3.12 cmake glfw
python3.12 --version
cmake --version
docker --version
```

3つのversionが表示されればOKです。`command not found`になればNGです。

Ubuntu HostではC/C++ build環境、CPython 3.12、CMake、OpenGL／GLFW、Dockerを準備します。ROS 2はContainerで実行するため、HostへのROS 2 installationは不要です。

## 2. `host-hako`端末を開く

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal。この操作後に開くchild shellが`host-hako`になる。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で確認済みのHostコマンドと、clone済みの2リポジトリ |
| この作業のゴール | Foundation、Forge、Runtimeの操作に使用する`host-hako`端末が開く。 |

通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で場所を確認してください。そこから次のコマンドだけを実行します。

実行するコマンド（通常のHost terminal）:
```bash
source profiles/tool-env/enter-host-hako.bash
```

`host-hako`のプロンプトが出てから、新しく開いたshellで`pwd`を実行します。promptが`(host-hako) (hako)`で始まり、ディレクトリ末尾が`hakoniwa-business-pack`ならOKです。

## 3. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | clone済みリポジトリと、前段で確認済みのHostコマンド |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が`../work-host`へ準備され、doctorが成功する。 |

実行するコマンド（`host-hako`、`hakoniwa-business-pack`リポジトリルート）:
```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python tools/workspace.py doctor
python tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

`plan`に`Recipe plan:`が表示されれば、構築予定を確認できています。Nova5 が使う Runtime の拡張 API は[上流 PR #29](https://github.com/hakoniwalab/hakoniwa-robot-runtime/pull/29)で未マージのため、この Recipe は fork 上の対応 commit を固定して取得します。既に上流 `main` の Runtime を取得していた場合も、未変更の checkout なら `configure` が対応 commit へ切り替えます。初回の`plan`では、まだ存在しないFoundation成果物が`MISSING`と表示されても正常です。`configure`後に実行する2つのdoctorで`[OK]`と`SATISFIED`が表示され、ここでは`[NG]`、`MISSING`、`error:`がなければOKです。

## 4. Nova5 MJCFを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository rootから開始 |
| この作業の入力成果物 | Nova5 Model Forge Recipeと、前段で準備したFoundation |
| この作業のゴール | `../work-host/model-forge/nova5/install/nova5.contact.xml`が生成される。 |

実行するコマンド（`host-hako`、`hakoniwa-business-pack`リポジトリルート）:
```bash
python tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml

cd ../hakoniwa-robot-arm
python tools/recipe/nova5.py forge
ls -l ../work-host/model-forge/nova5/install/nova5.contact.xml
```

最後の`ls`で`nova5.contact.xml`が表示されればOKです。変換内容は[Nova5 Model Forge](../../reference/model-forge.md)を参照してください。

## 5. ROS 2 Docker imageを作成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 新しい通常Host terminal。以後`docker-run`端末として使用する。 |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 起動済みDocker Engine／Docker Desktopと、本リポジトリのDockerfile |
| この作業のゴール | `hakoniwa-arm-dev:jazzy` imageが生成される。 |

新しい通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してから実行します。

実行するコマンド（通常のHost terminal）:
```bash
bash docker/create-docker-image.bash jazzy
docker image inspect hakoniwa-arm-dev:jazzy --format '{{.RepoTags}}'
```

最後のコマンドに`hakoniwa-arm-dev:jazzy`が表示されればOKです。Humbleを使用する場合は、両方の`jazzy`を`humble`へ置き換えます。

次は[host+dockerビルド](build.md)へ進んでください。
