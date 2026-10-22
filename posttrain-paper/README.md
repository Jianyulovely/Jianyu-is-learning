# 大模型后训练：从「想要一篇论文」到「能投的论文」

> 时间锚点：**2026-10-22**。本文件里所有文献判断都基于这个时间点的检索结果，不是模型记忆。

---

## 0. 先说一句实话

你要的「直接给我一篇关于后训练的论文」，我做不到两件事：

1. **我不能给你一篇现成的、能署你名的论文。** 现成的论文都有作者，署名就是学术不端。
2. **我不会给你编实验数据。** 论文能中被接收，靠的是真实跑出来的数字。我可以把代码、协议、论文骨架全搭好，但 `Table 2` 里的数字必须是你自己 GPU 跑出来的。编数字的论文，查重/复现/审稿任何一环都可能炸，代价远大于收益。

我能给你的、也确实算「成果」的东西：

| 交付物 | 位置 | 作用 |
|---|---|---|
| 文献版图 + **已被占的选题清单** | `docs/01-literature-map.md` | 让你不撞车。这是本次搜索最大的价值 |
| **3 个可投的选题方案**（含算力预算/风险/venue） | `docs/02-topic-proposals.md` | 3 分钟选定方向 |
| 实验协议（控制变量、预算核算、统计规范） | `docs/03-experiment-protocol.md` | 审稿人挑不出方法学毛病 |
| **能跑的代码**（SFT / DPO / 采样 / 评测 / 出表） | `src/` | 今晚就能跑 smoke test |
| 解析器回归测试（18 条，已全过） | `tests/test_parsers.py` | 保证论文里每个数字的抽取口径不错 |
| ACL 格式论文骨架（**已编译成 6 页 PDF**） | `paper/main.tex`, `paper/main.pdf` | 空壳，等你填真数据 |
| 参考文献核对清单 | `paper/REF-CHECK.md` | 25 条里 15 条我只凭记忆写了编号，必须逐条核 |
| 环境与执行手册 | `RUNBOOK.md` | 从装环境到出第一张表 |

### 验证状态（重要，别跳过）

**我真的验过的：**

- `src/` 下 11 个 Python 文件全部通过 `py_compile`；
- 答案抽取器 **18 条回归测试全过**：分数 `3/4`、`\frac{1}{2}`、千分位 `1,000`、百分号 `72%`、未闭合 `\boxed{42`、裸答案被 strict 拒绝；
- 表格生成器在**合成数据**上跑通三种输出（markdown / LaTeX / per-seed），合成数据放临时目录、跑完即删，`runs/` 保持干净；
- `run_arena.py --dry-run` 正确排出 24 个训练 run 的计划；
- `paper/main.tex` **实际编译成功**：6 页、22 条参考文献、0 个未解析引用；
- 检索时**打开过页面**的文献：ACL 2026 那篇（作者/摘要逐字核对）、arXiv API 返回的 5 篇。

**我没验的（诚实交代）：**

- **任何训练/采样/评测代码的真实运行**——本机没装 torch，只有一张空卡，跑不了；
- `transformers` / `peft` 在 Python 3.13 上的具体版本兼容性（RUNBOOK 里给了做法，没跑过）；
- HuggingFace 模型与数据集的下载是否通（本机 `download.pytorch.org`、`pypi.org` 直连均失败，走了工具层代理）；
- 论文在**真正的 ACL 模板**下的排版——本机 MiKTeX 是坏的（连自己的日志目录都写不进去，`acl.sty`、`natbib`、`booktabs` 全缺），所以走的是我写的**降级分支**。你在好机器上装了 `acl.sty` 后排版会变，需要重新看一眼；
- `refs.bib` 里 15 条只凭记忆写的 arXiv 编号（清单在 `paper/REF-CHECK.md`）。

换句话说：**骨架是真的，数字一个都没有。** 这是有意的。

---

## 1. 你的硬件决定了选题

实测你这台机器：

```
GPU:    NVIDIA GeForce RTX 5060 Ti, 16311 MiB (16 GB), driver 610.88
Python: 3.13.15
torch:  未安装
```

这条约束比什么都重要：

| 你想做的事 | 16GB 单卡能不能做 |
|---|---|
| 1.5B 模型 bf16 + LoRA SFT | ✅ 轻松，~8GB 显存 |
| 1.5B 模型 DPO（LoRA + 冻结参考模型） | ✅ 可以，~10GB |
| 1.5B 模型 GRPO / 在线 RL | ⚠️ 能跑，但一个 run 8–20 小时，基本只够做 1–2 个 |
| 7B 全参数微调 | ❌ |
| 7B QLoRA | ⚠️ 很紧，seq 要压到 1024，容易 OOM |
| 任何「我们刷了 SOTA」的论文 | ❌ 别想 |

