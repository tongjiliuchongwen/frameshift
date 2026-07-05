# 论文 gap 输入：OFA-MAS —— 一对多的多智能体拓扑设计

来源：Li et al., *OFA-MAS: One-for-All Multi-Agent System Topology Design based on Mixture-of-Experts Graph Generative Models*（arXiv:2601.12996v1, WWW '26）。

多智能体系统（MAS）的表现"高度依赖底层协作拓扑的设计"。现有图学习方法多是"一对一"：每域单训一个专门模型，泛化差、不复用跨任务结构知识。OFA-MAS 提出"一对多"：用单个通用模型，为任意自然语言任务生成自适应协作图（TAGSE 任务感知图编码 + MoE 专家混合 + 三阶段课程训练 + LLM 合成"查询–拓扑"对降标注成本）。结果在 6 个跨域 benchmark 超过一对一模型。

## 值得撬动的几个隐含假设
- "一个通用模型服务所有任务"一定比"每域一个专门模型"好（一对多 vs 一对一本身就是可反转的框定）。
- "MAS 表现高度依赖拓扑设计"——拓扑是主要矛盾，那角色定义、提示、信道内容是不是被低估了？
- 训练数据靠 LLM 合成的"查询–拓扑"对，默认这些合成拓扑是高质量 ground truth。
- 拓扑是静态 DAG，先生成后执行；评价 = benchmark 准确率 + token 成本。

## 我想要的
用系统思维 + 水平思考，把这篇工作重构成几个更清楚、可验证的研究方向——尤其想看看除了"一对一 vs 一对多"之外，还有哪些被默认下来的框定可以翻一翻。

> v0.5 三段式示例输入。完整产物见 `outputs/`（含真实 Codex 双裁审计），validator exit 0。
