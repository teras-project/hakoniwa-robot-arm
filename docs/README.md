# 利用ガイド

このディレクトリは、対応ロボットを初めて利用する人が、環境構築からROS 2による動作確認までを再現するための詳細手順です。製品概要、アーキテクチャ、Business Packの基本概念は[トップREADME](../README.md)を先に参照してください。

環境別の手順はNova5を例に記載しています。FR5またはSO-101を使用する場合は、[対応ロボット](reference/robots.md)を参照してロボット名や関節名を置き換えてください。

## 読み方

次のいずれか1つの利用構成を選び、`setup`、`build`、`operation`の順に実行してください。

| 利用構成 | 適したユーザー | シミュレータ | ROS 2 | 手順 |
| --- | --- | --- | --- | --- |
| host-standalone | ROS 2を使わず箱庭単体で確認する | Host | 使用しない | [setup](procedures/host-standalone/setup.md) → [build](procedures/host-standalone/build.md) → [operation](procedures/host-standalone/operation.md) |
| windows-host-standalone | Windows nativeで箱庭単体を確認する | Windows Host | 使用しない | [setup](procedures/windows-host-standalone/setup.md) → [build](procedures/windows-host-standalone/build.md) → [operation](procedures/windows-host-standalone/operation.md) |
| windows-host-docker | WindowsでMuJoCo ViewerとROS 2連携を確認する | Windows Host | Docker Desktop | [setup](procedures/windows-host-docker/setup.md) → [build](procedures/windows-host-docker/build.md) → [operation](procedures/windows-host-docker/operation.md) |
| host-ros2 | Ubuntu HostだけでROS 2連携まで確認する | Host | Ubuntu Host | [setup](procedures/host-ros2/setup.md) → [build](procedures/host-ros2/build.md) → [operation](procedures/host-ros2/operation.md) |
| host+docker | macOSからROS 2を使う | Host | Docker Container | [setup](procedures/host-docker/setup.md) → [build](procedures/host-docker/build.md) → [operation](procedures/host-docker/operation.md) |
| docker-only | Hostへ開発環境を導入せず試す | 同一Container | 同一Container | [setup](procedures/docker-only/setup.md) → [build](procedures/docker-only/build.md) → [operation](procedures/docker-only/operation.md) |

環境をまだ選んでいない場合は、[セットアップ手順](procedures/setup.md)の比較表を参照してください。

手順を実行する前に、各段階の入力、ゴール、成功判定、次段への出力の読み方を[手順の読み方と進行ゲート](procedures/conventions.md)で確認してください。

## 実行手順

[実行手順の索引](procedures/README.md)には、環境別のsetup、build、operationと、ROS 2操作手順だけを配置しています。

- [利用構成を選ぶ](procedures/setup.md)
- [手順の読み方と進行ゲート](procedures/conventions.md)
- [ROS 2によるアーム操作](procedures/ros2/arm-operations.md)
- [独自ROS 2 nodeの作成とbuild](procedures/ros2/custom-nodes.md)

## 設計文書

[設計文書の索引](design/README.md)には、手順の背景となる責務、生成物、データフローを配置しています。

- [設定変更と反映方法](design/configuration-workflow.md)
- [環境profile](design/environment-profiles.md)
- [端末ロール](design/terminal-roles.md)
- [ROS 2 Bridge基盤環境の成果物と接続関係](design/ros2-bridge-environment.md)

## 参照資料

[参照資料の索引](reference/README.md)には、対応機種とModel Forgeの情報を配置しています。

- [対応ロボット](reference/robots.md)
- [Nova5 Model Forge](reference/model-forge.md)

## ライセンス

[ライセンス情報](license/README.md)には、依存OSS、Robot Modelの取得元、調査結果、再配布方針を配置しています。

## 手順の前提

- 利用者が最初にcloneするのは`hakoniwa-business-pack`と`hakoniwa-robot-arm`です。
- その他の依存リポジトリはRecipeまたはROS 2 workspaceのbuildが必要に応じて自動取得します。
- 箱庭側の生成物は`HAKONIWA_WORK_DIR`、ROS 2側の生成物は`HAKONIWA_ROS2_WS`へ分離します。
- 取得した上流モデルや生成したMJCFはGit管理せず、選択したworkディレクトリへ配置します。
- コマンドの前に、そのコマンドをHost、Container、箱庭Workspace、通常のROS shellのどこで実行するかを確認してください。
