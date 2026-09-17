# 手順の読み方と進行ゲート

この文書は、セットアップ、build、起動・動作確認の各手順で共通に使う進め方を定義します。各環境別手順は、ここで定義する段階と成功判定に従います。

## 段階の記述形式

各作業項目は、次の順で説明します。

| 項目 | 利用者が確認すること |
| --- | --- |
| **実行場所** | `host-hako`、`host-ros-*`、Containerなど、どの端末ロール・どの作業ディレクトリで実行するか。 |
| **入力** | 前段で確認済みの環境、設定、生成物。作業を開始してよい前提。 |
| **ゴール** | その段階で成立させる状態。 |
| **手順** | ゴールを満たすためのコマンドと操作。 |
| **成功判定** | ログ、`doctor`、生成物、Viewer、topicなどで確認できる客観的な条件。 |
| **次段への出力** | ゴール達成によって得られ、次の作業項目の入力になる状態または生成物。 |

前段の成功判定を満たしていない場合は、次段へ進みません。エラーが出た段階の入力・ゴールへ戻り、原因を解消して再実行します。

## `plan`、`configure`、`doctor`、`build`、`start`の役割

| 操作 | 役割 | 次へ進む条件 |
| --- | --- | --- |
| `plan` | Recipeによる取得、再利用、buildの予定を変更せずに表示する。 | 対象Recipe、依存repository、予定される処理が意図どおりであることを利用者が確認する。 |
| `configure` | 依存を解決し、FoundationとRecipe固有の設定・Launcher・profileをworkへmaterializeする。 | コマンドが正常終了し、表示されたworkと生成対象が選択した構成と一致する。 |
| `doctor` | Workspace、Foundation、Recipe、生成物の前提を検査する。 | 必須項目がすべて`[OK]`である。`[NG]`やerrorがある場合は先へ進まない。 |
| `build` | CMakeなどでRuntime実行ファイルをworkへ生成する。 | 実行ファイルが期待するwork配下にあり、必要なbuild検査が成功する。 |
| `start` | 生成済みLauncherでRuntimeと選択した補助assetを起動する。 | `status`が`RUNNING`となり、段階固有の動作確認が成功する。 |

`plan`は、依存取得や生成を始める前の計画確認ゲートです。初回の`configure`前、Recipeや依存revisionを変更した後、または予定外の取得・再buildを避けたいときに必ず実行します。

`doctor`は任意のトラブルシュート用コマンドではなく、段階のゴールを確認する合否ゲートです。次段へ進む前に、対象手順で指定された`doctor`がすべて`[OK]`であることを確認してください。

## 最小の段階例

```text
入力
  clone済みのComposerとRobot Arm repository
  ↓
plan
  Recipeと依存取得予定を確認
  ↓
configure
  Foundation、Recipe設定、Launcher、role profileをworkへ生成
  ↓
doctor
  WorkspaceとRecipeの必須項目がすべて[OK]
  ↓
出力
  buildを開始できる設定済みwork
```

この出力が、次のbuild段階の入力になります。buildが成功して実行ファイルが生成されると、それが起動・動作確認段階の入力になります。

## 期待結果の示し方

各手順は、長いログの全文ではなく、次のいずれかを成功判定として示します。

- `doctor`の全`[OK]`
- `status`の`RUNNING`または`TERMINATED`
- 生成したファイルのパスと存在確認
- Viewer上の期待挙動
- ROS 2 topic、message、monitor出力

期待結果に一致しない場合に確認するログ、再実行する段階、関連する設定文書も、各環境別手順に併記します。
