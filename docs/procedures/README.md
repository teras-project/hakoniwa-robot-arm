# 実行手順

このディレクトリには、利用者が上から順に実行する手順だけを配置します。内部構造や責務の説明は[設計文書](../design/README.md)、機種別情報は[参照資料](../reference/README.md)に分離しています。

## 利用構成を選ぶ

| 利用構成 | setup | build | operation |
| --- | --- | --- | --- |
| host-only | [setup](host-only/setup.md) | [build](host-only/build.md) | [operation](host-only/operation.md) |
| host+docker | [setup](host-docker/setup.md) | [build](host-docker/build.md) | [operation](host-docker/operation.md) |
| docker-only | [setup](docker-only/setup.md) | [build](docker-only/build.md) | [operation](docker-only/operation.md) |

環境をまだ選んでいない場合は[セットアップ手順](setup.md)から開始してください。各作業の入力、ゴール、成功判定の読み方は[手順の読み方と進行ゲート](conventions.md)にまとめています。

## ROS 2操作

- [ROS 2によるアーム操作](ros2/arm-operations.md)
- [独自ROS 2 nodeの作成とbuild](ros2/custom-nodes.md)
