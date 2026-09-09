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

## 4. 生成結果の確認

標準Runtimeが使用する最終成果物は次です。

```text
$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml
```

生成後に確認します。

```bash
test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

途中生成物は`build/`、取得した上流sourceは`source/`へ残るため、問題発生時の確認に利用できます。新しい成果物の生成と検証が完了するまでは既存の`install/`を保持し、成功後に切り替えます。

## 5. 周辺環境の生成

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

## 6. ライセンスと再配布

上流repositoryの`LICENSE`とROS package metadataではライセンス表記が一致していません。取得したXacro、URDF、mesh、生成MJCFを再配布する前に、[LICENSE_INFO.yaml](../sources/models/nova5/LICENSE_INFO.yaml)と[provenance.yaml](../sources/models/nova5/provenance.yaml)の確認事項を解消してください。

