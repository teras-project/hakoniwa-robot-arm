# 利用ガイド

このディレクトリは、DOBOT Nova5を初めて利用する人が、環境構築からROS 2による動作確認までを再現するための詳細手順です。製品概要、アーキテクチャ、Business Packの基本概念は[トップREADME](../README.md)を先に参照してください。

## 読み方

次のいずれか1つの利用構成を選び、同じ列の`setup`、`build`、`operation`を上から順番に実行してください。異なる列の手順やworkディレクトリを混ぜないでください。

| 利用構成 | 適したユーザー | シミュレータ | ROS 2 | 手順 |
| --- | --- | --- | --- | --- |
| host-only | Ubuntuをメイン環境として使う | Host | Ubuntu Host（任意） | [setup](setup-host-only.md) → [build](build-host-only.md) → [operation](operation-host-only.md) |
| host+docker | macOSからROS 2を使う | Host | Docker Container | [setup](setup-host-docker.md) → [build](build-host-docker.md) → [operation](operation-host-docker.md) |
| docker-only | Hostへ開発環境を導入せず試す | 同一Container | 同一Container | [setup](setup-docker-only.md) → [build](build-docker-only.md) → [operation](operation-docker-only.md) |

環境をまだ選んでいない場合は、[セットアップ手順](setup.md)の比較表を参照してください。

## 共通ガイド

- [セットアップ手順](setup.md): 利用構成の選択、共通前提、workの分離
- [ビルド手順](build.md): Viewerあり／headlessの選択と生成先
- [起動・動作確認手順](operation.md): ROSトピック、期待結果、終了方法
- [Nova5 Model Forge](model-forge.md): 上流モデルの取得、変換、生成物

## 手順の前提

- 利用者が最初にcloneするのは`hakoniwa-business-pack`と`hakoniwa-robot-arm`です。
- その他の依存リポジトリはRecipeまたはROS 2 workspaceのbuildが必要に応じて自動取得します。
- 箱庭側の生成物は`HAKONIWA_WORK_DIR`、ROS 2側の生成物は`HAKONIWA_ROS2_WS`へ分離します。
- 取得した上流モデルや生成したMJCFはGit管理せず、選択したworkディレクトリへ配置します。
- コマンドの前に、そのコマンドをHost、Container、箱庭Workspace、通常のROS shellのどこで実行するかを確認してください。
