# Dobot 公式 ROS 2 API と箱庭

Nova5 の公式 `dobot_msgs_v4/srv/*` を変更せずに使用します。`virtual` は Service Bridge → TCP/PDU-RPC → 箱庭の MuJoCo Asset、`real` は公式 `dobot_bringup_v4_node`、`both` は公開サービスから両者へ配送します。旧 `/joint_trajectory` topic 用の bridge はこの経路では起動しません。

## 利用手順

まず[環境別の段階2手順](../../docs/procedures/README.md#段階2ros-2から箱庭を操作)に従い、箱庭だけで公式 `dobot_demo demo` を確認してください。[共通ビルド手順](../../docs/procedures/ros2/dobot-build.md)は各環境のページで指定された端末・設定の後に実行します。実機 driver は[Ubuntu host-ros2 の追加手順](../../docs/procedures/host-ros2/real.md)でのみビルドします。

`hakoniwa_arm_samples control` と公式デモは同じ公開サービスを呼び、箱庭専用の宛先には固定されていません。同じ ROS domain に実機の同名サービスがある場合の競合や、実機での安全確認は[操作手順](../../docs/procedures/ros2/arm-operations.md)を参照してください。**公式デモの 50° 絶対移動は実機・`both` に送らないでください。**

## 仮想サービスの対応範囲

| API | 箱庭の処理 |
| --- | --- |
| RequestControl | TCP 相当モードとして受付成功 |
| EnableRobot | 現在姿勢を保持して動作許可 |
| DisableRobot | 軌道破棄・現在姿勢保持・動作指令禁止 |
| ServoJ | J1..J6 の絶対角（deg）を `t` 秒で線形補間 |
| MovJ | `mode=true` の関節角を受付順に実行。連続要求はキューに積む |
| MovL | `mode=true` の関節角を低速で順に実行。**Cartesian の直線 TCP 軌道ではない** |
| SpeedFactor | 1..100%。MovJ は最大 60 deg/s、MovL は最大 30 deg/s の割合で補間 |
| DO | 1..24 の論理出力。`time` が 1..60000 ms なら期限後に直前の値へ戻す。物理 IO・グリッパーなし |
| Stop | 軌道を破棄し、現在の実測姿勢を保持。Asset は終了しない |
| GetAngle | 現在関節角を deg の `{a,b,c,d,e,f}` で返す |
| RobotMode | 無効 4、待機 5、動作中 7 |
| ClearError | 受付成功（実機のアラーム体系は再現しない） |
| GetErrorID | 正常時の `{[]}` を返す |

`ServoJ` は次の物理更新後に受理応答を返し、到達は待ちません。`t` は 0.004..120 秒（省略時 0.1 秒）で、追加の `param_value` や範囲外角度・NaN・Inf は拒否します。`MovJ`／`MovL` の `mode=false`（TCP pose 指定）も拒否します。`res=0` は指令の受理で、到達を意味しません。到達は時間経過後の `GetAngle` または JointState で別途確認してください。内部角度と JointState は rad です。箱庭の姿勢保持は実機のブレーキ・衝突安全機能を再現しません。

## モードと同時配送

| backend | 公開サービス | 実機サービス | 箱庭サービス | JointState |
| --- | --- | --- | --- | --- |
| `real` | `/dobot_bringup_ros2/srv/*` | 同左 | なし | `/joint_states_robot` |
| `virtual` | 同上 | なし | 同左 | `/joint_states_robot` |
| `both` | 同上（mirror） | `/real/dobot_bringup_ros2/srv/*` | `/hakoniwa/dobot_bringup_ros2/srv/*` | `/real/joint_states_robot` と `/hakoniwa/joint_states_robot` |

`both` では `GetAngle`／`RobotMode`／`GetErrorID` を実機だけに問い合わせ、その他の10サービスを両方へ非同期で送ります。両サービスが準備できていることは送信前に確認しますが、受理の原子性や開始時刻の一致は保証しません。応答は通常実機の内容を使い、どちらかが失敗した場合は失敗を返します。結果は `dobot_twin/status` に出力します。timeout 時は結果が不明なため自動再送せず、両者を確認してください。`Stop` は非常停止の代わりにはなりません。

既定 launch は `virtual` です。`real`／`both` を使う場合は[実機追加手順](../../docs/procedures/host-ros2/real.md)に従い、初期姿勢と安全手段を確認してください。仮想 `MovL` や論理 `DO` の性質を実機の安全性・等価性とみなさないでください。MoveIt および13サービス以外の公式 API は検証対象外です。

Runtime 拡張 API は[上流 PR #29](https://github.com/hakoniwalab/hakoniwa-robot-runtime/pull/29)で未マージのため、Nova5 Recipe が[対応リビジョン](../../tools/dobot/versions.json)の fork commit を固定します。公式 Dobot ソースは変更しません。

## 検証済みと未検証

| 構成 | 状態 |
| --- | --- |
| macOS host+Docker（Jazzy、`virtual`） | 利用者が動作を確認。Native Asset と ROS 2 を接続し、無改変の公式デモと小動作を実行 |
| Ubuntu Native host-ros2（`virtual`／`real`／`both`） | 利用者が箱庭と実機の動作を確認 |
| Native TCP/PDU-RPC と仮想 ROS Bridge | 13サービスの結合試験と Python／C++ の単体試験を実施。mirror の Python 試験は配送ロジックの模擬試験 |
| docker-only（各 Host OS）、Windows host+Docker、macOS 以外の host+Docker | この Dobot 経路の環境別 end-to-end 動作は未確認。部分的なビルド・Container 起動を完了済みの構成も含む |
| Ubuntu 22.04／Humble | 現行 RPC の Python 3.12 以上要件により Dobot ROS ビルド不可。Python 3.10 対応と結合検証は[Issue #14](https://github.com/teras-project/hakoniwa-robot-arm/issues/14)で追跡 |

headless の Native 試験は独立した6軸モデルを使うため、Nova5 のモデル精度の検証ではありません。Core の `stop`／`start` 後に同じ Asset の物理ステップが再開することも未確認です。

## 開発時の試験

Python の設定・配送の試験:

```bash
PYTHONPATH=ros2_packages/hakoniwa_dobot python3 -m pytest -q tools/dobot/test
```

ROS 2 Jazzy の仮想 Service Bridge と Native Asset を起動した後、**同じ ROS domain に実機の同名サービスがないことを確認**してから結合試験を実行します。`real`／`both` では実行しません。

```bash
python3 tools/dobot/virtual_ros_roundtrip.py --confirm-virtual
```

Native の単体試験は [`tools/dobot/`](../../tools/dobot/) の `native_smoke.cpp` と `test/native_roundtrip.py` を使用します。
