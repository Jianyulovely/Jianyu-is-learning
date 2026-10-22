# 2026-10 大模型后训练：文献版图与选题避坑

检索时间：2026-10-22。以下按「对单卡 1.5B 的人有什么用」来组织，不是综述。

---

## 一、当前六个活跃方向

### 1. Midtraining（预训练与后训练之间的新阶段）
2026 年最明显的结构性变化：**多了一个阶段**。代表工作是 NVIDIA 的开放 midtraining 配方
[Priming Base Models for Agentic Post-Training (arXiv 2610.22019)](https://arxiv.org/abs/2610.22019)：
在 256K 上下文上用数千亿 token 做「软件工程语料 + 少量 agent 轨迹」，再进 SFT/RL。
报告称 Nemotron 3.5 Lightning 上 SWE-bench Verified 60.7→64.5。

> 对你不适用：需要千亿 token 级预训练算力。但它的**结论**对你写 related work 有用——
> 「SFT 太长会损害后续 RL 的可训练性」这句话值得引用。

### 2. On-policy Distillation（OPD）——2026 年最卷的方向
学生自己生成轨迹，教师在轨迹上做 token 级监督。这一条线上半年出了很多：
[Blockwise Policy-Drift Gating for On-Policy Distillation (2606.24084)](https://ar5iv.labs.arxiv.org/html/2606.24084)、
[Can Native Safety Travel? (2610.27555)](https://arxiv.org/abs/2610.27555)（把安全能力从小的安全预训练教师「蒸馏」给大模型，1.7B 学生）、
SEED（自演化 OPD for agentic RL）。

> 对你：**需要教师模型**，1.5B 学生 + 7B 教师在 16GB 上很挤（要 4bit 教师）。
> 而且这个方向每周都有新论文，你追不上。

### 3. RL 后训练的 scaling law / 实证研究
[Scaling Behaviors of LLM RL Post-Training: An Empirical Study in Mathematical Reasoning (ACL 2026)](https://aclanthology.org/2026.acl-long.1444/)：
Qwen2.5 0.5B–72B，四个结论——大模型计算/数据效率更高；性能-资源服从可预测幂律；
RL 学习效率随规模出现**饱和**；数据受限时性能由**数据总量**而非样本多样性驱动。

> **这篇是你的方法论模板。** 它证明「不做新方法、只做受控实证」能进 ACL 正会。
> 但它扫了 0.5B 到 72B，你只能覆盖 1.5B 一个点，所以你必须换一个**它没测的变量**。

### 4. Agentic 后训练 / 长程任务
[MLExpert (2610.22344)](https://arxiv.org/abs/2610.22344)：35B MoE，用 Windowed Interaction RL 在 MLE-Bench 上把 medal rate 从 37.9% 提到 72.7%。
[AutoSFT (2610.22194)](https://arxiv.org/abs/2610.22194)：多智能体自动做 SFT 数据研究，覆盖「调比例/剪枝/修复/替换/合成」五类数据动作。

> 对你不适用：35B MoE + 多轮 agent rollout，算力差 2 个数量级。
> 但 AutoSFT 的**结论**可引用：「自动化 SFT 的收益更多来自覆盖多种数据动作，而非把单一动作做强」。

### 5. 后训练的「副作用」——能力遗忘与意外退化
这条线 2026 年很热，而且**便宜**：
- [Unintended Side Effects of Value Training in LLMs (2610.29922, 2026-10-21)](https://arxiv.org/abs/2610.29922)：为单个 Hofstede 价值维度做微调，会污染未训练的价值维度、风险偏好、社会认知、安全特质。
- [Staged Continual Adaptation (2610.27904)](https://arxiv.org/abs/2610.27904)：日本金融文档的三阶段后训练，发现阶段间**非加性**——数学蒸馏会覆盖先前学到的金融知识，域适应阶段「修」的比「装」的多。
- Sequential-LoRA forgetting / TDG-LoRA / [Frozen Factor or Spectral Band? (2610.06621)](https://arxiv.org/abs/2610.06621)：LoRA 遗忘的机理与缓解。

> **这条线对你最友好**：只需要 LoRA + 一堆 benchmark 推理，不需要 RL。
> 但已经被占了不少（见下面「已被占」）。

### 6. 评测可靠性 / 结论稳定性
- [SafetyRepro: Configuration-Conditional Rank Instability on Alignment Benchmarks (2605.25492)](https://arxiv.org/abs/2605.25492)：安全榜单上的**排名**会随配置变化而不稳定。
- [Quagmires in SFT-RL Post-Training: When High SFT Scores Mislead (2510.01624)](https://arxiv.org/abs/2510.01624)：SFT 分数高反而误导后续 RL。

> 这条线是「元研究」，写作门槛低、算力低，但**审稿人对「你没有真的改进任何东西」很敏感**，需要极强的方法学严谨性。

---

## 二、已被占的选题（**重点：别做这些**）

我原本想推荐给你的四个方向，检索后发现全部已有 2025–2026 的工作。列在这里，省你两周：

| 你可能会想到的题目 | 已有工作 | 状态 |
|---|---|---|
| SFT vs RL 谁更好 / 计算匹配对比 | [Quagmires in SFT-RL (2510.01624)](https://arxiv.org/abs/2510.01624)、SFT vs RL (2609.16059)、[Ablation Analysis: Effectiveness of RL Fine-Tuning (2505.19501)](https://export.arxiv.org/pdf/2505.19501) | ❌ 红海 |
| SFT 与 RL 的**顺序/交错** | [Interleaving SFT and RL with Buffer (2510.04454)](https://browse-export.arxiv.org/pdf/2510.04454) | ❌ 已有 |
| 数据选择在小模型上是否有效 | [Capacity-Dependent Effects of Data Selection for Reasoning](https://aipulselab.tech/news/capacity-dependent-effects-of-data-selection-for-reasoning-6c8352) | ❌ 已有（「依赖模型容量」正是你想说的） |
| LoRA 顺序微调的灾难性遗忘 | Sequential-LoRA Rank-4 Occlusion (Zenodo 21309879)、TDG-LoRA、[Frozen Factor or Spectral Band? (2610.06621)](https://arxiv.org/abs/2610.06621) | ❌ 已有 |
| 后训练后 pass@k 多样性下降 | 2025 年起已有多篇（RLVR 收缩输出分布） | ❌ 红海 |
| 训练算力 vs 测试时算力如何分配 | [Train-to-Test (T²) Scaling Laws](https://snorkel.ai/blog/train-to-test-scaling-laws-reading-group/)、Snell et al. 2024 | ⚠️ 已有框架，但**后训练语境下的等预算横评**仍有缝 |
| 榜单排名不稳定 / 配置敏感 | [SafetyRepro (2605.25492)](https://arxiv.org/abs/2605.25492) | ⚠️ 已有，慎入 |

**这张表就是这次搜索最值钱的东西。** 上面任何一行，你如果闷头做两周，大概率是在重写别人的 abstract。

---

## 三、留给你的缝在哪

把「已被占」和「你的 16GB」两个约束叠在一起，剩下的空间是：

> **在 1.5B 这个具体规模上，把「可花掉的那点算力」当成一等公民，横向比较「训练侧」和「推理侧」的投入产出。**

具体说：现有工作大多**各自报自己方法的增益**，很少有人在**同一个 GPU 小时预算**下，
把 SFT / 拒绝采样自训练 / DPO / best-of-N / 自洽投票放在一起比，并明确回答
「我这 10 个小时该花在训模型还是花在采样上」。

这就是 `docs/02-topic-proposals.md` 的 **P1**。它的新颖性不在方法，在**预算核算的严谨性**和**规模定位**（所有人都往 7B+ 跑，1.5B 反而没人系统测）。

---

## 四、写作时要引的骨架文献

按论文结构给你排好了，`paper/refs.bib` 里已经建好条目：

- **后训练全景**：[Post-training Survey (2503.06072)](https://ar5iv.labs.arxiv.org/html/2503.06072)、[LLM Post-Training: A Deep Dive into Reasoning LLMs (2502.21321)](https://huggingface.co/papers/2502.21321)
- **对齐基础**：InstructGPT (Ouyang 2022)、DPO (Rafailov 2023)、PPO (Schulman 2017)
- **推理侧后训练**：DeepSeek-R1 (2501.12948)、Tülu 3 (2411.15124)
- **自训练**：STaR (Zelikman 2022)、RAFT (Dong 2023)
- **推理时扩展**：Self-Consistency (Wang 2022)、Snell et al. 2024
- **SFT 与 RL 的关系**：[SFT Memorizes, RL Generalizes (2501.17161)](https://arxiv.org/abs/2501.17161)、[Does RL Really Incentivize Reasoning Beyond the Base Model? (2504.13837)](https://arxiv.org/abs/2504.13837)
- **基准**：GSM8K、MATH、MATH-500、IFEval、AlpacaEval
- **高效微调**：LoRA、QLoRA
- **基座**：Qwen2.5 (2412.15115)

> ⚠️ `refs.bib` 里标了 `% VERIFY` 的条目，是我凭记忆写的 arXiv 编号，**投稿前请在 arXiv 上逐条核对**。标了 `% OK` 的是本次检索中实际打开过页面的。
