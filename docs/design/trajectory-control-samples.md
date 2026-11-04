# 箱庭単体 JointTrajectory と ROS 2 Dobot サンプル

箱庭単体の JointTrajectory PDU と、Nova5 の ROS 2 Dobot サービス操作は別の経路です。環境のsetup、build、起動順序は[実行手順](../procedures/README.md)を使用してください。

## 1. 2つの操作経路

| 項目 | 箱庭単体版 | ROS 2版 |
| --- | --- | --- |
| 送信プログラム | `tools/control/send_joint_trajectory.py` | `ros2_packages/hakoniwa_arm_samples/hakoniwa_arm_samples/control.py` |
| 軌道の指定 | `recipes/<robot>/demo-trajectory.json`または任意の外部JSON | `GetAngle`から現在角を読み、小さな相対目標を作成 |
| 送信先 | SHM上のJointTrajectory PDU | Dobot公式`GetAngle`、`EnableRobot`、`SpeedFactor`、`MovJ`サービス |
| Runtimeまでの経路 | sender → SHM PDU → Runtime | ROS 2 control → Service Bridge → TCP/PDU-RPC → Dobot Asset → Runtime |
| 標準の実行方法 | `tools/recipe/<robot>.py start`でLauncherが自動起動 | `ros2 run hakoniwa_arm_samples control`（既定はdry-run） |
| 外部軌道ファイル | `--trajectory <file>` | 非対応。必要なら独自のDobotサービスクライアントを作成 |

ROS 2 版は旧 `/joint_trajectory` topic を送信しません。箱庭単体版のsenderと外部軌道JSONの仕様は以下のとおりです。

## 2. 箱庭単体版

### 配置とLauncherの動作

送信プログラムとロボット別の標準軌道は次の場所にあります。

```text
tools/control/send_joint_trajectory.py
recipes/nova5/demo-trajectory.json
recipes/fr5/demo-trajectory.json
recipes/so101/demo-trajectory.json
```

`tools/recipe/<robot>.py configure`は、選択したロボットの`demo-trajectory.json`を絶対パスでLauncherへ登録します。`start`するとRuntimeの起動後にsenderが軌道を1回送信し、Launcherが停止するまで待機します。

```text
tools/recipe/<robot>.py start
  → tools/control/send_joint_trajectory.py
  → recipes/<robot>/demo-trajectory.json
  → JointTrajectory PDU
  → Robot Arm Runtime
```

### 軌道JSONの形式

Nova5の標準ファイルは`recipes/nova5/demo-trajectory.json`です。

```json
{
  "joint_names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
  "points": [
    {
      "time_from_start": 0.0,
      "positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    },
    {
      "time_from_start": 2.0,
      "positions": [0.35, -0.45, 0.55, 0.0, 0.25, 0.0]
    }
  ]
}
```

| field | 意味 |
| --- | --- |
| `joint_names` | 軌道に含める関節名と順序 |
| `points` | 時系列の軌道点。1点以上必要 |
| `time_from_start` | 軌道開始からその点へ到達するまでの秒数 |
| `positions` | `joint_names`と同じ順序の目標関節位置。通常radで扱う |

すべての`positions`は`joint_names`と同じ要素数にします。`time_from_start`は先頭から昇順にし、目標位置は対象モデルのjoint limit内に収めます。senderはposition制御を使用し、velocity、acceleration、effortは関節数と同じ長さのゼロ配列として送信します。

機種ごとの関節名は[対応ロボット](../reference/robots.md)を参照してください。

### 標準デモ軌道を変更して実行する

対象ロボットのファイルを編集します。

```text
recipes/<robot>/demo-trajectory.json
```

同じパスのJSON内容だけを変更した場合、configureやbuildは不要です。実行中なら一度停止し、再度起動します。

```bash
python tools/recipe/nova5.py stop
python tools/recipe/nova5.py start
python tools/recipe/nova5.py status
```

senderのログは次の場所に出力されます。

```text
../work-host/recipes/<robot>-joint-trajectory-control/logs/<robot>-trajectory-sender.out
../work-host/recipes/<robot>-joint-trajectory-control/logs/<robot>-trajectory-sender.err
```

