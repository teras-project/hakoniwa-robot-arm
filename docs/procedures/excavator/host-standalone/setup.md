# Excavator 箱庭単体セットアップ

macOS、Ubuntu 24.04 native、WSL2 Ubuntu 24.04でMathScavator9000をheadless実行する手順です。端末はbashの`host-hako`、作業ディレクトリは明記がない限り`hakoniwa-business-pack`ルートです。

[手順一覧](../../README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)

## 1. 共通前提とcheckout

| 項目 | 内容 |
| --- | --- |
| 実行端末 | 通常のHost terminal |
| 実行ディレクトリ | checkoutを置く親ディレクトリ |
| この作業の入力成果物 | Git、CPython 3.12、Ruby、CMake、C++ toolchain |
| この作業のゴール | Business PackとRobot Armが同じ親にcloneされる。 |

前提は[箱庭単体セットアップ](../../host-standalone/setup.md#1-hostの前提を準備する)に従います。Ubuntu native／WSL2では同ページの`apt`コマンドを先に実行します。macOSではトップREADMEのmacOS前提を使用します。

```bash
mkdir -p hakoniwa-robot-arm-workspace
cd hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
cd hakoniwa-robot-arm
source profiles/tool-env/enter-host-hako.bash
```

新しいpromptが`(host-hako) (hako)`で始まり、`pwd`が`hakoniwa-business-pack`なら成功です。command not foundやclone失敗はNGです。

## 2. FoundationとRuntime Recipe

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`ルート |
| この作業の入力成果物 | clone済みcheckout |
| この作業のゴール | `excavator-joint-trajectory-control`のFoundationと依存がSATISFIEDになる。 |

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-joint-trajectory-control.yaml
python3.12 tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-joint-trajectory-control.yaml
python tools/workspace.py doctor
python tools/recipe.py doctor \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-joint-trajectory-control.yaml
```

`Recipe plan:`、`Foundation: SATISFIED`が表示され、`[NG]`、`MISSING`、`error:`がなければ成功です。それらがあればNGです。

## 3. Model Forge

| 項目 | 内容 |
| --- | --- |
| 実行端末 | `host-hako` |
| 実行ディレクトリ | `hakoniwa-business-pack`ルートからRobot Armルートへ移動 |
| この作業の入力成果物 | 準備済みFoundation |
| この作業のゴール | bucket-proxy venvと`excavator.mobile.xml`が生成される。 |

```bash
python tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-model-forge.yaml
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-model-forge.yaml
cd ../hakoniwa-robot-arm
python tools/install_excavator_bucket_proxy_tools.py
python tools/recipe/excavator.py forge
test -f "$HAKONIWA_WORK_DIR/model-forge/excavator/install/excavator.mobile.xml"
```

`Excavator bucket-proxy tools are ready.`と`Excavator forge complete.`が表示され、`test`が0なら成功です。次は[ビルド](build.md)へ進みます。
