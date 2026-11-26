# pandas 数据处理练习（12 个按功能分类的 notebook）

这套 notebook 用一份**故意做脏的电商订单数据** + 一份**非结构化文档语料**，把 pandas 处理数据的完整链路走一遍：

```
造表 → 读表 → 取数 → 清洗 → 文本 → 聚合 → 合并 → 时间
     → 非结构化文本清洗/切分/去重 → SFT 数据集构建 → 性能工程 → 端到端实战
```

每个 notebook 都是**独立可运行**的，且已经保存了执行输出，可以直接当教程读；想动手时逐格运行即可。

---

## 一、怎么开始

### 1. 环境

- conda 环境：`llm_sft`（Python 3.11）
- 关键版本：`pandas 3.0.5`、`numpy 2.4`、`pyarrow 25`、`openpyxl 3.1`、`matplotlib 3.11`、`beautifulsoup4 4.15`、`datasets 5.0`

```bash
conda activate llm_sft
python -c "import pandas; print(pandas.__version__)"   # 3.0.5
```

### 2. 启动

```powershell
cd python/pandas          # 重要：在 python/pandas 目录下启动，data/ 才能被直接找到
jupyter lab
```

或者在 VSCode / PyCharm 里直接打开 `.ipynb`，把右上角内核选成 **llm_sft（python3）**。
如果内核列表里没有，执行一次：

```bash
conda activate llm_sft
python -m ipykernel install --user --name python3 --display-name "llm_sft"
```

### 3. 数据

`data/` 下的样例文件已经生成好了，开箱即用。想重新生成（或改完生成脚本后重跑）：

```bash
python python/pandas/data/make_sample_data.py
```

---

## 二、目录：按功能分类

| # | 文件 | 学什么 | 关键 API |
| --- | --- | --- | --- |
| 01 | [数据结构_Series与DataFrame](01_数据结构_Series与DataFrame.ipynb) | 两个核心对象、索引、dtype、对齐、Copy-on-Write | `Series` / `DataFrame` / `assign` / `astype` / `loc` |
| 02 | [数据读写_CSV_Excel_JSON_Parquet](02_数据读写_CSV_Excel_JSON_Parquet.ipynb) | 读文件的参数、编码、分块、Excel、JSONL、Parquet | `read_csv` / `read_excel` / `json_normalize` / `to_parquet` |
| 03 | [查看选择与过滤](03_查看选择与过滤.ipynb) | 体检、`loc`/`iloc`、布尔与 `query`、条件改值 | `head` / `info` / `describe` / `loc` / `query` / `mask` |
| 04 | [数据清洗_缺失重复异常](04_数据清洗_缺失重复异常.ipynb) | 缺失、重复、类型转换、脏文本、异常值、清洗管线 | `isna` / `dropna` / `fillna` / `duplicated` / `to_numeric` / `cut` |
| 05 | [字符串与文本处理](05_字符串与文本处理.ipynb) | `.str` 访问器、正则、`extract`、文本归一化、词频 | `str.replace` / `str.extract` / `str.split` / `normalize` |
| 06 | [分组聚合与透视](06_分组聚合与透视.ipynb) | split-apply-combine、命名聚合、`transform`、透视、分箱 | `groupby` / `agg` / `transform` / `pivot_table` / `crosstab` |
| 07 | [合并连接与重塑](07_合并连接与重塑.ipynb) | 四种连接、多对多陷阱、宽长转换 | `merge` / `concat` / `melt` / `pivot` / `stack` |
| 08 | [时间序列处理](08_时间序列处理.ipynb) | 时间解析、`.dt`、时间索引、重采样、移动窗口 | `to_datetime` / `resample` / `rolling` / `shift` |
| 09 | [非结构化文本_清洗切分去重](09_非结构化文本_清洗切分去重.ipynb) | HTML 抽正文、文本清洗、chunk 切分、SimHash 去重、质检 | `BeautifulSoup` / 正则 / `simhash` / `apply` |
| 10 | [SFT数据集构建_JSONL与对话格式](10_SFT数据集构建_JSONL与对话格式.ipynb) | JSONL 容错、对话展开、schema 校验、PII、去重、划分、导出 | `explode` / `json_normalize` / `pivot_table` / `to_json` |
| 11 | [性能优化与工程化](11_性能优化与工程化.ipynb) | dtype 优化、向量化、`pipe` 管线、性能坑 | `memory_usage` / `np.select` / `pipe` |
| 12 | [实战_从原始文档到SFT数据集](12_实战_从原始文档到SFT数据集.ipynb) | 端到端管线：盘点→抽取→清洗→切分→去重→质检→划分→导出 | 前 11 节的组合 |

### 每节的固定结构

```
目标 → 概念/心智模型 → 最小例子（带输出）→ 参数与变体 → 小练习（附参考答案）→ 小结与常见坑
```

---

## 三、学习路线（建议）

| 阶段 | 内容 | 建议时间 | 目标 |
| --- | --- | --- | --- |
| 基础 | 01 → 05 | 2~3 天 | 能独立把一份脏数据读进来、洗干净、做简单筛选 |
| 分析 | 06 → 08 | 1~2 天 | 能做分组报表、透视表、时间序列汇总 |
| 数据工程 | 09 → 12 | 3~5 天 | 能把一堆文档变成可训练的 SFT 数据集 |

