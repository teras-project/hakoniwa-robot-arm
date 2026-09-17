# 箱庭単体セットアップ

Nova5 RuntimeとMuJoCo ViewerをHost上で実行し、ROS 2を使わずに箱庭単体で動作確認するための準備手順です。

PS5コントローラー（DualSense）で操作する場合は、[箱庭単体・ゲームパッドセットアップ](setup-gamepad.md)へ進んでください。

各手順の直後に正常時の出力例とNG条件を示します。実際のログを照合し、NG条件に該当した場合はその段階で止めてください。

## 1. Hostの前提を準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | 任意 |
| この作業の入力成果物 | 同じ親ディレクトリへclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm` |
| この作業のゴール | Nova5 Runtimeのconfigureとbuildに必要なHostコマンドが使用できる。 |

UbuntuへHost用パッケージを導入します。

```bash
sudo apt update
sudo apt install -y \
  git ruby python3.12 python3.12-venv \
  build-essential cmake libboost-dev libgl1-mesa-dev libglfw3-dev

python3.12 --version
cmake --version
```

両方のversionが表示されればHost用パッケージはOKです。command not foundになればNGです。

## 2. `host-hako`端末を開く

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal。この操作後に開くchild shellが`host-hako`になる。 |
| 実行ディレクトリ | cloneした`hakoniwa-robot-arm`のrepository root |
| この作業の入力成果物 | 前段で確認済みのHostコマンドと、clone済みの2リポジトリ |
| この作業のゴール | Foundation、Forge、Runtimeの操作に使用する`host-hako`端末が開く。 |

`/absolute/path/to/hakoniwa-robot-arm`は、実際にcloneしたディレクトリへ置き換えます。

```bash
cd /absolute/path/to/hakoniwa-robot-arm
source profiles/tool-env/enter-host-hako.bash
```

新しく開いたshellで確認します。

```bash
pwd
```

正常時は次の形式になります。

```text
/.../hakoniwa-business-pack
```

promptが`(host-hako) (hako)`で始まり、ディレクトリ末尾が`hakoniwa-business-pack`ならOKです。

## 3. FoundationとRuntime Recipeを準備する

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`のrepository root |
| この作業の入力成果物 | clone済みリポジトリと、前段で確認済みのHostコマンド |
| この作業のゴール | FoundationとNova5 Runtime Recipeの依存が兄弟の`work-host`へ準備され、両方のdoctorが成功する。 |

`plan`はファイルを変更せず、Recipeを解決できることを事前確認します。基本手順では内容を利用者が判断する必要はなく、コマンドの成否だけを確認します。

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

先頭に`Recipe plan:`が表示され、`error:`で終了しなければOKです。

```bash
python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

正常時は、doctorの末尾を含む出力が次の状態になります。

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

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-model-forge.yaml

python3.12 tools/recipe.py configure \
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

```bash
cd ../hakoniwa-robot-arm
python tools/recipe/nova5.py forge
ls -l ../work-host/model-forge/nova5/install/nova5.contact.xml
```

正常時はForgeログに次の出力先が表示され、最後の`ls`で同じファイルの情報を確認できます。

```text
Nova5 output     : /.../work-host/model-forge/nova5/install
... /.../work-host/model-forge/nova5/install/nova5.contact.xml
```

`nova5.contact.xml`が表示されればOK、`No such file or directory`ならNGです。変換内容は[Nova5 Model Forge](../../reference/model-forge.md)を参照してください。

次は[箱庭単体ビルド](build.md)へ進みます。
