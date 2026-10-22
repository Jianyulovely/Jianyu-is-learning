# 交接文档：大模型后训练算力分配研究

> **给换工作目录之后的你，或任何接手这个项目的人 / 新的 AI 会话。**
>
> 读完这一页再动任何文件。本文档**不含绝对路径**，整个文件夹可以直接搬走。
>
> 最后更新：2026-10-22

---

## 0. 三十秒版本

**做什么**：在 0.5B / 1.5B / 3B 三个规模上，用**固定的 GPU 时间预算**横评四类后训练方法
（SFT、RFT 拒绝采样自训练、DPO、自洽投票），回答一个具体的工程问题：

> 一个只有单卡的实践者，接下来的**一个小时**该花在**训练模型**上，还是花在**推理采样**上？

**预算轴的单位是分钟（5 / 15 / 30 / 60），不是小时。** 3000 条数据一个 epoch 只要约 94 秒，
1 小时等于 38 个 epoch，整条 1–8 小时的轴全落在过拟合区，五条曲线会挤成一条。
原因写在 `configs/arena.py` 的注释里，改之前先读那段。

**现在到哪了**：代码骨架写完了，能测的部分都测过了。**但一次真实训练都没跑过**——开发机上没装 torch。

**下一步是什么**：装环境 → 跑通 smoke → 拿到第一组真数字 → 全量实验 → 出 GitHub repo + arXiv。

**目标是什么**（注意，已经变了）：**不是发论文**，是拿这个作品去投**大模型算法实习**。

---

## 1. 目标（已变更，以此为准）

### 原来的目标（已放弃）

发一篇会议/期刊论文。

**放弃原因**：投稿周期 3–6 个月（期刊 6–18 个月），期间多数会议有匿名期、论文不能公开；
而实习市场对「CCF-C 论文」几乎没有区分度。用 3 个月换一个实习简历上的小增量，不划算。

### 现在的目标

三周内产出三样东西，用来投**大模型算法实习**：

| 产物 | 优先级 | 说明 |
|---|---|---|
| **GitHub repo，能一键复现** | ★★★★★ | 面试官能当场点开验证；造假成本极高 |
| **arXiv 预印本** | ★★★★ | 证明你能从问题 → 实验 → 写作走完全程 |
| **技术解读一篇**（知乎/公众号） | ★★★ | 国内算法岗很吃这个，能带来内推 |

**投稿不是必须的。** 如果三周后正好有个 workshop / 会议 deadline 合适，顺手投可以；
但**不为它改计划、不为它等审稿**。

### 成功标准（不是「录用」，是这三条）

1. 陌生人 clone 下来，能复现出主表的数字；
2. 面试官追问三个「为什么」，你答得上；
3. repo 里**每一个数字都有出处**，没有一个是占位符。

---

## 2. 铁律（违反任何一条，整个作品就废了）

1. **不编数据。** 所有数字必须来自 `runs/evals/*.json`。
2. **不用测试集调参。** dev split 已经在 `build_data.py` 里切好了，用它。
3. **不挑 seed、不挑 checkpoint。** 所有 run 都要进附录，包括跑崩的。
4. **不为了「有论文」而做自己讲不清的工作。** 面试是深挖式的，讲不清的论文是负资产。
5. **每个数字要能追溯。** 论文/README 里的表，必须能用 `make_tables.py` 重新生成。

第 4 条最容易被自己骗。写不动的时候，宁可缩小 scope，不要模糊结果。

---

## 3. 硬件：两台机器，能力完全不同

### 机器 A — 训练用

```
RTX 5060 Ti 16GB · Windows · Python 3.13.15 · driver 610.88 · torch 未安装
架构 Blackwell sm_120 → 支持 bf16 + tensor core
```

### 机器 B — 采样/评测用

```
4 × TITAN Xp 12GB · Linux · yyin@server-3 · driver 580.159.04
架构 Pascal sm_61 → 无 tensor core、无 bf16、fp16 仅 fp32 的约 1/64 速率
```

**为什么这么分工**：

- 训练要算力密度 → 必须是 A（bf16 + tensor core）
- 采样/评测是**带宽受限**的 → B 的 547 GB/s × 4 ≈ 2.2 TB/s，远高于 A 的 448 GB/s
- 3B 模型放 A（bf16 权重约 6GB，能装下）

| 任务 | 放哪台 |
|---|---|
| SFT / RFT / DPO 训练 | 机器 A |
| K=8 采样、批量评测 | 机器 B（数据并行） |
| 3B 模型 | 机器 A（先用 micro_batch=1 试） |

