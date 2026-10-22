# 参考文献核对清单

BibTeX **不支持 `%` 注释**——`.bib` 里任何 `%` 都会被当成正文，轻则告警，
重则整条丢掉。所以状态标记放在这个文件里，不放进 `refs.bib`。

投稿前逐条处理下表。**标 `?` 的作者字段是占位符 `{Anonymous}`，会原样出现在参考文献里**，必须补全。

| key | arXiv / 出处 | 本次是否打开过页面 | 还需做什么 |
|---|---|---|---|
| `tan2026scaling` | ACL 2026, 2026.acl-long.1444 | ✅ 打开了 ACL Anthology 页面，作者与摘要均已核对 | 无 |
| `posttraining2025survey` | arXiv:2503.06072 | ✅ 搜索命中 | 补全作者列表 |
| `deepdive2025reasoning` | arXiv:2502.21321 | ✅ 搜索命中 | 补全作者列表 |
| `unintended2026values` | arXiv:2610.29922 | ✅ arXiv API 返回完整元数据 | 无（未引用，可删） |
| `midtraining2026` | arXiv:2610.22019 | ✅ arXiv API 返回完整元数据 | 补全其余作者 |
| `autosft2026` | arXiv:2610.22194 | ✅ arXiv API 返回完整元数据 | 补全其余作者（未引用） |
| `safetyrepro2026` | arXiv:2605.25492 | ✅ 搜索命中 | 补全作者列表 |
| `quagmires2025` | arXiv:2510.01624 | ✅ 搜索命中 | 补全作者列表 |
| `interleaving2025` | arXiv:2510.04454 | ✅ 搜索命中 | 补全作者列表 |
| `rafailov2023dpo` | NeurIPS 2023 | ❌ 凭记忆 | 核对会议与年份 |
| `ouyang2022instructgpt` | NeurIPS 2022 | ❌ 凭记忆 | 核对其余作者 |
| `schulman2017ppo` | arXiv:1707.06347 | ❌ 凭记忆 | 核对编号 |
| `hu2021lora` | ICLR 2022 | ❌ 凭记忆 | 核对年份（arXiv 2021，ICLR 2022） |
| `wang2022selfconsistency` | ICLR 2023 | ❌ 凭记忆 | 同上 |
| `zelikman2022star` | NeurIPS 2022 | ❌ 凭记忆 | 核对编号 |
| `dong2023raft` | TMLR 2023 | ❌ 凭记忆 | **优先核对**：我记的是 arXiv:2304.06767，不确定 |
| `deepseek2025r1` | arXiv:2501.12948 | ❌ 凭记忆 | 核对编号 |
| `lambert2024tulu3` | arXiv:2411.15124 | ❌ 凭记忆 | 核对编号 |
| `qwen2024qwen25` | arXiv:2412.15115 | ❌ 凭记忆 | 核对编号 |
| `cobbe2021gsm8k` | arXiv:2110.14168 | ❌ 凭记忆 | 核对编号；booktitle 应为 arXiv，改成 `@article` |
| `hendrycks2021math` | arXiv:2103.03874 | ❌ 凭记忆 | 核对编号 |
| `snell2024scaling` | ICLR 2025 | ❌ 凭记忆 | 核对编号 2408.03314 |
| `ifeval2023` | arXiv:2311.07911 | ❌ 凭记忆 | 未引用；若不用可删 |
| `sftmemorizes2025` | arXiv:2501.17161 | ❌ 凭记忆 | 核对编号 |
| `rlreasoning2025` | arXiv:2504.13837 | ❌ 凭记忆 | 核对编号 |

## 怎么核对（两分钟）

```powershell
# 逐条打开，看标题和作者对不对得上
start https://arxiv.org/abs/2501.12948
```

或者一次性把编号贴给任何能上网的地方查。**不要跳过这一步**：related work 里
一条对不上的引用，是审稿人成本最低的扣分点。

## 一个结构性提醒

`@inproceedings{cobbe2021gsm8k}` 的 `booktitle` 写的是 arXiv 编号——GSM8K 是
arXiv 预印本，应该用 `@article`。同理 `snell2024scaling` 我按 ICLR 2025 写，
但它也可能只是 arXiv。**这类字段错误不会让编译失败**，只会让参考文献格式难看，
而格式难看在评审眼里等于「作者没认真」。
