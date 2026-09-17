# host-onlyセットアップ

Nova5 RuntimeをHost上で実行する構成です。箱庭シミュレーション単体はmacOSまたはUbuntuで実行できます。ROS 2連携までHostだけで完結させる場合は、ROS 2 HumbleまたはJazzyを導入したUbuntuを使用します。

各段階の読み方は[手順の読み方と進行ゲート](procedure-guide.md)、端末の使い分けは[端末ロール](terminal-roles.md)を参照してください。

## 1. Hostの前提

**入力:** [トップREADME](../README.md#クイックスタート)に従ってclone済みの`hakoniwa-business-pack`と`hakoniwa-robot-arm`。

**ゴール:** Nova5 RuntimeをbuildできるHost環境を用意する。ROS 2連携を行う場合は、ROS 2 workspaceもbuildできる状態にする。

このページの例はUbuntu 24.04／ROS 2 Jazzyです。Humbleを使う場合は`jazzy`を`humble`へ読み替えます。

```bash
sudo apt update
sudo apt install -y \
  git ruby python3.12 python3.12-venv \
  build-essential cmake libboost-dev libgl1-mesa-dev libglfw3-dev

python3.12 --version
```

ROS 2連携を使う場合だけ、ROS 2とcolconを確認します。

```bash
sudo apt install -y python3-colcon-common-extensions
test -f /opt/ros/jazzy/setup.bash
/usr/bin/python3 -m colcon --help >/dev/null
```

**成功判定:** 必要なコマンドが正常終了する。ROS 2を使わない単体デモでは、後半のROS 2確認は不要です。

**次段への出力:** `host-hako`を開けるHost環境。

## 2. `host-hako`を開く

**入力:** 前段のHost環境。

**ゴール:** Foundation、Forge、Runtimeを操作する`host-hako`端末を開く。

通常のHost terminalで、Robot Arm repositoryへ移動してbootstrap profileをsourceします。

```bash
cd /path/to/hakoniwa-robot-arm
source profiles/tool-env/enter-host-hako.bash
```

この操作は、checkout配置からComposerを自動解決し、`$HAKOBASE_DIR/work-host`を`HAKONIWA_WORK_DIR`として箱庭Workspaceを開きます。手動で環境変数を`export`する必要はありません。

**成功判定:** 子shellのpromptが`(host-hako) (hako)`で始まる。

**次段への出力:** active Hakoniwa Workspace。以降、このページの「`host-hako`で実行」はこのshellを指します。

## 3. FoundationとRuntime Recipeを準備する

**入力:** activeな`host-hako`。

**ゴール:** Nova5 Runtime Recipeが依存取得・Foundation構築を実行できる状態にする。

`host-hako`で、まず変更を加えない`plan`で取得・build予定を確認します。予定が意図どおりなら`configure`を実行します。

```bash
python3.12 tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"

python3.12 tools/workspace.py doctor
python3.12 tools/recipe.py doctor \
  --recipe "$ARM_PACK/recipes/nova5/nova5-joint-trajectory-control.yaml"
```

**成功判定:** `plan`の対象Recipeと依存repositoryが意図どおりであり、両方の`doctor`で必須項目がすべて`[OK]`または`SATISFIED`となる。

**次段への出力:** FoundationとNova5 Runtime Recipeの依存が準備されたwork。

## 4. Nova5 Model Forgeを実行する

**入力:** FoundationとRuntime Recipeの準備が完了した`host-hako`。

**ゴール:** 上流モデルからNova5のMuJoCo入力を生成する。

```bash
python3.12 tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python3.12 tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
python "$ARM_PACK/tools/recipe/nova5.py" forge

test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

**成功判定:** `nova5.contact.xml`が存在し、Forgeがerrorなく終了する。

**次段への出力:** buildで使用するNova5 MJCF。詳細は[Nova5 Model Forge](model-forge.md)を参照してください。

次は[host-onlyビルド](build-host-only.md)へ進んでください。
