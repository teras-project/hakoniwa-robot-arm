# host+dockerセットアップ

Nova5 RuntimeとMuJoCo ViewerをHost、ROS 2 Bridge、monitor、controlをDocker Containerで実行するための準備手順です。macOS＋ROS 2 Jazzyを主な対象とします。

## 1. Hostの前提を準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 任意 |
| この作業の入力成果物 | 同じ親ディレクトリへclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm` |
| この作業のゴール | HostでNova5 Runtimeをbuildでき、Dockerを実行できる。 |

macOSでは次のHost packageを準備します。

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

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/enter-host-hako.bash
```

新しく開いたshellで`pwd`を実行します。promptが`(host-hako) (hako)`で始まり、ディレクトリ末尾が`hakoniwa-business-pack`ならOKです。

## 3. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | clone済みリポジトリと、前段で確認済みのHostコマンド |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が`../work-host`へ準備され、doctorが成功する。 |

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

`plan`に`Recipe plan:`、doctorに`[OK]`と`SATISFIED`が表示され、`[NG]`、`MISSING`、`error:`がなければOKです。

## 4. Nova5 MJCFを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository rootから開始 |
| この作業の入力成果物 | Nova5 Model Forge Recipeと、前段で準備したFoundation |
| この作業のゴール | `../work-host/model-forge/nova5/install/nova5.contact.xml`が生成される。 |

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml
python3.12 tools/recipe.py configure \
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

```bash
cd /absolute/path/to/hakoniwa-robot-arm
bash docker/create-docker-image.bash jazzy
docker image inspect hakoniwa-arm-dev:jazzy --format '{{.RepoTags}}'
```

最後のコマンドに`hakoniwa-arm-dev:jazzy`が表示されればOKです。Humbleを使用する場合は、両方の`jazzy`を`humble`へ置き換えます。

次は[host+dockerビルド](build.md)へ進んでください。