成功時は標準出力ログに`Successfully sent JointTrajectory PDU.`が記録されます。

### 任意の外部JSONを直接送信する

senderの`--trajectory`には任意のJSONファイルを指定できます。まず標準ファイルをwork領域へコピーして編集する例を示します。

```bash
mkdir -p ../work-host/trajectories
cp recipes/nova5/demo-trajectory.json ../work-host/trajectories/my-trajectory.json
```

Runtimeが`RUNNING`であることを確認し、`host-hako`端末の`hakoniwa-robot-arm` repository rootで実行します。`--environment`を付けてconfigureした構成では、生成済みのenvironment manifestを指定します。

```bash
python tools/control/send_joint_trajectory.py \
  ../work-host/recipes/nova5-joint-trajectory-control/config/asset-manifest-environment.json \
  --trajectory ../work-host/trajectories/my-trajectory.json
```

`--environment`を使わなかった構成では、manifest名を`asset-manifest.json`へ置き換えます。任意JSONの直接送信にconfigureやbuildは不要です。

通常の箱庭単体Launcherは起動直後に標準デモ軌道も送信します。外部JSONだけを評価する場合は、その初回送信が完了してから外部JSONを送信し、後から送った軌道の動作を確認してください。

## 3. ROS 2版

### ソースとbuild後の配置

ROS 2サンプルpackageとcontrol nodeのソースは次の場所にあります。

```text
ros2_packages/hakoniwa_arm_samples/
└── hakoniwa_arm_samples/
    ├── control.py
    └── monitor.py
```

host-ros2構成では標準colcon build後に次の実行物が生成されます。

```text
../work-host/dobot-apps/install/
└── hakoniwa_arm_samples/lib/hakoniwa_arm_samples/
    ├── control
    └── monitor
```

host+Dockerとdocker-onlyでは、選択した`DOBOT_WORK/dobot-apps/install/`以下へ生成されます。

### Dobot公式サービスによる実行

`control` は J1 の現在角から+3°を計算して表示し、`--execute` を付けた場合だけ
`SpeedFactor=10` と `MovJ` を呼びます。受理応答と実測角の到達は別々に確認します。

```bash
ros2 run hakoniwa_arm_samples control
ros2 run hakoniwa_arm_samples control --execute --delta-deg 3
ros2 run hakoniwa_arm_samples monitor
```

`monitor` の既定topicは `/joint_states_robot`、表示間隔は1秒です。
実機を含む `real`／`both` で `--execute` を使う前に安全確認が必要です。
同じ公式サービスを使う独自nodeの作成方法は[独自ROS 2 node](../procedures/ros2/custom-nodes.md)、
利用構成と安全上の注意は[ROS 2によるアーム操作](../procedures/ros2/arm-operations.md)を参照してください。

## 4. 変更内容と必要な反映操作

| 変更内容 | configure | build | 必要な実行 |
| --- | --- | --- | --- |
| `recipes/<robot>/demo-trajectory.json`の内容 | 不要 | 不要 | Runtimeを停止して`start`し直す |
| 外部JSONを箱庭単体senderへ渡す | 不要 | 不要 | `send_joint_trajectory.py --trajectory ...`を実行 |
| `tools/control/send_joint_trajectory.py` | 不要 | 不要 | Runtimeを停止して`start`し直す |
| ROS 2 controlのCLI値 | 不要 | 不要 | `ros2 run ... control`を再実行 |
| ROS 2 controlの`--delta-deg`を変更 | 不要 | 不要 | dry-runで点検後、必要なら`--execute`を明示 |
| `ros2_packages/.../control.py` | 不要 | サンプルworkspaceを再build | install環境をsourceして`ros2 run`を再実行 |
| 独自ROS 2 package | 不要 | 独自workspaceをbuild | install環境をsourceしてnodeを実行 |

軌道やサンプルを変更しても、MJCFの再Forgeは不要です。Robot Model、joint limit、actuator設定を変更した場合の反映方法は[設定変更と反映方法](configuration-workflow.md)を参照してください。
