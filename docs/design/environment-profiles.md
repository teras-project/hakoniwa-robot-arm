# 環境profile

この文書は、`hakoniwa-robot-arm`を実行するshell環境の責務と初期化方法の正本です。

## 目的

checkoutの配置は利用者ごとに異なります。手順へ`$HOME`や利用者固有の絶対パスを埋め込まず、新しい端末ではprofileを`source`するだけで必要な環境を再現できるようにします。

```bash
source /path/to/hakoniwa-robot-arm/profiles/tool-env/activate.bash
```

この共通profileは、ファイル自身の配置からパスを解決するため、checkoutをホームディレクトリ以外へ置いても利用できます。

## profileの構成

```text
hakoniwa-robot-arm/
└── profiles/
    └── tool-env/
        └── activate.bash          # Git管理する共通profile

$HAKONIWA_WORK_DIR/
└── profiles/
    ├── activate-host-hako.bash
    ├── activate-host-ros-build.bash
    ├── activate-host-ros-bridge.bash
    ├── activate-host-ros-monitor.bash
    └── activate-host-ros-control.bash
```

| profile | 管理場所 | 責務 |
| --- | --- | --- |
| `profiles/tool-env/activate.bash` | リポジトリ | Arm Pack、Composer、checkout起点を、checkout配置から自動導出する |
| `activate-host-*.bash` | `HAKONIWA_WORK_DIR/profiles/` | 選択済みRuntime構成のwork、ROS 2 workspace、端末ロールを設定する |
| `$HAKONIWA_ROS2_WS/activate.bash` | ROS 2 workspaceの生成物 | ROS 2 Python環境とbuild済みパッケージを有効化する |

共通profileは、checkout配置に共通する値だけを設定します。構成ごとに異なる`HAKONIWA_WORK_DIR`と`HAKONIWA_ROS2_WS`は、`configure`が生成する`activate-host-*.bash`で設定します。

## 構成固有profileの生成仕様

共通profileはclone直後から利用できますが、Runtime構成ごとのprofileは、選択したRecipe、workディレクトリ、ROS 2 distributionが確定して初めて作成できます。そのため、構成固有profileは`configure`の完了時に、選択した`HAKONIWA_WORK_DIR`配下へ生成します。

```text
clone
  │
  ├─ 共通profileをsource
  │    └─ checkoutとComposerを解決する
  │
  └─ configure
       └─ 構成固有profileをwork配下へ生成する
```

host-onlyで`--ros2-tcp`を指定した場合の生成先とファイル名は次です。

```text
$HAKONIWA_WORK_DIR/profiles/
├── activate-host-hako.bash
├── activate-host-ros-build.bash
├── activate-host-ros-bridge.bash
├── activate-host-ros-monitor.bash
└── activate-host-ros-control.bash
```

| profile | 設定する責務 |
| --- | --- |
| `activate-host-hako.bash` | 箱庭Workspace、Foundation、Forge、Runtime、Viewerを操作する環境 |
| `activate-host-ros-build.bash` | ROS 2 workspaceをbuildする通常Host環境 |
| `activate-host-ros-bridge.bash` | ROS 2 Bridgeを起動・維持する環境 |
| `activate-host-ros-monitor.bash` | `JointState`を観察する環境 |
| `activate-host-ros-control.bash` | `JointTrajectory`を送信する環境 |

各profileは共通profileを読み込んだ上で、`HAKONIWA_WORK_DIR`、`HAKONIWA_ROS2_WS`、必要なbinding pathを設定し、`HAKO_TERMINAL_ROLE`を設定してpromptへ`(host-hako)`などのロール名を表示します。既存の箱庭Workspace promptは上書きせず、併記します。

ROS用profileは、`ros2_workspace.py build`により`$HAKONIWA_ROS2_WS/activate.bash`が作成された後に利用できます。profileをsourceした時点でこのファイルがない場合は、ROS 2 workspaceをbuildする必要があることを明示して失敗させます。

`--ros2-tcp`を指定しない構成では、`activate-host-hako.bash`だけを生成します。ROS 2連携へ切り替える場合は、`--ros2-tcp`を付けて再configureしてください。

### 利用方法

通常のHost terminalで、生成されたprofileをsourceします。

```bash
# 箱庭Workspaceを開く。子shellのpromptは (host-hako) (hako) ... となる。
source "$HAKONIWA_WORK_DIR/profiles/activate-host-hako.bash"

# ROS 2 workspaceをbuildする通常Host terminalで実行する。
source "$HAKONIWA_WORK_DIR/profiles/activate-host-ros-build.bash"

# ROS 2 workspace build後、用途ごとに別の通常Host terminalで実行する。
source "$HAKONIWA_WORK_DIR/profiles/activate-host-ros-bridge.bash"
source "$HAKONIWA_WORK_DIR/profiles/activate-host-ros-monitor.bash"
source "$HAKONIWA_WORK_DIR/profiles/activate-host-ros-control.bash"
```

## 環境変数の責務

| 変数 | 所有者 | 意味 |
| --- | --- | --- |
| `HAKOBASE_DIR` | 共通profile | `hakoniwa-robot-arm`とComposerを置くcheckout親ディレクトリ。利用者が手動設定する必要はない。 |
| `ARM_PACK` | 共通profile | `hakoniwa-robot-arm`リポジトリの絶対パス。既存ツールとの互換性のために提供する。 |
| `HAKONIWA_COMPOSER` | 共通profile | Composerリポジトリの絶対パス。標準配置では自動検出し、曖昧な場合だけ利用者が明示指定する。 |
| `HAKONIWA_WORK_DIR` | `workspace.py enter`または環境別手順 | Foundation、Forge、Recipeの生成物、設定、ログ、sessionの配置先。 |
| `HAKONIWA_ROS2_WS` | ROS 2手順 | ROS 2専用venv、build、install、logの配置先。 |

`CHECKOUT_ROOT`と`NOVA5_HOST_WORK`は、今後の手順では利用しません。前者は`HAKOBASE_DIR`で代替し、後者は特定ロボットに依存しない`HAKONIWA_WORK_DIR`へ置き換えます。

## 標準外の配置

通常は、共通profileがArm Packの兄弟ディレクトリからComposerを検出します。Composerを別の場所に置く場合、または候補が複数あって自動検出できない場合に限り、profileをsourceする前に設定します。

```bash
export HAKONIWA_COMPOSER=/absolute/path/to/composer-repository
source /path/to/hakoniwa-robot-arm/profiles/tool-env/activate.bash
```
