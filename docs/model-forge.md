# Nova5 Model Forge

この文書では、DOBOT Nova5の上流Xacro／meshから、MuJoCoと箱庭ロボットランタイムが使用するMJCFを再現可能に生成する手順を説明します。

## 1. 基本方針

Nova5の上流モデル本体はこのリポジトリへコミットしません。取得元、branch、固定revision、必要ファイルは[source.yaml](../sources/models/nova5/source.yaml)、出典とライセンス確認情報は[provenance.yaml](../sources/models/nova5/provenance.yaml)で管理します。

Forgeが取得・生成するsource、build、installは、すべて次のwork所有領域へ配置します。

```text
$HAKONIWA_WORK_DIR/model-forge/nova5/
├── source/
├── build/
└── install/
```

生成済みMJCFを直接編集せず、Recipe設定または変換ツールを変更してForgeを再実行してください。

Forgeの対象外であるEnvironment、Asset Manifest、PDU、Endpoint、Runtime component設定を含む全体の区分は、[設定変更と反映方法](configuration-workflow.md)を参照してください。

## 2. Forge環境の準備

いずれかの[環境別セットアップ](setup.md)に従い、Business Packの`(hako)` Workspaceへ入ります。操作起点はComposerのルートです。

```text
(hako) .../hakoniwa-business-pack $
```

最初にRecipeの予定を確認します。

```bash
python tools/recipe.py plan \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
```

続けて、Forge用の依存リポジトリとPythonパッケージを準備します。

```bash
python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
```

このRecipeは、`hakoniwa-mbody-registry`と`hakoniwa-mujoco-robots`を宣言されたrevisionで準備します。利用者がForge専用venvを手作業で構築する必要はありません。

## 3. MJCFの生成

同じ`(hako)` Workspaceで実行します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" forge
```

Forgeは次の処理を行います。

```text
固定revisionの上流Xacroとmeshを取得
  → ROS／Gazebo固有記述をstandalone URDFへ正規化
  → URDFをMJCFへ変換
  → joint limitをRuntime設定へ同期
  → 6軸のposition actuatorを追加
  → MuJoCo simulation optionを設定
  → 不要なbody間contactを除外
  → MJCFとjoint設定を検証
  → 検証済み成果物をinstallへ切り替え
```

主な入力は次のとおりです。

| 入力 | 役割 |
| --- | --- |
| `sources/models/nova5/source.yaml` | 上流repository、固定revision、取得対象 |
| `recipes/nova5/actuator.yaml` | MuJoCo position actuator設定 |
| `recipes/nova5/contact-excludes.yaml` | contact除外設定 |
| `recipes/nova5/config/actuator/joint/` | Runtimeのjoint bindingとlimit |

## 4. `kp`と`dampratio`の調整

Nova5はMuJoCoのposition actuatorを使用します。サーボ応答は[`recipes/nova5/actuator.yaml`](../recipes/nova5/actuator.yaml)の`kp`と`dampratio`で調整します。

| 項目 | 意味 | 大きくした場合 | 小さくした場合 |
| --- | --- | --- | --- |
| `kp` | 現在位置と目標位置の誤差に対する比例ゲイン | 追従が強く速くなる一方、振動、overshoot、接触時の不安定化が起きやすくなる | 応答が穏やかになる一方、追従が遅くなり、外力に対して柔らかくなる |
| `dampratio` | position actuatorの減衰比 | 振動を抑えやすい一方、大きすぎると応答が遅くなる | 応答が振動的になり、overshootが起きやすくなる |

`dampratio: 1.0`は臨界減衰を狙う基準値です。ただし、実際の応答はリンクの質量と慣性、joint構造、`kp`、timestep、接触条件にも依存するため、値だけで応答を保証するものではありません。

現在のNova5設定は次です。

| joint | `kp` | `dampratio` |
| --- | ---: | ---: |
| joint1〜joint3 | 100.0 | 1.0 |
| joint4〜joint6 | 20.0 | 1.0 |

### 4.1 変更と再生成

`kp`または`dampratio`はForge時にMJCFへ埋め込まれます。`actuator.yaml`を変更しただけでは、すでに生成されている`nova5.contact.xml`へ反映されません。**ゲインを反映する処理は`nova5.py forge`であり、`nova5.py configure`だけでは反映されません。**

次の順序で再生成してください。

1. 実行中のNova5を停止する。
2. `recipes/nova5/actuator.yaml`の対象jointを変更する。
3. 同じ`HAKONIWA_WORK_DIR`でForgeを再実行する。
4. `--environment`を使用する場合は、同じ起動optionで`nova5.py configure`を再実行する。
5. 軌道指令、JointState、Viewerまたはログで応答と数値安定性を確認する。

Composerの`(hako)` Workspaceでのコマンド例です。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop

# recipes/nova5/actuator.yamlを編集した後
python "$ARM_PACK/tools/recipe/nova5.py" forge

# --environmentを使用している場合は、派生モデルとLauncher設定を再生成
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
```

