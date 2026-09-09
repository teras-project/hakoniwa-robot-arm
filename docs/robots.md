# 対応ロボット

ロボットごとにシミュレータの構築手順や実施手順は変わりません。
あらかじめ設定されているロボット定義ファイルやツールなどを用意しているため、それらのファイルやツールを同じ手順で利用できます。

## 対応状況

| Robot | ID | レシピ | ロボット定義ファイル(MJCF) | 確認状況 |
| --- | --- | --- | --- | --- |
| DOBOT Nova5 | `nova5` | `tools/recipe/nova5.py` | `nova5.contact.xml` | 動作確認済み |
| FAIRINO FR5 | `fr5` | `tools/recipe/fr5.py` | `FR5WM.contact.xml` | ソースとツールを公開。動作確認中。 |
| SO-101 follower | `so101` | `tools/recipe/so101.py` | `so101.xml` | ソースとツールを公開。動作確認中。 |

FR5とSO-101についても、[Nova5の環境別手順](README.md)と同じWorkspace、Foundation、Forge、configure、build、operationの流れで実行します。

個別手順はありません。ツールに渡すロボット名を変更するだけです。

## ロボット名を置き換えるポイント

ロボット名(`<robot>`) には、`nova5`、`fr5`、`so101` を指定できます。

| Nova5手順中の項目 | 共通表現 |
| --- | --- |
| `recipes/nova5/nova5-model-forge.yaml` | `recipes/<robot>/<robot>-model-forge.yaml` |
| `recipes/nova5/nova5-joint-trajectory-control.yaml` | `recipes/<robot>/<robot>-joint-trajectory-control.yaml` |
| `tools/recipe/nova5.py` | `tools/recipe/<robot>.py` |
| `model-forge/nova5/` | `model-forge/<robot>/` |
| `recipes/nova5-joint-trajectory-control/` | `recipes/<robot>-joint-trajectory-control/` |

たとえば、対象を一度だけ選んで次のように参照できます。

```bash
export ROBOT=fr5  # nova5 | fr5 | so101

python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/$ROBOT/$ROBOT-model-forge.yaml"
python "$ARM_PACK/tools/recipe/$ROBOT.py" forge

python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/$ROBOT/$ROBOT-joint-trajectory-control.yaml"
python "$ARM_PACK/tools/recipe/$ROBOT.py" configure --headless
python "$ARM_PACK/tools/recipe/$ROBOT.py" build --headless
python "$ARM_PACK/tools/recipe/$ROBOT.py" doctor
```

Viewer、`--environment`、`--ros2-tcp`、realtime pacing、start／status／stopも、同じentrypointへNova5手順と同じoptionを指定します。生成物は選択中の`HAKONIWA_WORK_DIR`以下でロボットIDごとに分離されます。

## ROS 2の関節名

ROS 2の`control` sampleプログラムでは、ジョイント名はNova5を基準に構成されています。
他のロボットの場合は、`--joint-names`を指定することで、Nova5以外のジョイント名を明示的に設定できます。

| Robot | 関節名（軌道順） |
| --- | --- |
| Nova5 | `joint1 joint2 joint3 joint4 joint5 joint6` |
| FR5 | `j1_joint j2_joint j3_joint j4_joint j5_joint j6_joint` |
| SO-101 | `shoulder_pan shoulder_lift elbow_flex wrist_flex wrist_roll gripper` |

```bash
ros2 run hakoniwa_arm_samples control \
  --joint-names j1_joint j2_joint j3_joint j4_joint j5_joint j6_joint
```

ROS 2 TCP設定の生成先も、次のようにロボット名で切り替わります。

```text
$HAKONIWA_WORK_DIR/recipes/<robot>-joint-trajectory-control/config/ros2-tcp
```

HostとDockerを接続する場合は、このロボット固有ディレクトリを`HAKONIWA_ROS2_TCP_CONFIG`へ指定します。異なるロボットの設定を混在させないでください。

## 機種固有情報とライセンス

機種固有のモデル取得元、固定revision、変換内容は`recipes/<robot>/`と`sources/models/<robot>/`で管理します。Robot Model本体はGit管理せず、Forgeによってworkへ取得・生成します。

ライセンスと再配布条件は[Robot Modelのライセンス情報](license/robot-models.md)を参照してください。特にFR5は上流ライセンスが未確定のため、モデルや正規化済みURDFを外部へ再配布しません。Forge前に必要な正規化は[FR5 source normalization](../sources/models/fr5/README.md)に従い、利用者のwork内で行います。
