# FR5 source normalization

FR5のModel Forgeは、固定revisionから取得した原本と、変換に使用する正規化済みURDFを
`HAKONIWA_WORK_DIR`内で分離します。原本や正規化済みURDFをこのリポジトリへ追加しないでください。

## 正規化が必要な理由

対象の`FR5WM.urdf`には、定義がコメントアウトされている`gripper_Link`をchildとして参照する
`tool` fixed jointがあります。この参照は有効なlinkへ解決できないため、そのままではモデル変換へ
進めません。

Forgeはすべてのjointについてparent／childのlink参照を検査します。不正参照を検出すると、
取得済みの原本を保持したまま停止し、正規化済みURDFの配置先を表示します。

## 手順

最初に通常どおりForgeを実行します。

```bash
python "$ARM_PACK/tools/recipe/fr5.py" forge
```

初回実行は原本を次へ取得します。

```text
$HAKONIWA_WORK_DIR/model-forge/fr5/source/fairino_description/urdf/FR5WM.urdf
```

表示された不正参照を確認したら、原本を`normalized/`へコピーします。

```bash
FR5_FORGE_ROOT="$HAKONIWA_WORK_DIR/model-forge/fr5"
FR5_URDF_REL="fairino_description/urdf/FR5WM.urdf"
mkdir -p "$FR5_FORGE_ROOT/normalized/$(dirname "$FR5_URDF_REL")"
cp "$FR5_FORGE_ROOT/source/$FR5_URDF_REL" \
  "$FR5_FORGE_ROOT/normalized/$FR5_URDF_REL"
```

`normalized/fairino_description/urdf/FR5WM.urdf`を編集し、次の要素全体を除去します。

- `name="tool"`かつ`type="fixed"`のjoint
- このjoint内のchildは、定義されていない`gripper_Link`を参照しています

原本の`source/.../FR5WM.urdf`は編集しません。また、コメントアウトされている
`gripper_Link`を有効化するのではなく、不正な`tool` jointだけを除去します。

編集後、同じForgeコマンドを再実行します。

```bash
python "$ARM_PACK/tools/recipe/fr5.py" forge
```

Forgeは`normalized/`のURDFを再検査し、問題がなければ`build/`へコピーしてDAE変換、
MJCF変換、actuator追加、contact設定を継続します。再実行時に`source/`と`normalized/`は
削除されません。変換中間物は`build/`、実行用成果物は`install/`へ生成されます。

## 取得定義を変更する場合

`source.yaml`の取得元repository、固定revision、取得対象ファイルを変更する場合は、
新しい`HAKONIWA_WORK_DIR`を選び、原本の取得と正規化を最初から行ってください。
既存workの`source/`と`normalized/`は自動更新されません。これは、取得定義だけが新しく、
実際の変換入力は以前のrevisionという混在や、手編集した正規化結果の意図しない削除を防ぐためです。
