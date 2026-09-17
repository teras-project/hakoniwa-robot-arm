# 箱庭単体の端末ロール

箱庭単体では、`host-hako`の1端末だけを使用します。

| ロール | prompt | 役割 |
| --- | --- | --- |
| `host-hako` | `(host-hako) (hako)` | 箱庭Workspace、Foundation、Forge、Runtime、MuJoCo Viewerを操作する。 |

Robot Arm repositoryの通常Host terminalから次を実行すると、`host-hako`のchild shellが開きます。

```bash
source profiles/tool-env/enter-host-hako.bash
```

セットアップから終了まで、この端末で操作します。具体的な実行順序は[箱庭単体手順](../procedures/host-standalone/setup.md)を参照してください。
