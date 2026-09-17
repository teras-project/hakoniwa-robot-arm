# JointTrajectoryサンプルの構成と変更方法

この文書は、箱庭単体版とROS 2版のJointTrajectoryサンプルについて、ソースの配置、軌道の設定方法、実行方法、変更の反映条件を説明します。環境のsetup、build、起動順序は[実行手順](../procedures/README.md)を使用してください。

## 1. 2つのサンプル

| 項目 | 箱庭単体版 | ROS 2版 |
| --- | --- | --- |
| 送信プログラム | `tools/control/send_joint_trajectory.py` | `ros2_packages/hakoniwa_arm_samples/hakoniwa_arm_samples/control.py` |
| 軌道の指定 | `recipes/<robot>/demo-trajectory.json`または任意の外部JSON | 単体版と同じ外部JSON、またはCLIによる正弦軌道生成 |
| 送信先 | SHM上のJointTrajectory PDU | ROS 2 `/joint_trajectory` topic |
| Runtimeまでの経路 | sender → SHM PDU → Runtime | ROS 2 control → ROS Bridge → TCP → Endpoint → SHM PDU → Runtime |
| 標準の実行方法 | `tools/recipe/<robot>.py start`でLauncherが自動起動 | `ros2 run hakoniwa_arm_samples control ...` |
| 外部軌道ファイル | `--trajectory <file>` | `--trajectory <file>` |

どちらも`trajectory_msgs/JointTrajectory`と同じ関節名、位置、開始からの時刻をRuntimeへ渡します。ただし、軌道を作る場所と入力方法が異なります。

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
../work-host/ros2-samples/install/
└── hakoniwa_arm_samples/lib/hakoniwa_arm_samples/
    ├── control
    └── monitor
```

host+Dockerとdocker-onlyでは、選択した`HAKONIWA_ROS2_WS`に`-samples`を付けたworkspaceの`install/`以下へ生成されます。

### 軌道の設定と実行

ROS 2 `control`サンプルは、外部JSONを指定しない場合、CLIオプションから4点の正弦波状軌道を生成して`/joint_trajectory`へ1回publishします。

```bash
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory \
  --joints 6 \
  --amplitude 0.15 \
  --duration 2.0
```

| option | 意味 | default |
| --- | --- | --- |
| `--topic` | JointTrajectoryの送信先topic | `/joint_trajectory` |
| `--trajectory` | 単体版と同じ形式の外部軌道JSON | 未指定 |
| `--joints` | `joint1`から連番で生成する関節数 | `6` |
| `--joint-names` | 関節名を順序付きで明示する。指定時は`--joints`より優先 | 未指定 |
| `--amplitude` | 正弦波状に生成する目標位置の振幅 | `0.35` |
| `--duration` | 連続する軌道点の時間間隔。最終点は`3 × duration`秒 | `3.0` |

Nova5以外では関節名を明示します。FR5の例は次のとおりです。

```bash
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory \
  --joint-names j1_joint j2_joint j3_joint j4_joint j5_joint j6_joint \
  --amplitude 0.15 \
  --duration 2.0
```

ROS 2側の詳細な端末準備と成功判定は[ROS 2によるアーム操作](../procedures/ros2/arm-operations.md)を参照してください。

### 任意の軌道を送信する

`--trajectory`へ、箱庭単体版と同じ`joint_names`と`points`を持つJSONを指定します。

```bash
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory \
  --trajectory /absolute/path/to/my-trajectory.json
```

`--trajectory`指定時はJSON内の関節名、軌道点、時刻、位置をそのまま使用します。`--joints`、`--joint-names`、`--amplitude`、`--duration`とは併用できません。JSON形式と検証条件は[箱庭単体版の軌道JSONの形式](#軌道jsonの形式)と共通です。

外部JSONを使わず、プログラムで軌道を生成したい場合は次のいずれかを選びます。

- `control.py`を変更し、サンプル用ROS 2ワークスペースを再buildする。
- 独自ROS 2 nodeから`trajectory_msgs/msg/JointTrajectory`を`/joint_trajectory`へpublishする。

独自nodeの配置とbuild方法は[独自ROS 2 nodeの作成とbuild](../procedures/ros2/custom-nodes.md)を参照してください。

## 4. 変更内容と必要な反映操作

| 変更内容 | configure | build | 必要な実行 |
| --- | --- | --- | --- |
| `recipes/<robot>/demo-trajectory.json`の内容 | 不要 | 不要 | Runtimeを停止して`start`し直す |
| 外部JSONを箱庭単体senderへ渡す | 不要 | 不要 | `send_joint_trajectory.py --trajectory ...`を実行 |
| `tools/control/send_joint_trajectory.py` | 不要 | 不要 | Runtimeを停止して`start`し直す |
| ROS 2 controlのCLI値 | 不要 | 不要 | `ros2 run ... control`を再実行 |
| 外部JSONをROS 2 controlへ渡す | 不要 | 不要 | `ros2 run ... control --trajectory ...`を実行 |
| `ros2_packages/.../control.py` | 不要 | サンプルworkspaceを再build | install環境をsourceして`ros2 run`を再実行 |
| 独自ROS 2 package | 不要 | 独自workspaceをbuild | install環境をsourceしてnodeを実行 |

軌道やサンプルを変更しても、MJCFの再Forgeは不要です。Robot Model、joint limit、actuator設定を変更した場合の反映方法は[設定変更と反映方法](configuration-workflow.md)を参照してください。