---

## 4. 环境：唯一的硬阻塞

### 机器 A（Blackwell sm_120）

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

### 机器 B（Pascal sm_61）—— 这里有个大坑

**必须用 cu124 的 wheel，绝对不能装最新版。**

- CUDA 13.0 移除了 CC 7.5 以下（Maxwell 5.x / Pascal 6.x / Volta 7.0–7.2）的**离线编译**支持
- PyTorch 的 **cu128+ wheel 已不含 sm_5x/sm_6x kernel**
- driver 580 是**最后一个**支持 Pascal 的分支（LTS，支持到 2028 年中）—— 你正好在上面，别升级

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

**装错的症状**（非常迷惑，务必记住）：

```python
torch.cuda.is_available()   # True  ← 骗你的
torch.randn(8, 8, device="cuda") @ torch.randn(8, 8, device="cuda")
# RuntimeError: CUDA error: no kernel image is available for execution on the device
```

### 每台新机器第一件事

```bash
python src/check_env.py
```

必须看到 **`fp32 matmul : OK`**。看到 `FAIL` 就是 wheel 不对，卸了重装。

### 其他环境注意

- 国内网络：`$env:HF_ENDPOINT = "https://hf-mirror.com"`（PowerShell）/ `export HF_ENDPOINT=...`（bash）
- 开发机上 `pypi.org` 和 `download.pytorch.org` 直连都失败过，网络可能是最大变量
- Windows 控制台默认 GBK，所有脚本已调 `setup_stdout()` 强制 UTF-8
- **不要装 bitsandbytes**：1.5B 在 bf16 下 16GB 完全够，4-bit 量化只会引入 Pascal 上的新问题

---

## 5. 文件地图

```
posttrain-paper/
├─ HANDOVER.md            ← 你在这
├─ README.md              ← ⚠️ 按"投稿"写的，方向已变，仅供参考
├─ RUNBOOK.md             ← 操作手册，Windows 视角，仍然有效
├─ requirements.txt
├─ configs/
│   └─ arena.py           ← 唯一需要改的配置（模型/预算/超参/K/温度）
├─ src/
│   ├─ check_env.py       ← 环境体检，每台新机器先跑这个
│   ├─ common.py          ← 种子/日志/答案抽取/预算计时/UTF-8
│   ├─ modeling.py        ← 模型构建 + LoRA + dtype 自动选择
│   ├─ configs_loader.py  ← 读 configs/arena.py
│   ├─ train_common.py    ← tokenize / collate / optimizer / scheduler
│   ├─ build_data.py      ← 下数据、统一 target 格式、切 dev
│   ├─ sample.py          ← K 次采样 → 同时产出 RFT 数据 + DPO 对 + 自洽投票基线
│   ├─ train_sft.py       ← 预算感知的 LoRA SFT（RFT 也用它）
│   ├─ train_dpo.py       ← 预算感知的 LoRA DPO
│   ├─ eval_math.py       ← 三档解析器评测
│   ├─ make_tables.py     ← 汇总 JSONL → Markdown / LaTeX 表
│   └─ run_arena.py       ← 按顺序跑整个网格（--dry-run 先看计划）
├─ tests/
│   └─ test_parsers.py    ← 18 条解析器回归测试，不需要 torch
├─ docs/
│   ├─ 01-literature-map.md      ← 2026-10 文献版图 + 已被占的选题（写 related work 时用）
│   ├─ 02-topic-proposals.md     ← 三个候选方案，选了 P1，论证在这里
│   └─ 03-experiment-protocol.md ← 实验协议：控制变量、预算核算、统计规范
└─ paper/
    ├─ main.tex / main.pdf ← 论文骨架（6 页，可编译，全是占位符）
    ├─ refs.bib            ← 25 条参考文献，15 条待核
    └─ REF-CHECK.md        ← 逐条核对清单
```

**新会话快速恢复上下文**：读 `HANDOVER.md` → `docs/02-topic-proposals.md`。
`docs/01` 是文献调研，不用通读。

---

## 6. 完成度（诚实版）

### ✅ 已验证