headless構成では`configure`に`--headless`も指定します。Forge環境をまだ準備していない場合やForge Recipeの依存を変更した場合は、先に次を実行します。

```bash
python tools/recipe.py configure \
  --recipe "$ARM_PACK/recipes/nova5/nova5-model-forge.yaml"
```

`kp`／`dampratio`だけを変更した場合、Foundation、Nova5 C++ Runtime、ROS 2 workspaceの再ビルドは不要です。Runtimeは起動時に再Forge後のMJCFを読み込みます。

- `nova5.contact.xml`を直接使う構成では、ゲイン反映のための再`configure`は不要です。Launcher設定がすでにあり、起動optionを変えない場合は、そのまま再起動できます。
- `--environment`を使う構成では、再`configure`が必要です。`configure`は新しい`nova5.contact.xml`をもとに`nova5.environment.xml`を作り直します。
- 起動モード、ROS 2 TCP、headlessなどのLauncher条件を変更する場合も、対応するoptionで再`configure`します。

生成済みの`$HAKONIWA_WORK_DIR/model-forge/nova5/install/*.xml`を直接編集しないでください。次回Forgeで置き換わり、設定の由来も追跡できなくなります。

### 4.2 調整後の確認

最初は小さな変更幅と小さな軌道振幅で確認してください。[環境別の動作確認手順](operation.md)に従い、少なくとも次を確認します。

- `/joint_trajectory`の目標へ各jointが追従する。
- `/pdu/joint_states`の値が滑らかに変化する。
- Viewer上で継続的な振動や過大なovershootがない。
- `nova5-plant.err`に`simulation is unstable`、`Nan, Inf or huge value`などの数値不安定を示す出力がない。
- 接触を使用する構成では、接触時にもシミュレーションが安定している。

ログは次にあります。

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/logs/nova5-plant.out
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/logs/nova5-plant.err
```

### 4.3 `ctrlrange`との違い

`ctrlrange`はactuatorへ与えられる目標位置の範囲です。Nova5では上流URDFのjoint limitを正本とし、Forge時に`actuator.yaml`とRuntime joint設定へ同期します。可動範囲を変える目的で`ctrlrange`だけを編集しないでください。

```text
上流URDFのjoint limit
  ├── recipes/nova5/actuator.yaml の ctrlrange
  └── recipes/nova5/config/actuator/joint/ の spec.limit
```

`kp`と`dampratio`は調整対象ですが、`ctrlrange`は上流モデルとの同期対象、という違いがあります。

## 5. 生成結果の確認

標準Runtimeが使用する最終成果物は次です。

```text
$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml
```

生成後に確認します。

```bash
test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

途中生成物は`build/`、取得した上流sourceは`source/`へ残るため、問題発生時の確認に利用できます。新しい成果物の生成と検証が完了するまでは既存の`install/`を保持し、成功後に切り替えます。

## 6. 周辺環境の生成

床、背景、固定障害物はRobot Model Forgeへ含めません。[workspace.json](../recipes/nova5/config/environment/workspace.json)から、Nova5のruntime `configure`時に生成します。

```bash
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --environment --realtime-sync-cycle-msec 50
```

生成先は次です。

```text
$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.environment.xml
```

元の`nova5.contact.xml`は変更しません。ROS 2 TCPやheadlessなど、実際に使用する利用構成のoptionは各[動作確認手順](operation.md)に従って追加してください。

## 7. ライセンスと再配布

上流repositoryの`LICENSE`とROS package metadataではライセンス表記が一致していません。取得したXacro、URDF、mesh、生成MJCFを再配布する前に、[Robot Modelのライセンス情報](license/robot-models.md)、[LICENSE_INFO.yaml](../sources/models/nova5/LICENSE_INFO.yaml)、[provenance.yaml](../sources/models/nova5/provenance.yaml)の確認事項を解消してください。
