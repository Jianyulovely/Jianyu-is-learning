# RUNBOOK：从零到第一张表

目标机器：Windows + RTX 5060 Ti 16GB + Python 3.13.15。
每一步都写了「怎么判断成功了」，别跳过验收。

---

## 1. 装 PyTorch（唯一有坑的一步）

RTX 5060 Ti 是 Blackwell 架构，计算能力 **sm_120**。这个数字很关键：

- 只有 **CUDA 12.8 及以上** 编译的 torch 才带 sm_120 kernel；
- 装错了不会报错，只会在第一次 `model.to("cuda")` 时抛
  `no kernel image is available for execution on the device`；
- Python 3.13 需要 **torch >= 2.7**（cp313 wheel 从 2.7 才有）。

```powershell
# 先卸掉可能存在的旧 torch
pip uninstall -y torch torchvision torchaudio

# 装 cu128 版本
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

> **国内网络**：`download.pytorch.org` 大概率连不上。两个办法：
> 1. 配代理后再装；
> 2. 用镜像站找 cu128 的 whl 文件手动装，例如
>    `pip install https://mirror.example/whl/torch-2.8.0+cu128-cp313-cp313-win_amd64.whl`
>    （具体路径以镜像站实际为准）。
>
> 本机实测 `curl download.pytorch.org` 失败（走了工具层代理，shell 直连不通），
> 所以这一步你**必须自己确认网络**。这是全流程唯一的硬阻塞点。

**验收：**

```powershell
python -c "import torch;print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))"
```

必须看到 `True`、`NVIDIA GeForce RTX 5060 Ti`、`(12, 0)`。

**再做一次真·矩阵乘法**（`is_available()` 为 True 但仍可能缺 kernel）：

```powershell
python -c "import torch;a=torch.randn(2048,2048,device='cuda');print((a@a).sum().item())"
```

不报错才算真的能算。**这一步过了，后面就没有环境问题了。**

---

## 2. 装其余依赖

```powershell
cd D:\Repository\JasonYin\posttrain-paper
pip install -r requirements.txt
```

国内建议加镜像：

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**验收：**

```powershell
python -c "import transformers,peft,datasets;print(transformers.__version__,peft.__version__)"
```

---

## 3. 下载模型和数据

```powershell
# 国内必须设镜像，否则 huggingface.co 直连会卡住
$env:HF_ENDPOINT = "https://hf-mirror.com"

python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen2.5-1.5B-Instruct')"
```

数据在第一次 `build_data.py` 时自动下载（GSM8K / hendrycks_math / MATH-500）。
如果 MATH 加载失败，脚本会**警告并继续**（只用 GSM8K 也能跑，但论文会弱一些）。

**验收：** `~/.cache/huggingface` 下能看到模型目录，约 3GB。

---

## 4. Smoke test（10 分钟）

```powershell
python src/build_data.py --smoke
python src/train_sft.py --model 1.5B --train-file data/train.jsonl --smoke --out runs/_smoke
```

**验收：**

- `data/` 下出现 4 个 jsonl；
- 打印 `trainable params: ...M`（LoRA 大概 10–20M，占全模型 1% 左右）；
- loss 从 ~2.x 降到 ~1.x；
- `runs/_smoke/adapter_model.safetensors` 存在。

**显存观察**（另开一个窗口）：

```powershell
nvidia-smi --query-gpu=memory.used --format=csv -l 1
```

1.5B + LoRA + seq 1024 应该在 **6–9 GB**。如果超 14GB，把
`configs/arena.py` 里 `train.micro_batch` 降到 1，或 `max_seq_len` 降到 768。

---

## 5. 全量采样（最贵的一步，约 2 小时）

```powershell
python src/sample.py --model 1.5B
```

**验收：** 打印 `pass@8`（模型自己答对的比例）。这个数很重要：

- 若 **< 10%**：你的 RFT 没有正样本可学，DPO 也配不出对。**先调 temperature 到 0.9 重采**，
  或者换更大的模型（3B）。
- 若 **> 70%**：题目太简单，提升空间小，论文没故事。换更难的 MATH 子集。
- **健康的区间是 25%–55%。** 这个数直接决定论文能不能成立，务必先看一眼再往下跑。

产出：`runs/sample/{samples,rft,dpo_pairs}.jsonl`。

---

## 6. 单点验证（先跑一个，别直接跑全网格）

```powershell
python src/train_sft.py --model 1.5B --train-file data/rft.jsonl --budget-gpu-hours 0.5 --seed 42 --out runs/rft_b30m_s42
python src/eval_math.py --model 1.5B --adapter runs/rft_b30m_s42 --method rft --budget 0.5 --seed 42 --test gsm8k_test
python src/make_tables.py
```

**验收：** 表格里出现一行 rft。**哪怕数字很难看，只要它出现了，流水线就是通的。**

这一步的意义是：在花 34 小时之前，用 1 小时证明整条链路能产出可发表格式的结果。

---

## 7. 跑全网格

```powershell
python src/run_arena.py --model 1.5B --dry-run   # 先看它要跑什么
python src/run_arena.py --model 1.5B
```

会连跑 ~24 个训练 + ~50 次评测。**建议夜里跑，并关掉 Windows 睡眠：**

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

0.5B 的第二条曲线，等 1.5B 跑完再跑（同一份代码，`--model 0.5B`）。

---

## 8. 出表出图

```powershell
python src/make_tables.py
python src/make_tables.py --per-seed
python src/make_tables.py --latex
```

把 Markdown 表贴进 `paper/main.tex` 的 `\input` 或直接替换 `\TODO` 处。
**Figure 1（accuracy vs GPU·h）需要你自己用 matplotlib 画**，数据在
`runs/evals/*.json`，横轴用 `budget`，纵轴用 `parsers.standard.accuracy`，误差棒用 seed 间标准差。

---

## 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| `no kernel image is available` | torch 不是 cu128 | 回第 1 步 |
| `CUDA out of memory` | batch/seq 太大 | `micro_batch=1`，`max_seq_len=768` |
| `dpo_pairs.jsonl` 为空 | 采样全对或全错 | 看 pass@8，调 temperature |
| 训练 loss 一直是 2.3 不动 | 学习率太小或数据没 mask 对 | 检查 `tokenize_supervised` 的 labels |
| `KeyError: 'question'` | jsonl 字段不对 | 重跑 `build_data.py` |
| HuggingFace 卡住 | 没设镜像 | `$env:HF_ENDPOINT="https://hf-mirror.com"` |
| 推理输出重复 | temperature 太低 + top_p 太窄 | 采样时 0.7/0.95 |

---

## 一条纪律

**每跑完一个 run，立刻把它的数字记下来。** 不要指望「最后一起汇总」——
中途 OOM、断电、改配置都会让你不知道该信哪份结果。`runs/*/meta.json`
记录了每个 run 的完整配置，这是你写论文附录时唯一能救命的东西。