- 13 个 Python 文件全部通过语法解析（12 个 src + 1 个测试）
- 答案抽取器 **18 条回归测试全过**：分数 `3/4`、`\frac{1}{2}`、千分位 `1,000`、百分号 `72%`、未闭合 `\boxed{42`、裸答案被 strict 拒绝
- 表格生成器在**合成数据**上跑通三种输出（markdown / LaTeX / per-seed），合成数据放临时目录、跑完即删
- `run_arena.py --dry-run` 从**任意工作目录**都能正确解析出全部路径
- `paper/main.tex` 实际编译成功：6 页、22 条参考文献、0 个未解析引用
- `check_env.py` 语法正确（但**从未真正执行过**，因为没有 torch）

### ❌ 未验证（不要假装它们能用）

- **任何真实的训练 / 采样 / 评测运行** —— 一次都没有
- `transformers` / `peft` 在 Python 3.13 上的具体版本兼容性
- HuggingFace 模型与数据集的下载
- **3B 模型的显存占用** —— 只是估算能装下，没实测
- Pascal 机器上的 torch cu124 wheel 是否能跑出 kernel
- 论文在**真正的 ACL 模板**下的排版（开发机 MiKTeX 损坏，走的是降级分支）

---

## 7. 按顺序执行

### Phase 0 — 环境（今天，1 小时）

```powershell
python src/check_env.py
# 必须看到 fp32 matmul : OK

pip install -r requirements.txt
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

**验收**：`torch.cuda.is_available()` 为 True **且** `a @ a` 不报错。只看前者会被骗。

### Phase 1 — Smoke（半天）

```powershell
python src/build_data.py --smoke
python src/train_sft.py --model 1.5B --smoke --out runs/_smoke
```

**验收**：
- `data/` 下出现 4 个 jsonl
- 打印 `trainable params: ...M`（约 10–20M，占全模型 1% 左右）
- loss 从 ~2.x 降到 ~1.x
- `runs/_smoke/adapter_model.safetensors` 存在
- 显存 6–9 GB（`nvidia-smi --query-gpu=memory.used --format=csv -l 1`）

### Phase 2 — 采样（2 小时）★ 关键决策点

```powershell
python src/sample.py --model 1.5B
```

**看一个数字：`pass@8`。**

| pass@8 | 意味着 | 怎么办 |
|---|---|---|
| < 10% | 没有正样本可学，RFT/DPO 拿不到数据 | 调 temperature 到 0.9 重采，或换 3B |
| **25%–55%** | **健康区间** | 继续 |
| > 70% | 题太简单，没有提升空间 | 换更难的 MATH 子集 |

**这个数直接决定整个项目能不能成立。** 看一眼再往下走，别闷头跑。

### Phase 3 — 单点验证（1 小时）

```powershell
python src/train_sft.py --model 1.5B --train-file data/rft.jsonl --budget-gpu-hours 0.5 --seed 42 --out runs/rft_b30m_s42
python src/eval_math.py --model 1.5B --adapter runs/rft_b30m_s42 --method rft --budget 0.5 --seed 42 --test gsm8k_test
python src/make_tables.py
```

**验收**：表里出现一行 `rft`。**哪怕数字很难看，只要它出现了，流水线就是通的。**

### Phase 4 — 全量（1–2 天，可挂机）

```powershell
python src/run_arena.py --model 1.5B --dry-run   # 先看计划
python src/run_arena.py --model 1.5B
```

顺序建议：1.5B 先跑（最重要），然后 0.5B（便宜，撑起规模轴），最后 3B（最贵）。

### Phase 5 — 出表 + 画图

```powershell
python src/make_tables.py
python src/make_tables.py --per-seed
python src/make_tables.py --latex
```

**⚠️ 画图脚本还不存在**，要自己写（见第 9 节 TODO）。

### Phase 6 — 发布

1. 建 GitHub repo，加 `.gitignore`（已提供），**只提交代码 + 日志 + 表，不提交权重**
2. 写 README：一句话结论 + 主图 + 一键复现命令
3. 写 arXiv（用 `paper/main.tex` 改，删掉 TODO 占位符）
4. 写技术解读

---

## 8. 关键设计决策（改之前先读为什么）

### ① 按预算截断，不跑收敛

`train_sft.py --budget-gpu-hours H` 会先跑 12 步校准，测出每步耗时，再换算成固定步数。

**如果改成「跑到收敛」，整个实验就失去意义**——因为那是在比各方法需要的算力，而不是比同样算力下的产出。

### ② 一次采样喂三个方法

在这之前想清楚这个链条：

```
种子模型 ──采样 K=8──┬─→ 保留答对的 → RFT（再 SFT）
                     ├─→ 答对/答错配对 → DPO
                     └─→ 对 K 个答案投票 → 自洽投票（不训练）
