# セットアップ手順

この文書は利用構成を選ぶための入口です。初回のclone方法と前提ソフトウェアは[トップREADME](../../README.ja.md#クイックスタート)を参照してください。環境変数の責務とprofileの仕組みは[環境profile](../design/environment-profiles.md)を正本とします。

[手順一覧](README.md) → **セットアップ** → [ビルド](build.md) → [起動・動作確認](operation.md)。コマンドと出力例、シェル切替の区別は[手順の読み方](conventions.md#コードブロックと端末の読み方)を参照してください。

## 利用構成を選ぶ

| 利用構成 | 適した環境 | Nova5 Runtime / MuJoCo | ROS 2 | 詳細手順 |
| --- | --- | --- | --- | --- |
| host-standalone | Ubuntu／macOSでROS 2を使わず箱庭単体で確認する | Host | 使用しない | [setup](host-standalone/setup.md) |
| windows-host-standalone | Windows nativeで箱庭単体を確認する | Windows Host | 使用しない | [setup](windows-host-standalone/setup.md) |
| Excavator host-standalone | macOS／Ubuntu 24.04／WSL2でExcavatorをheadless確認する | Host | 使用しない | [setup](excavator/host-standalone/setup.md) |
| Excavator windows-host-standalone | Windows nativeでExcavatorをheadless確認する | Windows Host | 使用しない | [setup](excavator/windows-host-standalone/setup.md) |
| windows-host-docker | WindowsでMuJoCo ViewerとROS 2連携を確認する | Windows Host | Docker Desktop | [setup](windows-host-docker/setup.md) |
| host-ros2 | Ubuntu HostだけでROS 2連携まで確認する | Host | 同じUbuntu Host | [setup](host-ros2/setup.md) |
| host+docker | macOSからROS 2を使う、またはUbuntuでROS 2環境を分離する | Host | Docker Container | [setup-host-docker.md](host-docker/setup.md) |
| docker-only | HostへPython、CMake、ROS 2などを導入せず試す | Container | 同じContainer | [setup-docker-only.md](docker-only/setup.md) |

## 共通原則

- 利用構成から1つだけを選び、同じ行のsetup、build、operationを使用します。
- HostではViewerありを標準とします。CI、画面のない環境、macOS上のdocker-onlyでは`--headless`を使用します。
- `HAKONIWA_WORK_DIR`にはFoundation、Forge、Recipe build、設定、ログ、セッションを生成します。
- `HAKONIWA_ROS2_WS`にはROS 2専用venv、Endpoint、colcon build/install/logを生成します。
- Foundation、Forge、Runtimeを含む箱庭workは、Host、Container、Humble、Jazzyで分離します。Docker内のROS 2成果物だけは、同じdistributionとCPU architectureのhost+docker／docker-only間で共有します。
- workディレクトリはRecipeから再生成できる領域であり、ソースの正本ではありません。

## cloneと依存リポジトリ

最初に空のcheckout用workspaceへ次の2リポジトリだけをcloneします。

実行するコマンド（通常のHost terminal。利用者が選んだ親ディレクトリで実行）:
```bash
mkdir -p hakoniwa-robot-arm-workspace
cd hakoniwa-robot-arm-workspace
git clone https://github.com/hakoniwalab/hakoniwa-business-pack.git
git clone https://github.com/teras-project/hakoniwa-robot-arm.git
```

Nova5 Runtime Recipeの`configure`は、Foundation、`hakoniwa-robot-runtime`、`hakoniwa-mujoco-robots`などを自動取得します。Forge Recipeの`configure`は`hakoniwa-mbody-registry`を自動取得します。ROS 2 workspaceの`build`はROS側の依存がなければ自動取得します。

既存checkoutは検査して再利用します。固定revisionと異なるcleanなcheckoutは指定revisionへ切り替える場合があります。未コミット変更があるcheckoutは変更せず、処理を停止します。

セットアップの中で箱庭Workspaceへ入り、`hakoniwa-business-pack`のリポジトリルート（`tools/`ディレクトリがある場所）にいる状態なら次の`plan`で予定を確認できます。まだWorkspaceに入っていない場合は選択した構成のsetupに進んでください。

実行するコマンド（箱庭Workspace内の`hakoniwa-business-pack`リポジトリルート）:
```bash
python3.12 tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/nova5/nova5-joint-trajectory-control.yaml
```

## 次の手順

- [箱庭単体セットアップ](host-standalone/setup.md)
- [Windows native箱庭単体セットアップ](windows-host-standalone/setup.md)
- [Excavator 箱庭単体セットアップ](excavator/host-standalone/setup.md)
- [Excavator Windows native箱庭単体セットアップ](excavator/windows-host-standalone/setup.md)
- [Windows host+Dockerセットアップ](windows-host-docker/setup.md)
- [Host ROS 2連携セットアップ](host-ros2/setup.md)
- [host+dockerセットアップ](host-docker/setup.md)
- [docker-onlyセットアップ](docker-only/setup.md)
- [Nova5 Model Forge](../reference/model-forge.md)
