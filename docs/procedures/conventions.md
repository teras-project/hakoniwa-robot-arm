# 手順の読み方と進行ゲート

この文書は、セットアップ、build、起動・動作確認の各手順で共通に使う進め方を定義します。各環境別手順は、ここで定義する段階と成功判定に従います。

## 段階の記述形式

各作業項目は、最初に次の4項目を一つの表で示します。端末の状態を入力成果物へ混ぜません。

| 項目 | 利用者が確認すること |
| --- | --- |
| **実行端末** | `host-hako`、`host-ros-*`、通常Host terminal、Containerなど。 |
| **実行ディレクトリ** | `hakoniwa-business-pack`または`hakoniwa-robot-arm`のrepository rootなど、コマンドを実行する具体的な場所。 |
| **この作業の入力成果物** | 前段で生成・確認済みのファイル、設定、build済みRuntimeなど。端末ロールは含めない。 |
| **この作業のゴール** | この段階で新たに生成するファイル、設定、または成立させる稼働状態。 |

表の後に手順と確認方法を示します。手順書のためだけのshell制御は追加せず、ツールが実際に出すログ、`[OK]`／`[NG]`、`ls`による成果物確認、`RUNNING`／`TERMINATED`、Viewer上の動作など、利用者がそのまま比較できる条件にします。

前段の成功判定を満たしていない場合は、次段へ進みません。エラーが出た段階の入力・ゴールへ戻り、原因を解消して再実行します。

## `plan`、`configure`、`doctor`、`build`、`start`の役割

| 操作 | 役割 | 次へ進む条件 |
| --- | --- | --- |
| `plan` | Recipeを変更せずに解決し、取得・再利用・buildの予定を表示する。 | 先頭に`Recipe plan:`が表示され、`error:`で終了しない。基本手順では内容の設計判断を利用者へ求めない。 |
| `configure` | 依存を解決し、FoundationとRecipe固有の設定・Launcher・profileをworkへmaterializeする。 | ツールが出力先と選択モードを表示し、指定された成果物を`ls`で確認できる。 |
| `doctor` | Workspace、Foundation、Recipe、生成物の前提を検査する。 | 出力に`[NG]`、`MISSING`、`error:`がない。 |
| `build` | CMakeなどでRuntime実行ファイルをworkへ生成する。 | buildがerrorなく終了し、実行ファイルを`ls`で確認できる。 |
| `start` | 生成済みLauncherでRuntimeと選択した補助assetを起動する。 | 起動完了ログが表示され、`status`が`RUNNING`を返す。 |

`plan`は、依存取得や生成を始める前にRecipeを解決できることを確認する読み取り専用ゲートです。初回の`configure`前、Recipeや依存revisionを変更した後に実行します。基本手順の利用者は依存一覧の妥当性を判断せず、`Recipe plan:`が表示されてerrorなく終了することを確認します。

`doctor`は任意のトラブルシュート用コマンドではなく、段階のゴールを確認する合否ゲートです。次段へ進む前に、出力へ`[NG]`、`MISSING`、`error:`がないことを確認してください。

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
