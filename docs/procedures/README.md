# 実行手順

このディレクトリには、利用者が上から順に実行する手順だけを配置します。内部構造や責務の説明は[設計文書](../design/README.md)、機種別情報は[参照資料](../reference/README.md)に分離しています。

## 段階1：箱庭単体（ROS 2なし）

| 利用構成 | setup | build | operation |
| --- | --- | --- | --- |
| host-standalone（Ubuntu／macOS） | [setup](host-standalone/setup.md) | [build](host-standalone/build.md) | [operation](host-standalone/operation.md) |
| host-standalone + PS5 gamepad（Ubuntu／macOS） | [setup](host-standalone/setup-gamepad.md) | [build](host-standalone/build-gamepad.md) | [operation](host-standalone/operation-gamepad.md) |
| windows-host-standalone（Windows native） | [setup](windows-host-standalone/setup.md) | [build](windows-host-standalone/build.md) | [operation](windows-host-standalone/operation.md) |
| Excavator host-standalone（macOS／Ubuntu 24.04／WSL2） | [setup](excavator/host-standalone/setup.md) | [build](excavator/host-standalone/build.md) | [operation](excavator/host-standalone/operation.md) |
| Excavator windows-host-standalone | [setup](excavator/windows-host-standalone/setup.md) | [build](excavator/windows-host-standalone/build.md) | [operation](excavator/windows-host-standalone/operation.md) |

## 段階2：ROS 2から箱庭を操作

環境を1つ選び、setup → build → operation の順に進みます。各環境とも箱庭上で無改変の公式 `dobot_demo demo` を確認することがゴールです。

| 利用構成 | setup | build | operation |
| --- | --- | --- | --- |
| host-ros2（Ubuntu） | [setup](host-ros2/setup.md) | [build](host-ros2/build.md) | [operation](host-ros2/operation.md) |
| host+docker（macOS） | [setup](host-docker/setup.md) | [build](host-docker/build.md) | [operation](host-docker/operation.md) |
| windows-host-docker | [setup](windows-host-docker/setup.md) | [build](windows-host-docker/build.md) | [operation](windows-host-docker/operation.md) |
| docker-only（Ubuntu／macOS／Windows） | [setup](docker-only/setup.md) | [build](docker-only/build.md) | [operation](docker-only/operation.md) |

ROS launch の既定は箱庭（`virtual`）です。Windows native Host + Docker の[専用 Asset 手順](windows-host-docker/build.md)は未検証なので、各段階の成功判定を確認してください。環境をまだ選んでいない場合は[セットアップ手順](setup.md)から開始してください。各作業の入力、ゴール、成功判定の読み方は[手順の読み方と進行ゲート](conventions.md)にまとめています。

## 段階3：Ubuntu host-ros2 で実機にも接続（発展）

段階2の host-ros2 を完了後、[実機 driver の追加と `real`／`both` への切り替え](host-ros2/real.md)へ進みます。公式デモの絶対角移動を実機へ送らないでください。

## デモ

- [SO-101 キューブ把持デモ](so101-grasp-demo.md)（host-standalone。キューブをつかんで持ち上げ、横へ置く）

## ROS 2操作

- [ROS 2によるアーム操作](ros2/arm-operations.md)
- [Dobot 仮想サービスの共通ビルド手順](ros2/dobot-build.md)
- [独自ROS 2 nodeの作成とbuild](ros2/custom-nodes.md)
