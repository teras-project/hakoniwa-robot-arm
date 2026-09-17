# 端末ロール

利用構成ごとに必要な端末が異なるため、説明を分離しています。実行する構成だけを参照してください。

- [箱庭単体の端末ロール](terminal-roles-standalone.md): `host-hako`の1端末
- [Host ROS 2連携の端末ロール](terminal-roles-ros2.md): Runtime、Bridge、monitor、controlの4端末とbuild端末
- [host+dockerの端末ロール](../procedures/host-docker/operation.md): Host Runtimeと、Container内のBridge、monitor、control
- [docker-onlyの端末ロール](../procedures/docker-only/operation.md): 同じContainer内のRuntime、Bridge、monitor、control

各profileが設定するパスと生成時点は[環境profile](environment-profiles.md)を参照してください。
