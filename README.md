# frameshift

输入一篇论文，frameshift 定位它"被夹持住、没人去动"的自由度，用水平思考算子把它们松开成
新的研究问题，每个问题先过证伪闸门，过了才按"商业行动性 × 概念深度"铺成一张可交互的二维
价值地图——**机器铺地图，人来挑方向、再定向**。这是一个 agent 驱动、零 API key、零外部依赖
（Python 标准库 + 一个 React 看板）的人机协作工具；agent 跑「定位 → 发散 → 收敛/鉴价 → 价值地图」
四工位回路（剧本见 `SKILL.md`，角色卡在 `roles/`），人在地图上决定哪几个方向值得做。

## 起前端

```bash
cd dashboard && npm install && npm run build   # 构建看板（一次即可）
cd ..                                          # 回到仓库根
python -m engine.cli serve                     # 起服务（API + 静态看板，默认 :8420）
```

然后浏览器打开 http://127.0.0.1:8420 看价值地图。

未构建看板时 `serve` 仍提供 JSON API（`/api/runs`、`/api/runs/<id>/graph|cards|map|run`），
并展示一个提示构建步骤的落地页。开发模式可在 `dashboard/` 下 `npm run dev`（已配置代理到 :8420）。
