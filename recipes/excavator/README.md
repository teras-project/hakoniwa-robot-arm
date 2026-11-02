# MathScavator9000 Excavator Recipe

MathWorksの公開MathScavator9000モデルから、移動可能な6輪差動走行モデルと4関節の箱庭Runtimeを生成・実行するRecipeです。

## 確認状況

macOS Hostで、mobile excavatorのheadless実行（6輪差動Twist走行・停止、続く4関節JointTrajectory、JointState出力、数値安定性）を確認済み。移動モデルのViewer表示は未確認。掘削worksite（bucket proxy、terrain hfield、soil）は実験的で、bucket collision calibrationの`accepted`が必要。Docker／Ubuntu／Windows／ROS 2経路は未確認。

## 実行手順

fresh checkoutからのFoundation、Runtime Recipe、Model Forge、headless build、smoke、停止は公開手順を正本とします。

- [macOS／Ubuntu 24.04 native／WSL2 Ubuntu 24.04](../../docs/procedures/excavator/host-standalone/setup.md)
- [Windows native PowerShell](../../docs/procedures/excavator/windows-host-standalone/setup.md)

Windows native／WSL2：確認中。Viewer実行：未確認。

## Recipe固有ファイルとデモ

`asset-manifest.json`は通常のmobile model、`asset-manifest-digging.json`は実験的worksiteを選びます。`demo-drive.json`は6輪差動Twist、`demo-trajectory.json`は4関節軌道、`demo-manual.json`は手動デモです。PS5 mappingは`ps5-controller-macos.json`で管理します。

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