具体用法建议：

1. **第一遍**：只读 markdown + 看输出，理解每个 API 在干什么；
2. **第二遍**：清空输出（Kernel → Restart & Clear Output），自己重写每个 cell，再对照；
3. **第三遍**：把 `data/` 里的数据换成你自己的数据，重跑整条链路——这一步才算真的学会。

> 小练习都写了参考答案。**先自己做，再看答案**，否则只是"读代码"而不是"写代码"。

---

## 四、数据说明

| 文件 | 内容 | 用在哪 |
| --- | --- | --- |
| `data/sales_orders.csv` | 60 行订单（日期、城市、品类、渠道、金额、销售代表，含少量缺失） | 02、03、06、11 |
| `data/sales_orders_messy.csv` | 12 行**故意做脏**的订单：空格、多种日期格式、`¥1,299.00`、重复行、非法日期、负数 | 02、04 |
| `data/customers.csv` / `customer_orders.csv` | 客户维表 + 订单表（含匹配不上的客户 C09） | 07 |
| `data/prices_wide.csv` | 宽表（每年一列） | 02、07 |
| `data/customers_gbk.csv` | GBK 编码的中文 CSV | 02 |
| `data/customers.json` | 嵌套 JSON（`contact.email`、`tags` 列表） | 02 |
| `data/events.jsonl` | 40 条事件日志（一行一条 JSON，含嵌套 `props`） | 02 |
| `data/site_visits.csv` | 6 天网站访问日志（时间戳、用户、页面、设备、时长） | 08 |
| `data/docs/*` | 4 篇非结构化文档：Markdown、纯文本（带零宽字符/页码）、HTML（带导航/脚本/广告）、转载重复版 | 09、12 |
| `data/raw_sft/*` | SFT 原料：对话日志 JSONL（含 1 行坏 JSON、空消息、PII）、Alpaca JSONL（含重复/空指令/空回答）、嵌套 FAQ JSON | 10、12 |
| `data/make_sample_data.py` | 生成以上全部数据，**改这里就能改数据** | — |

**想练手？** 把 `make_sample_data.py` 里的 `n = 60` 改成 6000，把 `docs/` 换成你自己的 PDF 转出来的文本，再重跑对应章节。

---

## 五、pandas 3.0 与常见版本的差异（踩坑必读）

本套代码在 pandas 3.0 上验证过，和网上大量 pandas 1.x/2.x 教程有几处**行为不同**：

| 变化 | 3.0 的行为 | 本教程的写法 |
| --- | --- | --- |
| Copy-on-Write 默认开启 | `df[条件]["列"] = 值` **不生效**（会警告 `ChainedAssignmentError`） | 一律用 `df.loc[条件, "列"] = 值` |
| 文本 dtype | 默认是 `str`（Arrow 支撑），不再是 `object` | `df.dtypes` 里会看到 `str`，属于正常 |
| 正则引擎 | 不支持 `\u4e00` 这种转义 | 写字符本身：`"[\u4e00-\u9fff]"`（不写 `r` 前缀） |
| `applymap` | 已移除 | 用 `df.map(func)` |
| `resample` 频率 | `"M"`/`"Q"` 已废弃 | 用 `"ME"`/`"QE"` |
| `fillna(method=...)` | 已移除 | 用 `ffill()` / `bfill()` |
| `contains` 遇到缺失 | `str` dtype 下默认当 `False`；`object` 列则返回 `NaN` | 统一写 `na=False`，行为一致 |

---

## 六、常见问题

**Q：运行时报 `FileNotFoundError: data/...`？**
A：Jupyter 的工作目录不是 `python/pandas`。在 `python/pandas` 下启动 Jupyter，或用 notebook 第一个 cell 里的兜底逻辑（它会在 `python/pandas/data` 找）。

**Q：中文显示成方块 / 报 `MissingGlyph`？**
A：绘图需要中文字体，第 08 节已设置 `Microsoft YaHei`；Linux 上改成 `Noto Sans CJK SC`。

**Q：CSV 用 Excel 打开是乱码？**
A：写文件时加 `encoding="utf-8-sig"`（第 02、07 节有例子）。

**Q：不想装 `datasets` / `openpyxl` 怎么办？**
A：对应 cell 是可选依赖，删掉或跳过即可；其余内容不受影响。

**Q：notebook 输出太多，卡？**
A：`Kernel → Restart & Clear Output`，或者只运行需要的 cell。

---

## 七、产物

运行 notebook 会在 `output/` 下生成中间件（CSV / Parquet / JSONL / xlsx / 报告），用于演示"写出后再读回"。
这些文件**可以随时删除**，重跑对应 notebook 会重新生成；已在 `.gitignore` 里忽略。

---

## 八、学完之后

建议按顺序做三件事：

1. 把 09/10/12 里的函数抽成一个 `data_pipeline.py`，做成命令行工具（输入目录 → 输出 JSONL）；
2. 接上真实 tokenizer（`transformers.AutoTokenizer`），把"估算 token"换成精确计数，重新定 `max_length`；
3. 用你自己的领域文档跑一遍全链路，抽样 50 条人工检查——**这一步会发现最多问题**。

配套速查表见 [速查表.md](速查表.md)。
