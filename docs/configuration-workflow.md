# 設定変更と反映方法

この文書は、Nova5のどの設定を変更すると、Forge、configure、buildのどれを再実行する必要があるかをまとめた利用者向けガイドです。各JSON項目の厳密な意味と制約は、[Robot Runtime Configuration](https://github.com/hakoniwalab/hakoniwa-robot-runtime/blob/f7db45434ae86d8fbc1c9c1682018db7c6106aa8/docs/configuration.md)と[JSON Schema](https://github.com/hakoniwalab/hakoniwa-robot-runtime/tree/f7db45434ae86d8fbc1c9c1682018db7c6106aa8/schemas)を正本とします。

## 1. 変更の基本ルール

設定と生成処理の境界は次のとおりです。

```text
モデル取得・変換設定 ── forge ──> 実行用MJCF
                                     │
Recipe設定・起動option ─ configure ──┼──> 実行用Manifest・Launcher・ROS 2 TCP設定
                                     │
C++ソース・Viewer有無 ─── build ─────┴──> Nova5実行ファイル
```

- `forge`は、上流Xacro／meshからMuJoCoモデルを作る処理です。
- `configure`は、生成済みモデルとNova5設定を選び、今回の起動構成をworkへ具体化する処理です。
- `build`は、C++実行ファイルをCMakeで構築する処理です。
- `start`は、configure済みのLauncher設定を読み込んでプロセスを起動します。

`$HAKONIWA_WORK_DIR`以下は生成物です。直接編集せず、リポジトリ内の入力を変更して対応する処理を再実行してください。

## 2. パラメータ別の反映方法

| 変更する入力 | 主な変更内容 | 必要な処理 | 主な反映先 |
| --- | --- | --- | --- |
| `sources/models/nova5/source.yaml` | 上流repository、revision、取得対象 | `nova5.py forge` | `model-forge/nova5/source/`、`build/`、`install/nova5.contact.xml` |
| `recipes/nova5/actuator.yaml` | `kp`、`dampratio` | `nova5.py forge` | `install/nova5.contact.xml`の`<actuator>` |
| `recipes/nova5/contact-excludes.yaml` | 衝突計算から除外するbody pair | `nova5.py forge` | `install/nova5.contact.xml`の`<contact>` |
| 上流URDFのjoint limit | 関節可動範囲 | `nova5.py forge` | MJCFのrange、`actuator.yaml`の`ctrlrange`、Runtime joint設定の`spec.limit` |
| `recipes/nova5/config/environment/workspace.json` | 床、照明、障害物、摩擦 | `nova5.py configure --environment ...` | `install/nova5.environment.xml` |
| `asset-manifest*.json` | 使用モデル、PDU、Endpoint、Runtime component構成 | `nova5.py configure ...` | Recipe work内の実行用Manifest |
| `config/runtime.json` | command timeoutなどRuntime共通設定 | `nova5.py configure ...`後に再起動 | 実行用Manifestから参照されるソース設定 |
| `config/actuator/`、`controller/`、`sensors/` | joint binding、制御、状態出力 | `nova5.py configure ...`後に再起動 | 実行用Manifestから参照されるソース設定 |
| `config/pdu/`、`config/endpoint/` | PDU contract、型、SHM通信 | `nova5.py configure ...`後に再起動 | 実行用Manifest。`--ros2-tcp`時はROS 2 TCP派生設定にも反映 |
| `demo-trajectory.json` | 標準デモの軌道 | 実行中なら停止して再起動 | trajectory senderが読み込む入力 |
| `--environment`、`--ros2-tcp`、`--gamepad`、`--realtime-sync-cycle-msec` | 起動モードとLauncher構成 | 同じoptionで`nova5.py configure` | `launcher.json`と関連する派生設定 |
| `--headless` | Viewerの組み込みと起動抑止 | `build --headless`と`configure --headless` | 実行ファイルと`launcher.json` |
| C++ソース、`CMakeLists.txt` | Runtime applicationの実装 | `nova5.py build` | Recipe work内の実行ファイル |
| `ros2_packages/` | ROS 2 Bridge／sample node | ROS 2 workspaceを再build | `$HAKONIWA_ROS2_WS/install/` |

表中の`install/`は、特記がない限り`$HAKONIWA_WORK_DIR/model-forge/nova5/install/`を表します。

Forge Recipe自体の依存リポジトリやPython requirementsを変更した場合だけ、`nova5.py forge`の前にBusiness Packの`tools/recipe.py configure --recipe .../nova5-model-forge.yaml`も再実行します。

### PDU contractとROS 2 TCP

PDU Definition、PDU Types、Endpoint、component bindingは、ロボットランタイムが使用する通信契約です。MJCF変換には関係しないため、変更後の再Forgeは不要です。

ただし、`--ros2-tcp`ではconfigureがソース側のPDU contractを読み、TCP Endpoint、Bridge、ROS topic bindingをworkへ生成します。この構成でPDU名、型、方向、Endpointを変更した場合は、必ず同じoptionで再configureし、Host側とROS 2側が同じ生成済み設定を使用するようにしてください。

### environmentとForge済みモデル

`--environment`を指定すると、configureはForge済みの`nova5.contact.xml`へ床、照明、障害物などを加え、`nova5.environment.xml`を生成します。そのため、次のどちらを変更した場合も再configureが必要です。

- `config/environment/workspace.json`を変更した。
- `actuator.yaml`や`contact-excludes.yaml`を変更して、基になる`nova5.contact.xml`を再Forgeした。

## 3. 標準の再生成手順

実行中のNova5を停止し、現在使用しているものと同じ`HAKONIWA_WORK_DIR`、同じconfigure optionで実行します。

### Forge対象を変更した場合

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" forge

# 利用構成に合わせてoptionを選ぶ
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
```

`--environment`を使わず、起動optionも変更していない場合、Forge後の再configureはモデル反映だけを目的とするなら不要です。ただし、手順を統一して設定の取り違えを防ぐため、通常は再configureを推奨します。

### configure対象だけを変更した場合

```bash
python "$ARM_PACK/tools/recipe/nova5.py" stop
python "$ARM_PACK/tools/recipe/nova5.py" configure \
  --ros2-tcp --environment --realtime-sync-cycle-msec 50
python "$ARM_PACK/tools/recipe/nova5.py" doctor
python "$ARM_PACK/tools/recipe/nova5.py" start
```

この場合、ForgeとC++ buildは不要です。headless構成では、上のconfigureにも`--headless`を加えます。

## 4. 生成ファイルの配置場所

### 箱庭work

```text
$HAKONIWA_WORK_DIR/
├── foundation/                                  # 箱庭共通実行環境
├── model-forge/nova5/
│   ├── source/                                  # 固定revisionから取得した上流モデル
│   ├── build/                                   # Forge途中生成物
│   └── install/
│       ├── nova5.contact.xml                    # Forgeの最終MJCF
│       └── nova5.environment.xml                # --environment時の派生MJCF
└── recipes/nova5-joint-trajectory-control/
    ├── build/bin/robot-arm-hakoniwa-asset       # C++ build成果物
    ├── config/
    │   ├── asset-manifest.json                  # 通常モデル選択時の実行用Manifest
    │   ├── asset-manifest-environment.json      # --environment時の実行用Manifest
    │   ├── launcher.json                        # configureした起動構成
    │   └── ros2-tcp/                            # --ros2-tcp時の派生設定一式
    ├── logs/                                    # asset別stdout／stderr
    └── runtime/                                 # Launcher session
```

実行用Manifestは、モデルをwork内のMJCFへ、PDU、Endpoint、Runtime component設定を本リポジトリ内のファイルへ、それぞれ絶対パスで解決します。ソース設定のコピーではありません。

### ROS 2 workspace

```text
$HAKONIWA_ROS2_WS/
├── venv/
├── native/                                      # native Endpoint library
├── build/
├── install/
├── log/
└── activate.bash
```

HostとDockerのROS 2 TCP設定の受け渡しには、次のディレクトリを`HAKONIWA_ROS2_TCP_CONFIG`として使用します。

```text
$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/ros2-tcp
```

## 5. 反映結果の確認

### 生成先とLauncherの確認

```bash
echo "$HAKONIWA_WORK_DIR"
python "$ARM_PACK/tools/recipe/nova5.py" doctor

test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
test -f "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/launcher.json"
```

`configure`の標準出力にもRecipe workspace、Launcher、viewer／headless、ROS 2 TCP、environment、realtime pacingの選択結果が表示されます。

### actuatorとcontactの確認

```bash
grep -n 'kp=\|dampratio=' \
  "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
grep -n '<exclude ' \
  "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.contact.xml"
```

`--environment`を使用する場合は、最終的に起動される派生モデルも確認します。

```bash
test -f "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.environment.xml"
grep -n 'kp=\|dampratio=\|<exclude ' \
  "$HAKONIWA_WORK_DIR/model-forge/nova5/install/nova5.environment.xml"
```

### ROS 2 TCP設定の確認

```bash
python "$ARM_PACK/tools/recipe/ros2_tcp.py" config-root --robot nova5
python "$ARM_PACK/tools/recipe/ros2_tcp.py" doctor --robot nova5

test -f "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/ros2-tcp/ros/binding.json"
test -f "$HAKONIWA_WORK_DIR/recipes/nova5-joint-trajectory-control/config/ros2-tcp/metadata.json"
```

最後は[利用構成別の動作確認手順](operation.md)に従い、軌道指令、JointState、ログを確認します。ファイル生成の成功だけでは、制御応答やHost／Docker間の接続まで保証しないためです。
