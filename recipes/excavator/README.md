# MathScavator9000 Excavator Recipe

MathWorksの公開MathScavator9000モデルから、移動可能な6輪差動走行モデルと4関節の箱庭Runtimeを生成・実行するRecipeです。

## 確認状況

macOS Hostで、mobile excavatorのheadless実行（6輪差動Twist走行・停止、続く4関節JointTrajectory、JointState出力、数値安定性）を確認済み。移動モデルのViewer表示は未確認。掘削worksite（bucket proxy、terrain hfield、soil）は実験的で、bucket collision calibrationの`accepted`が必要。Docker／Ubuntu／Windows／ROS 2経路は未確認。

## 前提

[箱庭単体セットアップ](../../docs/procedures/host-standalone/setup.md)に従い、`hakoniwa-business-pack`と`hakoniwa-robot-arm`を同じ親ディレクトリへcloneし、`host-hako` Workspaceへ入ってください。以下は`hakoniwa-robot-arm`のrepository rootで実行します。

## Forge

Composerで上流モデルとForge依存を準備します。

```bash
cd ../hakoniwa-business-pack
python tools/recipe.py plan \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-model-forge.yaml
python tools/recipe.py configure \
  --recipe ../hakoniwa-robot-arm/recipes/excavator/excavator-model-forge.yaml
cd ../hakoniwa-robot-arm
bash tools/install-excavator-bucket-proxy-tools.bash
python tools/recipe/excavator.py forge
test -f "$HAKONIWA_WORK_DIR/model-forge/excavator/install/excavator.mobile.xml"
```

最後の`test`が終了コード0ならForge成功です。

## headlessデモ

6輪差動Twistの走行と停止に続けて4関節JointTrajectoryを送り、RuntimeのJointStateと数値安定性を確認します。

```bash
python tools/recipe/excavator.py configure --headless
python tools/recipe/excavator.py build --headless
python tools/recipe/excavator.py doctor
python tools/recipe/excavator.py smoke
```

`smoke`がTwist完了、非ゼロwheel control、安定したground motion、command受付、数値不安定なしをすべて`[OK]`で報告すれば成功です。

## Viewerと手動操作

移動モデルのViewer表示は未確認です。確認する場合は、通常デモ、JSON定義のmanual demo、PS5 controllerのいずれかを選びます。

```bash
python tools/recipe/excavator.py configure --manual-demo
python tools/recipe/excavator.py build
python tools/recipe/excavator.py start
python tools/recipe/excavator.py status
python tools/recipe/excavator.py stop
```

PS5 controllerを使う場合は、[gamepadのセットアップ](../../docs/procedures/host-standalone/setup-gamepad.md)を完了してから`configure --gamepad`を使用します。

## 実験的な掘削worksite

掘削worksiteは、[`bucket-collision.yaml`](bucket-collision.yaml)の`calibration.status`が`accepted`の場合だけ生成できます。bucket proxy、terrain hfield、簡易剛体soilをmaterializeします。

```bash
python tools/recipe/excavator.py bucket-proxy
python tools/recipe/excavator.py configure --headless --digging-worksite
python tools/recipe/excavator.py build --headless
python tools/recipe/excavator.py doctor
```

設定値と生成物は[`config/environment/README.md`](config/environment/README.md)を参照してください。soilは土質力学モデルではなく、掘削操作の実験用PoCです。

## ライセンス

上流MathScavator9000 assetsはBSD-3-Clauseです。再配布条件と固定revisionは[Robot Modelのライセンス情報](../../docs/license/robot-models.md)と[`LICENSE_INFO.yaml`](../../sources/models/excavator/LICENSE_INFO.yaml)を確認してください。
