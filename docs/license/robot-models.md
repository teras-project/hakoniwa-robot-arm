# Robot Modelの取得元とライセンス

## 基本方針

本リポジトリは、第三者が公開するRobot Model本体をGit管理しません。

- Robot Modelの正本は、`sources/models/<robot>/source.yaml`に記録した上流repositoryと固定revisionです。
- 上流のURDF、Xacro、MJCF、mesh、CAD、texture、ROS description packageのコピーは、本リポジトリへコミットしません。
- Forgeが取得・変換したファイルは、`$HAKONIWA_WORK_DIR/model-forge/<robot>/`へ配置します。
- 変換後のMJCFも上流モデルの派生成果物になり得るため、本リポジトリのApache License 2.0が自動的に適用されるものとは扱いません。
- 本リポジトリでは、取得定義、provenance、ライセンス調査、変換Recipe、箱庭固有設定を管理します。
- 上流ライセンスが未確定のFR5はpatchを同梱せず、利用者がwork内で原本を保持しながら正規化します。

```text
sources/models/<robot>/                    Git管理するmetadata
├── source.yaml                            取得元と固定revision
├── provenance.yaml                        出典と変換履歴（機種により配置）
├── LICENSE_INFO.yaml                      ライセンス調査
└── README.md                              work内で行う正規化手順（必要な場合）

$HAKONIWA_WORK_DIR/model-forge/<robot>/    Git管理しない取得・生成物
├── source/
├── build/
└── install/
```

## 対象モデル

| Robot Model | 上流repository | 固定revision | 確認した宣言 | 現在の再配布判定 | 詳細台帳 |
| --- | --- | --- | --- | --- | --- |
| DOBOT Nova5 | [`Dobot-Arm/DOBOT_6Axis_ROS2_V4`](https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4) | `0f21e9839888f188ac06b0a9fea622d13a29a74f` | repository: MIT、`cra_description/package.xml`: BSD | 宣言の不一致を解消するまで要確認 | [`LICENSE_INFO.yaml`](../../sources/models/nova5/LICENSE_INFO.yaml)、[`provenance.yaml`](../../sources/models/nova5/provenance.yaml) |
| FAIRINO FR5 | [`FAIR-INNOVATION/frcobot_ros2`](https://github.com/FAIR-INNOVATION/frcobot_ros2) | `60755d44d521a5ad6bee8494cc19522f8801aa20` | 利用可能な宣言を確認できず、package metadataも未確定 | モデルと正規化済みURDFは、許諾確認まで外部再配布不可。正規化は利用者のwork内で実施 | [`LICENSE_INFO.yaml`](../../sources/models/fr5/LICENSE_INFO.yaml) |
| SO-101 follower | [`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100) | `7629d2ad9853d10fb903093a33ef6114099d97e5` | Apache License 2.0 | ライセンス条件と対象資産の確認を満たす場合に限る | [`LICENSE_INFO.yaml`](../../sources/models/so101/LICENSE_INFO.yaml)、[`provenance.yaml`](../../sources/models/so101/provenance.yaml) |

共通手順のロボットIDを置き換える方法は[対応ロボット](../robots.md)にまとめています。FR5とSO-101のソースとツールは移行済みですが、本リポジトリへの移行後の実行再検証は未実施です。また、metadataを含むことは、それらのモデル本体を本リポジトリが再配布することを意味しません。

## Nova5の注意事項

Nova5の固定revisionでは、repositoryルートの`LICENSE`がMIT Licenseを示す一方、`cra_description/package.xml`は種類を特定しない`BSD`と記載しています。どの条件がNova5のURDFとmeshへ適用されるかを確定できないため、現在は次の方針です。

- 上流モデルとForge生成物を、本リポジトリや納品物へ含めない。
- 利用者自身が固定revisionから取得し、ローカルworkへForgeする。
- Forgeが上流`LICENSE`をwork内の成果物とともに保持する。
- 上流モデルまたは派生成果物を外部へ再配布する前に、権利者へ適用ライセンスを確認する。

Nova5の取得・生成手順と配置場所は[Model Forge](../model-forge.md)、反映確認は[設定変更と反映方法](../configuration-workflow.md)を参照してください。

## 固定revisionを更新する場合

revisionを変更するときは、モデル形状やファイル名だけでなく、次も再確認して台帳を更新します。

- 上流の`LICENSE`、`NOTICE`、ROS package metadata
- 取得対象となるURDF、Xacro、mesh等の個別ライセンス
- 変換後の成果物へ残すべき著作権表示と変更表示
- 再配布の可否と条件

各`LICENSE_INFO.yaml`は確認記録であり、法的助言ではありません。
