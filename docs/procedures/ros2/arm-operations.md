# ROS 2によるアーム操作

この文書は、対応するRobot Modelで共通のROS 2操作を説明します。host-ros2、host+docker、docker-onlyの各手順は、Bridgeへ接続できる端末を用意するところまでを扱い、monitorとcontrolの意味・期待結果はこの文書を正本とします。

[手順一覧](../README.md)に戻る。以下のコマンドは、選択した構成のROS 2 monitor／control端末で、基盤環境とサンプルの`setup.bash`を有効にしてから実行します。

## 入力とゴール

- **入力**: RuntimeとHost側Bridgeが`RUNNING`であり、ROS Bridgeが対象bindingを使って起動していること。
- **ゴール**: `JointTrajectory`指令でアームを動かし、その結果を`JointState`で観察できること。
- **成功判定**: control送信後、Viewer上の動作とmonitorに表示される関節位置の変化が一致すること。

## monitor: 関節状態を観察する

`monitor`は`/pdu/joint_states`から`sensor_msgs/msg/JointState`を受信し、`joint1=...`から`joint6=...`の形式で関節位置を表示します。これは、Runtimeが状態をPDUへ出力し、ROS BridgeがROS topicへ変換できていることを確認する操作です。

実行するコマンド（ROS 2 monitor端末）:
```bash
ros2 topic info /pdu/joint_states
ros2 run hakoniwa_arm_samples monitor --topic /pdu/joint_states
```

終了するまで表示を続けます。最初の1メッセージだけ確認したい場合は`--once`を指定します。

## control: 軌道を送信する

`control`は`/joint_trajectory`へ`trajectory_msgs/msg/JointTrajectory`を1回publishします。既定では6関節を対象に、4点からなる正弦波状の目標位置列を送信します。

サンプルのソース配置、箱庭単体版との違い、軌道の生成方法、変更時の再build条件は[JointTrajectoryサンプル](../../design/trajectory-control-samples.md)を参照してください。

実行するコマンド（ROS 2 control端末）:
```bash
ros2 topic info /joint_trajectory
ros2 run hakoniwa_arm_samples control \
  --topic /joint_trajectory --joints 6 --amplitude 0.15 --duration 2.0
```

| option | 意味 | この例 |
| --- | --- | --- |
| `--topic` | 送信先のJointTrajectory topic | `/joint_trajectory` |
| `--trajectory` | 箱庭単体版と同じ形式の外部軌道JSON。指定時は軌道生成optionと併用不可 | 未指定 |
| `--joints` | `joint1`から順に対象とする関節数 | `6` |
| `--amplitude` | 各関節の目標位置を作る正弦波の振幅。JointTrajectoryの関節位置として通常radで扱う。 | `0.15` |
| `--duration` | 連続する軌道点の時間間隔（sec）。4点の最終点は`3 × duration`秒となる。 | `2.0` |

`--amplitude`は小さな値から試してください。Robot Modelのjoint limitを超える目標を指定しないようにし、Viewerとmonitorを同時に確認します。関節名が連番でないRobot Modelでは、`--joints`の代わりに`--joint-names`へ実際の関節名を列挙します。

任意の軌道JSONを送る場合は、`--joints`、`--joint-names`、`--amplitude`、`--duration`を付けずに実行します。事前に送信するJSONを用意してください。

実行するコマンド（ROS 2 control端末。実行後にJSONの絶対パスを入力してEnter）:
```bash
printf '軌道JSONの絶対パス: '
IFS= read -r TRAJECTORY_JSON
```

実行するコマンド（同じROS 2 control端末。指定したファイルの存在を確認してから送信）:
```bash
if test -f "$TRAJECTORY_JSON"; then
  ros2 run hakoniwa_arm_samples control \
    --topic /joint_trajectory \
    --trajectory "$TRAJECTORY_JSON"
else
  printf '軌道JSONが見つかりません: %s\n' "$TRAJECTORY_JSON" >&2
fi
```

JSONの配置、形式、変更方法は[JointTrajectoryサンプル](../../design/trajectory-control-samples.md)を参照してください。

## カスタマイズ

より複雑な軌道を試す場合は、`hakoniwa_arm_samples.control`を変更するのではなく、ROS 2の任意のnodeから同じ`trajectory_msgs/msg/JointTrajectory`を`/joint_trajectory`へpublishできます。独自nodeでも、次を守ります。

- `joint_names`と各pointのposition配列の長さを一致させる。
- Robot Modelのjoint limitを尊重する。
- 実行結果を`/pdu/joint_states`とViewerで確認する。

独自packageを別のROS 2ワークスペースへbuild・実行する手順は、[独自ROS 2 nodeの作成とbuild](custom-nodes.md)を参照してください。