```

`sample.py` 一次生成 `samples.jsonl`，`_derive()` 同时产出 `rft.jsonl`、`dpo_pairs.jsonl` 和自洽投票基线。
**如果拆成三次采样，预算直接翻三倍，实验在单卡上做不完。**

### ③ 三档解析器

`lenient`（抓最后一个数字）/ `standard`（`\boxed{}` 优先）/ `strict`（只认 `\boxed{}` 且要求有推理）。

**只报一档会被质疑「你是不是挑了解析器」。** 三档都报，差值本身就是论文里的 Table 3。

### ④ DPO 的参考模型 = 关掉 adapter 的同一个模型

`model.disable_adapter()`，不额外加载一份权重。省一半显存，这是 16GB 能跑 DPO 的原因。

### ⑤ 不用 TRL / vLLM / bitsandbytes

自己写的训练循环，约 100 行。理由是**减少版本漂移**：TRL 的 API 在 2025–2026 改过多次，
而且 Pascal 上 bnb 的 4-bit 算子还有额外问题。依赖越少，三周内跑完的概率越高。

### ⑥ dtype 自动选择

`configs/arena.py` 里 `"dtype": "auto"`：有 bf16 用 bf16，没有落 **fp32**。

**注意不是 fp16**——Pascal 的 fp16 只有 fp32 的 1/64 速率，用 fp16 反而更慢。
这是反直觉的，但实测如此。

---

## 9. 已知问题与 TODO（按优先级）

| # | 问题 | 影响 | 优先级 |
|---|---|---|---|
| 1 | **没有多卡分片**：`sample.py` / `eval_math.py` 没有 `--shard/--num-shards` | 4 张 Titan Xp 用不起来，采样和评测还在单卡上 | **高** |
| 2 | **没有画图脚本**：`make_tables.py` 只出表，不出 Figure 1 | README 和 arXiv 缺主图 | **高** |
| 3 | `README.md` / `docs/` 仍是「投稿」框架 | 容易误导接手的人 | 中 |
| 4 | `refs.bib` 有 15 条凭记忆写的编号 | 不投稿了，优先级降低；但 arXiv 上仍会显示 | 低 |
| 5 | 测试只覆盖解析器，训练循环没有测试 | 训练 bug 只能靠 smoke test 发现 | 中 |
| 6 | `paper/main.tex` 全是 `\TODO` 和 `\XX` 占位符 | 正常，等真数据 | — |

**第 1 项**的具体做法：给两个脚本加 `--shard i --num-shards n` 参数，按 `i::n` 切数据；
启动时用 `CUDA_VISIBLE_DEVICES=i` 让每个进程只看到一张卡。

**第 2 项**的具体做法：新建 `src/make_figure.py`，读 `runs/evals/*.json`，
x 轴 = budget，y 轴 = `parsers.standard.accuracy`，误差带 = seed 间范围，输出 PDF 到 `paper/figs/`。

---

## 10. 换工作目录后的清单

- [x] **所有路径已改为相对项目根**（`run_arena.py` 刚修过，从任意 cwd 都能跑）
- [ ] 整个文件夹直接搬，不需要改任何代码
- [ ] 新机器第一件事：`python src/check_env.py`
- [ ] `runs/` 和 `data/` 是空的，换目录后必须从 `build_data.py` 重来
- [ ] 如果搬到 Linux：代码没问题（用 `pathlib`），但 `RUNBOOK.md` 里的 PowerShell 命令要换成 bash
- [ ] 别忘了 `$env:HF_ENDPOINT` / `export HF_ENDPOINT`
- [ ] `.gitignore` 已提供，别把权重和数据集提交进去

---

## 11. 需要外部输入的地方

| 事项 | 卡在哪 | 谁来定 |
|---|---|---|
| 机器 B 能否跑 torch | 需要有人在 server-3 上跑 `check_env.py` | 你（或给 SSH 访问让 AI 去验） |
| 3B 是否真的装得下 | 需要实测显存 | 你，跑一次 smoke |
| pass@8 落在哪个区间 | 需要跑完采样 | 实验决定，不是人决定 |
| 要不要顺手投个会议 | 看当时有没有合适的 deadline | 你，但**别为它改计划** |

---

## 附：一句话记住这个项目

> **不要问「哪个方法更好」，要问「同样的钱，花在哪最值」。**
>
> 前者已经有一百篇论文了，后者还没有人认真算过账。
