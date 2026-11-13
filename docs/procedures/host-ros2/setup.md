# Host ROS 2連携セットアップ

Nova5 Runtime、MuJoCo Viewer、Dobot 公式サービスに接続する ROS 2 Bridge と sample node を同じ Ubuntu Host 上で実行する準備手順です。Ubuntu 24.04／ROS 2 Jazzy を使用します。Ubuntu 22.04／Humble の Dobot 経路は現時点で[対応待ち](../ros2/dobot-build.md)です。ROS launch の既定は箱庭で、実機の `real`／`both` は箱庭確認後の[追加手順](real.md)で扱います。公式 Dobot ソースとメッセージは[ビルド手順](build.md)で取得・生成します。

手順: [一覧](../README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)

| 端末 | 実行場所・Python環境 |
| --- | --- |
| 通常のHost terminal | パッケージの準備。箱庭Workspaceは有効にしない。 |
| `host-hako` | Foundation／Forge／Runtime用。初回のFoundation構築はCPython 3.12、構築後はFoundationの`python`を使用。 |
| `host-ros-*` | ROS 2用の別端末。箱庭Workspaceには入らず、ROS 2のシステムPythonと専用venvを使用。 |

コードブロックと端末切替は[手順の読み方](../conventions.md#コードブロックと端末の読み方)を参照してください。

各手順の直後に正常時の出力例とNG条件を示します。実際のログを照合し、NG条件に該当した場合はその段階で止めてください。

## 1. Hostの前提を準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 任意 |
| この作業の入力成果物 | 同じ親ディレクトリへclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm` |
| この作業のゴール | Nova5 Runtimeのconfigureとbuildに必要なHostコマンドに加え、ROS 2とcolconが使用できる。 |

UbuntuへHost用パッケージを導入します。FoundationにはCPython 3.12とそのvenv作成機能が必要です。

実行するコマンド（通常のHost terminal）:
```bash
sudo apt update
sudo apt install -y \
  git ruby python3.12 python3.12-venv \
  build-essential cmake libboost-dev libgl1-mesa-dev libglfw3-dev

python3.12 --version
cmake --version
```

両方のversionが表示されればHost用パッケージはOKです。command not foundになればNGです。

使用するROS distributionとcolconを確認します。以下はUbuntu 24.04／Jazzyの例です。

実行するコマンド（通常のHost terminal）:
```bash
sudo apt install -y python3-colcon-common-extensions python3-venv python3-pip
ls -l /opt/ros/jazzy/setup.bash
/usr/bin/python3 -m colcon --help
```

`setup.bash`のファイル情報とcolconのhelpが表示されればOKです。`No such file or directory`またはPython errorになればNGです。

## 2. `host-hako`端末を開く

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal。この操作後に開くchild shellが`host-hako`になる。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で確認済みのHostコマンドと、clone済みの2リポジトリ |
| この作業のゴール | Foundation、Forge、Runtimeの操作に使用する`host-hako`端末が開く。 |

`/absolute/path/to/hakoniwa-robot-arm`は、実際にcloneしたディレクトリへ置き換えます。

通常のHost terminalで`hakoniwa-robot-arm`のrepository rootへ移動し、`pwd`で確認してください。次のコマンドだけを実行し、新しいプロンプトを待ちます。

実行するコマンド（通常のHost terminal）:
```bash
source profiles/tool-env/enter-host-hako.bash
```

新しく開いた`host-hako` shellで確認します。

実行するコマンド（`host-hako`）:
```bash
pwd
```

promptが`(host-hako) (hako)`で始まり、`pwd`の結果が`.../hakoniwa-business-pack`ならOKです。

## 3. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | clone済みリポジトリと、前段で確認済みのHostコマンド |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が兄弟の`work-host`へ準備され、両方のdoctorが成功する。 |

`plan`はファイルを変更せず、Recipeを解決できることを事前確認します。基本手順では内容を利用者が判断する必要はなく、コマンドの成否だけを確認します。

実行するコマンド（`host-hako`、`hakoniwa-business-pack`リポジトリルート）:
```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

先頭に`Recipe plan:`が表示され、`error:`で終了しなければOKです。

実行するコマンド（`host-hako`、`hakoniwa-business-pack`リポジトリルート）:
```bash
python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python tools/workspace.py doctor
python tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

doctorに次のような`[OK]`と`SATISFIED`が表示されれば正常です。

```text
[OK] Foundation Python and Hakoniwa modules are workspace-owned.
Foundation: SATISFIED
[SATISFIED] Recipe dependency ...
[SATISFIED] Recipe runtime: ...
```

`[NG]`、`MISSING`、`error:`が一つもなければOKです。

## 4. Model Forge Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | Nova5 Model Forge Recipeと、前段で準備したFoundation |
| この作業のゴール | 上流モデルの取得とMJCF変換に必要なツール、Python packageを準備する。 |

Forge Recipeを解決し、変換に必要なツールとPython packageを準備します。

実行するコマンド（`host-hako`、`hakoniwa-business-pack`リポジトリルート）:
```bash
python tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml

python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml
```

`plan`の先頭に`Recipe plan:`が表示され、両コマンドが`error:`で終了しなければOKです。

## 5. 上流モデルからNova5 MJCFを生成する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 固定revisionで指定された上流Nova5 Xacro／STL mesh、`actuator.yaml`、`contact-excludes.yaml`、前段で準備したForge変換ツール |
| この作業のゴール | 上流のURDF/XacroモデルをMuJoCo形式のMJCFへ変換し、`../work-host/model-forge/nova5/install/nova5.contact.xml`を生成する。 |

`host-hako`でRobot Arm repositoryへ移動して実行します。

実行するコマンド（`host-hako`、Robot Arm repository rootへ移動する）:
```bash
cd ../hakoniwa-robot-arm
python tools/recipe/nova5.py forge
ls -l ../work-host/model-forge/nova5/install/nova5.contact.xml
```

Forgeログに`Nova5 output`と`.../work-host/model-forge/nova5/install/nova5.contact.xml`が表示され、最後の`ls`で同じファイルを確認できればOKです。`No such file or directory`ならNGです。変換内容は[Nova5 Model Forge](../../reference/model-forge.md)を参照してください。

次は[Host ROS 2連携ビルド](build.md)へ進みます。
