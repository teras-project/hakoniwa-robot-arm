# 対応ロボット

ロボットごとにシミュレータの構築手順や実施手順は変わりません。
あらかじめ設定されているロボット定義ファイルやツールなどを用意しているため、それらのファイルやツールを同じ手順で利用できます。

## 対応状況

| Robot | ID | レシピ | ロボット定義ファイル(MJCF) | 確認状況 |
| --- | --- | --- | --- | --- |
| DOBOT Nova5 | `nova5` | `tools/recipe/nova5.py` | `nova5.contact.xml` | Ubuntu 24.04 native host-ros2、Windows 11 native host-standalone／host+Docker（Jazzy）、macOS host+docker（Jazzy）、Linux arm64 docker-only（Humble／Jazzy）で動作確認済み。 |
| FAIRINO FR5 | `fr5` | `tools/recipe/fr5.py` | `FR5WM.contact.xml` | ソースとツールを公開。動作確認中。 |
| SO-101 follower | `so101` | `tools/recipe/so101.py` | `so101.xml` | ソースとツールを公開。動作確認中。 |
| MathScavator9000 Excavator | `excavator` | `tools/recipe/excavator.py` | `excavator.mobile.xml` | macOS host、WSL2 Ubuntu 24.04、Windows 11 native（いずれもheadless）で走行を動作確認済み。Viewer表示は未確認、掘削は実験的。[実行手順](../procedures/excavator/host-standalone/setup.md)。 |

FR5とSO-101についても、基本的な実行手順は[Nova5の環境別手順](../README.md)と共通です。ただしFR5では、初回Model Forge時に機種固有のURDF正規化が必要です。詳細は[FR5 source normalization](../../sources/models/fr5/README.md)を参照してください。

## ロボット名を置き換えるポイント

ロボット名(`<robot>`) には、`nova5`、`fr5`、`so101`、`excavator` を指定できます。

| Nova5手順中の項目 | 共通表現 |
| --- | --- |
| `recipes/nova5/nova5-model-forge.yaml` | `recipes/<robot>/<robot>-model-forge.yaml` |
| `recipes/nova5/nova5-joint-trajectory-control.yaml` | `recipes/<robot>/<robot>-joint-trajectory-control.yaml` |
| `tools/recipe/nova5.py` | `tools/recipe/<robot>.py` |
| `model-forge/nova5/` | `model-forge/<robot>/` |
| `recipes/nova5-joint-trajectory-control/` | `recipes/<robot>-joint-trajectory-control/` |

たとえば、対象を一度だけ選んで次のように参照できます。`ROBOT`には`nova5`、`fr5`、`so101`、`excavator`のいずれかを指定します。以下は`fr5`の例です。

```bash
export ROBOT=fr5

python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/$ROBOT/$ROBOT-model-forge.yaml"
python "$ARM_PACK/tools/recipe/$ROBOT.py" forge

python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/$ROBOT/$ROBOT-joint-trajectory-control.yaml"
python "$ARM_PACK/tools/recipe/$ROBOT.py" configure --headless
python "$ARM_PACK/tools/recipe/$ROBOT.py" build --headless
python "$ARM_PACK/tools/recipe/$ROBOT.py" doctor
```

その他のオプションもNova5と共通です。
生成されるファイルは、ロボット名ごとに `HAKONIWA_WORK_DIR`配下のディレクトリ内に作成されます。

## Robot Model の関節名

関節名は各モデルの軌道JSONや JointState に使用します。ROS 2 の
`hakoniwa_arm_samples control` は Dobot 公式サービスによる **Nova5 専用**の
小動作サンプルで、他のロボットの関節名を `--joint-names` で指定する機能はありません。

| Robot | 関節名（軌道順） |
| --- | --- |
| Nova5 | `joint1 joint2 joint3 joint4 joint5 joint6` |
| FR5 | `j1_joint j2_joint j3_joint j4_joint j5_joint j6_joint` |
| SO-101 | `shoulder_pan shoulder_lift elbow_flex wrist_flex wrist_roll gripper` |
| MathScavator9000 | `base_chassis_joint chassis_boom_joint boom_stick_joint stick_bucket_joint` |

## MathScavator9000固有情報

公開MathScavator9000 URDFを固定revisionから取得し、mesh正規化、4軸position actuator、6輪差動base、隣接contact除外を加えて`excavator.mobile.xml`を生成します。bucket proxy、HField、50個の剛体球によるsoilを含む`excavator.soil.xml`は掘削操作用の実験的PoCで、土質力学モデルではありません。

Nova5 の ROS 2 操作は[公式サービスの手順](../procedures/ros2/arm-operations.md)を参照してください。

ROS 2 TCP設定の生成先も、次のようにロボット名で切り替わります。

```text
$HAKONIWA_WORK_DIR/recipes/<robot>-joint-trajectory-control/config/ros2-tcp
```

HostとDockerを接続する場合は、このロボット固有ディレクトリを`HAKONIWA_ROS2_TCP_CONFIG`へ指定します。異なるロボットの設定を混在させないでください。

## 機種固有情報とライセンス

機種固有のモデル取得元、固定revision、変換内容は`recipes/<robot>/`と`sources/models/<robot>/`で管理します。Robot Model本体はGit管理せず、Forgeによってworkへ取得・生成します。

ライセンスと再配布条件は[Robot Modelのライセンス情報](../license/robot-models.md)を参照してください。特にFR5は上流ライセンスが未確定のため、モデルや正規化済みURDFを外部へ再配布しません。Forge前に必要な正規化は[FR5 source normalization](../../sources/models/fr5/README.md)に従い、利用者のwork内で行います。
