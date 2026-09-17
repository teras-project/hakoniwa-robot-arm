# セットアップ手順

この文書は利用構成を選ぶための入口です。初回のclone方法と前提ソフトウェアは[トップREADME](../../README.md#クイックスタート)を参照してください。環境変数の責務とprofileの仕組みは[環境profile](../design/environment-profiles.md)を正本とします。

## 利用構成を選ぶ

| 利用構成 | 適した環境 | Nova5 Runtime / MuJoCo | ROS 2 | 詳細手順 |
| --- | --- | --- | --- | --- |
| host-standalone | ROS 2を使わず箱庭単体で確認する | Host | 使用しない | [setup](host-standalone/setup.md) |
| host-ros2 | Ubuntu HostだけでROS 2連携まで確認する | Host | 同じUbuntu Host | [setup](host-ros2/setup.md) |
| host+docker | macOSからROS 2を使う、またはUbuntuでROS 2環境を分離する | Host | Docker Container | [setup-host-docker.md](host-docker/setup.md) |
| docker-only | HostへPython、CMake、ROS 2などを導入せず試す | Container | 同じContainer | [setup-docker-only.md](docker-only/setup.md) |

## 共通原則

- 4つの利用構成から1つだけを選び、同じ行のsetup、build、operationを使用します。
- HostではViewerありを標準とします。CI、画面のない環境、macOS上のdocker-onlyでは`--headless`を使用します。
- `HAKONIWA_WORK_DIR`にはFoundation、Forge、Recipe build、設定、ログ、セッションを生成します。
- `HAKONIWA_ROS2_WS`にはROS 2専用venv、Endpoint、colcon build/install/logを生成します。
- Host、Container、Humble、Jazzyの生成物には、それぞれ異なるworkディレクトリを使用します。
- workディレクトリはRecipeから再生成できる領域であり、ソースの正本ではありません。

## cloneと依存リポジトリ

最初に空のcheckout用workspaceへ次の2リポジトリだけをcloneします。

```bash
# 利用者が置きたい親ディレクトリで実行する。
mkdir -p hakoniwa-robot-arm-workspace
cd hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
```

Nova5 Runtime Recipeの`configure`は、Foundation、`hakoniwa-robot-runtime`、`hakoniwa-mujoco-robots`などを自動取得します。Forge Recipeの`configure`は`hakoniwa-mbody-registry`を自動取得します。ROS 2 workspaceの`build`はROS側の依存がなければ自動取得します。

既存checkoutは検査して再利用します。固定revisionと異なるcleanなcheckoutは指定revisionへ切り替える場合があります。未コミット変更があるcheckoutは変更せず、処理を停止します。

実行前に次の`plan`で予定を確認できます。

```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

## 次の手順

- [箱庭単体セットアップ](host-standalone/setup.md)
- [Host ROS 2連携セットアップ](host-ros2/setup.md)
- [host+dockerセットアップ](host-docker/setup.md)
- [docker-onlyセットアップ](docker-only/setup.md)
- [Nova5 Model Forge](../reference/model-forge.md)