**结论：你的论文不能是「提出新方法刷榜」，只能是「受控实证 / 诊断 / 应用」。** 这不是退而求其次——2026 年这条路是通的，ACL 2026 正会就收了纯实证的 [Scaling Behaviors of LLM RL Post-Training](https://aclanthology.org/2026.acl-long.1444/)（Qwen2.5 0.5B–72B 的 scaling 实证）。区别是人家有 72B 的卡，你要把 scope 收到 1.5B。

---

## 2. 三句话结论

1. **别做「SFT vs RL 谁更好」**——2026 年这个坑已经被填满了（见 `docs/01` 的「已被占」清单，至少 4 篇）。
2. **推荐做「等算力竞技场」**：把 SFT / RFT（拒绝采样自训练）/ DPO / 测试时计算（自洽投票）放在**同一份 GPU 时间预算**下横评，回答「0.5B–3B 规模下，这些钱花在哪最值」。一次采样同时喂给 RFT 和 DPO，采样成本摊薄，总预算 ~50 GPU 小时。
3. **这条路的上限是 workshop / CCF-C / Findings，不是 ACL 主会。** 你要「水一个」，这是最诚实也最快的定位。想要更好的，得加算力。

---

## 3. 今晚就能做的三件事

```powershell
cd D:\Repository\JasonYin\posttrain-paper

# 1) 装环境（约 20-40 分钟，取决于网速；国内建议加镜像，见 RUNBOOK）
pip install -r requirements.txt

# 2) 验证 GPU 和 torch 匹配（RTX 5060 Ti 是 Blackwell sm_120，必须 cu128+）
python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# 3) 200 条样本的 smoke test，跑通全链路，约 10 分钟
python src/build_data.py --smoke
python src/train_sft.py --model 1.5B --smoke --out runs/_smoke
```

跑通这三步，你就有了「一条能出数的流水线」。剩下的是把 `--smoke` 去掉，让它跑一晚上。

---

## 4. 目录结构

```
posttrain-paper/
├─ README.md                  ← 你在这
├─ RUNBOOK.md                 ← 从零到第一张表的操作手册
├─ requirements.txt
├─ configs/
│   └─ arena.py               ← 唯一需要改的配置（模型/数据/预算/超参）
├─ src/
│   ├─ common.py              ← 工具：种子、日志、答案抽取、预算计时
│   ├─ modeling.py            ← 模型/tokenizer/LoRA 构建
│   ├─ configs_loader.py      ← 读 configs/arena.py
│   ├─ train_common.py        ← tokenize / collate / optimizer 等训练工具
│   ├─ build_data.py          ← 数据准备
│   ├─ sample.py              ← K 次采样（同时供 RFT / DPO / 自洽投票）
│   ├─ train_sft.py           ← LoRA SFT（也用于 RFT），预算感知
│   ├─ train_dpo.py           ← LoRA DPO，预算感知
│   ├─ eval_math.py           ← 数学评测（三档解析器）
│   ├─ make_tables.py         ← 汇总 JSONL → Markdown/LaTeX 表
│   └─ run_arena.py           ← 按顺序跑完整网格（可 --dry-run）
├─ tests/
│   └─ test_parsers.py        ← 18 条解析器回归测试（无需 torch）
├─ docs/
│   ├─ 01-literature-map.md   ← 2026-10 后训练版图 + 已被占选题
│   ├─ 02-topic-proposals.md  ← 3 个方案对比
│   └─ 03-experiment-protocol.md
└─ paper/
    ├─ main.tex               ← 论文骨架（缺宏包会自动降级，可编译）
    ├─ main.pdf               ← 已编译：6 页
    ├─ refs.bib               ← 25 条参考文献（.bib 里不能写 % 注释）
    └─ REF-CHECK.md           ← 逐条核对清单，15 条待你验证
```

---

## 5. 你还需要做的决定

`docs/02-topic-proposals.md` 里给了三个方案。**默认我已经按 P1（等算力竞技场）把代码搭好了**，因为它是三者里唯一「算力够、风险可控、还有一点新意」的。

如果你导师/学校对 venue 有硬要求（比如必须是 CCF-C 以上、或者必须是 SCI 期刊），告诉我，方案要重新裁。不同的 venue 对「贡献强度」的要求差一个数量级。
