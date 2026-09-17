# 設計文書

このディレクトリには、Recipe、生成物、端末環境、ROS 2接続の責務とデータフローを配置します。コマンドを順番に実行する手順は[実行手順](../procedures/README.md)を参照してください。

- [設定変更と反映方法](configuration-workflow.md): Forge、configure、buildの責務と生成先
- [環境profile](environment-profiles.md): 環境変数、共通profile、端末別profileの責務
- [端末ロール](terminal-roles.md): 箱庭単体とHost ROS 2連携に分けた端末構成
- [ROS 2 Bridge基盤環境の成果物と接続関係](ros2-bridge-environment.md): ROS 2 Bridge、Endpoint、TCP、SHM、Runtimeの接続
- [JointTrajectoryサンプル](trajectory-control-samples.md): 箱庭単体版とROS 2版の配置、軌道設定、実行方法
