# companion-ai 功能逻辑漏洞审计

本报告聚焦三类问题：**任务规划**、**工具调用**、**业务对话逻辑**，并附带其他横向问题。
每条结论标注：严重程度（高/中/低）、定位（文件:行号）、问题描述、触发场景、修复建议。

---

## 1. 任务规划（Task Planning）

### P-01【高】"不可以" 会被误判为同意，导致危险命令执行
- 位置：`core/agent_service.py:764-772`（`_is_approval_reply`）、`52-77`（`APPROVAL_WORDS / APPROVAL_CODEPOINTS`）
- 问题：判定逻辑是 `any(word in normalized for word in APPROVAL_WORDS)`，使用「子串包含」匹配。
  - 用户回复 `不可以` → 包含 `可以` → 返回 `True`。
  - 用户回复 `不好`、`不同意`、`绝不允许` 同理。
  - 单字母 `y` 也在白名单里，`yesterday I think...` 会通过。
- 触发场景：当 `computer_shell` 进入 `waiting_human`，用户拒绝写入/删除命令时，会被当作同意，进而执行命令。
- 修复建议：
  1. 改为「整词/精确匹配」，对中文用 `normalized in APPROVAL_WORDS`，对英文按词边界匹配。
  2. 先扫描 `否定词`（不、别、不要、no、never、cancel）做一票否决。
  3. 同时维护 `REJECT_WORDS` 集合，两者都命中时让 LLM 复述确认而不是直接通过。

### P-02【高】并行多 tool_calls 时的早退导致协议错乱
- 位置：`core/agent_service.py:627-734`（`_execute_tool_calls`）
- 问题：循环 `for tool_call in result.tool_calls:` 内部，遇到 `ask_human`、`terminate`、`computer_shell` 的确认场景，会 `return` 提前退出。
  - 已经追加到 `task.messages` 的 `assistant.tool_calls` 包含 N 条 tool_call，但只产生了 1 条 `tool` 结果。
  - 任务被持久化（`save_task`）后，下次恢复时把这份消息序列再发给 LLM/OpenAI 兼容接口，会因为 `tool_call_id` 未一一对应而 400。
- 触发场景：LLM 在一次响应里同时发出 `tavily_search` + `ask_human`，或两条 `computer_shell` 写命令。
- 修复建议：
  1. 在循环开始前判断：若包含 `ask_human / terminate / computer_shell-confirm` 则将整批转为顺序执行并允许暂停；其余 tool_call 在暂停前必须先伪造空响应（`content=""`）补齐占位。
  2. 或者强制要求一次只有一个工具调用：检测到多个时只保留第一个并把其余打回（追加 system 提示 "请逐个调用工具"）。

### P-03【中】`PlanningFlow.decide` 启发式过于敏感，普通寒暄被升级为「多步计划」
- 位置：`core/planning/flow.py:198-225`（`_looks_complex`）、`42-86`
- 问题：长度 ≥ 40 或包含 `分析 / 总结 / 整理 / 比较` 等关键词时直接判定需要计划。
  - "帮我分析下今天发生了啥呀" → 命中 `分析` → 进入 plan 流程，多花若干轮 LLM。
  - LLM 第一轮 JSON 解析失败时还会用 `_default_steps` 给一份「澄清-执行-验证」的模板。模板与真实意图不相关，浪费上下文。
- 触发场景：聊天型用户高频。
- 修复建议：
  1. 关键词清单缩窄到「真正需要分步的动词」（写一个、安装、整理文件、批量、跑脚本）。
  2. JSON 解析失败时不要回落到通用模板；应直接走单轮 agent loop。
  3. `_looks_complex` 在 chat-only role 下应可关闭（role 配置加 `allow_planning: bool`）。

### P-04【中】计划恢复时不区分「补充上下文」和「换话题」
- 位置：`core/agent_service.py:183-198`（continue/补充分支）
- 问题：用户在计划进行中说一句完全无关的话（比如开始聊天气），代码把这句话当作「补充信息」拼到 task.messages，继续推动当前 step。
- 触发场景：用户对长任务失去耐心后随便聊几句。
- 修复建议：
  1. 用轻量分类器（关键词 + LLM judge）判断「补充 / 切换主题 / 求助」，切换时主动提示用户「计划进度已记录，要先聊别的吗？」并让对方选择。
  2. 提供显式 `/pause` 命令，把当前 task 状态转为 `paused`，下次显式 `/resume`。

### P-05【中】"running" 状态的非 planning 任务被静默删除
- 位置：`core/agent_service.py:284-285`
- 问题：`if existing_task and existing_task.status in {"running", "failed", "done"}: await delete_task(...)`。
  - 这意味着上一轮因为进程崩溃或网络断开留下的 running 任务，下一次用户发言时被直接删除，task.messages 里残存的工具结果、半成品规划全部丢失。
- 触发场景：服务异常退出 / Redis 写失败 / Telegram 端断流。
- 修复建议：
  1. 区分 `running`（活动）和 `stale_running`（>5min 未更新）。后者才能直接清理。
  2. 清理之前留一条系统消息「我之前的工作中断了，我重新开始」让用户感知。

### P-06【中】控制指令匹配过于死板，标点会让命令失效
- 位置：`core/agent_service.py:374-411`（`_normalized_control_text` / `_is_plan_*_request`）
- 问题：`_normalized_control_text` 只 `lower + 去空白`，不去标点。
  - "取消计划！" / "继续。" / "下一步～" 都无法命中。
- 修复建议：在 normalize 时去掉中英文标点（`re.sub(r"[\W_]+", "", text)` 或 `string.punctuation + 中文标点`），并扩充同义词（停止、终止、放弃、abort、forget it）。

### P-07【中】拒绝命令时 LLM 完全感知不到结果
- 位置：`core/agent_service.py:172-177` / `233-238`
- 问题：用户拒绝 `computer_shell` 后，代码直接 `delete_task` 并 `return "已取消这次电脑命令。"`。
  - "User did not approve..." 的 tool message 虽然 append 进了 messages，但 task 紧接着被删除，LLM 再也不会被回灌这次结果。
  - 下一轮用户继续讨论同一个问题，LLM 没有记忆「上一次已经被拒绝」，可能又提议同一条命令。
- 修复建议：
  1. 拒绝后不要立即 delete_task，把它转为 `done` 并写入 session history（"我刚才想跑 X，被你拒绝了"）。
  2. 把拒绝信息以 assistant 消息形式落到 history，让下一轮上下文可见。

### P-08【中】Plan ID 时间戳无时区
- 位置：`core/agent_service.py:321` `int(datetime.now().timestamp())`
- 问题：`datetime.now()` 用本地时间，但项目其它地方用 `ZoneInfo("Asia/Shanghai")`。在容器/不同时区机器上 ID 形式不一致，且不带 tz 易混淆。
- 修复建议：直接用 `int(time.time())` 或 `datetime.now(ZoneInfo(timezone_name)).timestamp()`。

### P-09【低】fallback 计划 steps 总把图片步骤插在中间
- 位置：`core/planning/flow.py:190-196`
- 问题：`_default_steps` 的兜底文案是英文 + 通用模板，"Analyze the provided image(s)" 强插到第 1 位之后，但当时连话题都没确定，步骤毫无信息量。
- 修复建议：fallback 直接降级到 chat 模式（即 `needs_plan=False`），不要硬塞一份无意义计划。

### P-10【低】`current_step_index` 在 waiting_human 路径下不清零
- 位置：`core/agent_service.py:502-510`
- 问题：进入 `waiting_human` 后，`mark_step_blocked` 后 `current_step_index` 仍指向被阻塞的 step；后续 resume 时如果用户消息走 cancel/status 路径，渲染计划文本里仍会带 "->" 指针，误导用户。
- 修复建议：阻塞时一并 `task.current_step_index = None` 或在 `render_plan` 中只对 `in_progress` 显示指针。

---

## 2. 工具调用（Tool Calling）

### T-01【高】`computer_shell` 的 `cwd` 没做项目根目录校验
- 位置：`core/tool/computer/shell.py:134-141`（`_resolve_cwd`）
- 问题：
  - `os.path.expandvars` 允许 `%USERPROFILE%`、`%TEMP%`。
  - 绝对路径直接保留（`if not path.is_absolute(): ...` else 不做任何兜底）。
  - 仅读命令也能在任意盘符 `Get-Content C:\Users\...\.ssh\id_rsa`。
- 触发场景：LLM 配合 prompt injection 让模型读用户文件并回显。
- 修复建议：
  1. 解析后做 `is_relative_to(PROJECT_ROOT)` 检查，越界直接 `ToolResult(error=...)`。
  2. 不要 `expandvars / expanduser`，或者只允许白名单变量。

### T-02【高】`classify_command` 的安全清单可绕过
- 位置：`core/tool/computer/safety.py:25-185`
- 问题（PowerShell 语义实际比清单复杂得多）：
  1. `Invoke-Expression`、`iex`、`&` 调用操作符不在 DENY/CONFIRM。`& $cmd`、`iex $payload` 都能跳过分类。
  2. `cmd /c "del x"` 中 `cmd` 不在清单，整条会被识别为「未在只读白名单」→ 走 CONFIRM 路径，但只要用户一次同意就可以反复执行任意 cmd。
  3. `$(...)`、反引号续行未处理，`"$(Remove-Item x)"` 会被拆得稀碎。
  4. 命令分隔符 `&&`/`||`/`;` 走 CONFIRM，但 PowerShell 真正的命令分隔符其实是分号；这里把 `||` 一并处理虽不算错，但只检查 lowered 字符串里"是否包含"，会对 `if ($x -lt 5) { ... }` 这种正常 `;` 也强制 CONFIRM。
  5. `Get-Content` 后接 `|` 然后跟一个非白名单命令（如 `ForEach-Object {...}`） → 第二段命令不在任何清单 → CONFIRM。但很多只读管道都会这样写，导致大量「假阳性 confirm」。
- 修复建议：
  1. 使用更严格的解析（最好启用 PowerShell AST 校验，但成本高），或把策略从"白名单"提升到"沙盒进程 + 临时账户"。
  2. DENY 模式追加：`invoke-expression`、`iex`、`&`、`cmd`、`pwsh -encoded`、`base64`。
  3. CONFIRM 改成黑名单 + 关键写入正则匹配，减少假阳性，但同时降低真阴性。

### T-03【高】shell 命令一次同意可被借势复用
- 位置：`core/agent_service.py:665-680`（命中 approved_shell_command）
- 问题：approved_once 只比对 `command == approved_command` 字符串相等，不强制清理：
  - LLM 在 round N 把同一条命令再次发出（参数全一致）可继续放行；只要在 round N+1 之前未被清理，就能跑两遍。
  - 用户同意 `Set-Content a.txt 'x'` 后，LLM 把它存到 plan note，下一个 step 再次发同样命令仍然命中（同 session 内）。
- 修复建议：
  1. 在 approved 命令执行**之前**立即清空 `approved_shell_command`，再去执行，避免任何条件分支下命令复用。
  2. 给 approved 加 TTL/计数：approved_count=1，执行一次即过期。
  3. approved 对象包含 `tool_call_id`，仅匹配本次 tool_call。

### T-04【高】`computer_shell` 写文件验证只是「提示」，没有强制
- 位置：`core/agent_service.py:687-696`
- 问题：仅在 observation 上追加一段 `[verification required]` 文案让 LLM "自觉"再跑 Test-Path/Get-Content。LLM 完全可以无视，直接返回"已完成"。
- 修复建议：
  1. 在 agent loop 里检测到刚执行了写命令、且下一轮 LLM 没主动发 verify call，强制注入 system 提示重新决策。
  2. 或者直接由 agent 服务在写命令执行后自动追加一次 Test-Path 调用并把结果加到 messages。

### T-05【高】`parse_tool_arguments` 解析失败时构造非法 kwargs
- 位置：`core/agent/helpers.py:36-45`
- 问题：JSON 解析失败时返回 `{"_raw": "..."}`，调用 `tool(**{"_raw": "..."})` 时：
  - `ComputerShellTool.execute(*, command, ...)` 必须有 `command` → 触发 `TypeError`，跳出 `try/except ToolError` 范围。
  - 异常被 `_handle_message` 外层 try 兜底成「我这边刚才有点卡住了」，但 task 已经写入 Redis，下次恢复时仍包含损坏数据。
- 修复建议：
  1. 解析失败时返回空 dict + 错误标记，立刻构造 `ToolResult(error="arguments parse failed: ...")` 反馈给 LLM，不调用工具。
  2. 同时统一在 `ToolCollection.execute` 里捕获 `TypeError`，转为 `ToolFailure`。

### T-06【中】`tool_map` 不区分大小写 / 别名
- 位置：`core/tool/tool_collection.py:35-38`
- 问题：LLM 偶尔会用 `Tavily_Search`、`tavilySearch` 之类的名字，`tool_map.get` 直接 miss → `ToolFailure("Tool X is invalid")`，浪费一轮。
- 修复建议：建索引时做 `name.lower()`；可同时维护别名表（`computerShell -> computer_shell`）。

### T-07【中】Tool 结果不限长度，token 直接爆
- 位置：`core/agent/helpers.py:48-53`（`format_tool_result`）、`core/tool/tavily_search/base.py:108-150`
- 问题：`TavilySearchResponse.populate_output` 对每条 result 做了 1000 字截断，但 results 数量没限制（默认 5、最多 20），加上 raw_content、answer、image 描述，单次工具结果上万 char 不少见。`task.messages` 持续追加，几轮后超出 LLM 上下文。
- 修复建议：
  1. 设置总长 cap（如 6000 字）。超出后头尾截断 + `... omitted ...` 标记。
  2. `format_tool_result` 也加一层 truncate。

### T-08【中】MAX_TOOL_ROUNDS 默认 3 偏低，complex plan 直接被截断
- 位置：`config.py:57`
- 问题：planning 流程在每个 step 又会跑一遍 agent loop（每个 step ≤ 3 轮工具）。一个真正复杂的 step（先 list 文件 → 再读 → 再写 → verify）至少 4 轮，必然命中"已达上限"分支。
- 修复建议：
  1. 把 `MAX_TOOL_ROUNDS` 提到 6–8；为 planning 模式单独设较高值。
  2. 计数策略改为「连续 N 轮没有新观察」才退出，而不是总轮数。

### T-09【中】最大轮数兜底消息追加在 `user` role 下，触发奇怪角色排列
- 位置：`core/agent_service.py:594-604`
- 问题：在最后一次循环结束后，append `{"role": "user", "content": "You have reached the maximum tool rounds..."}`。
  - 与真实用户消息混在一起；下次恢复时 `normalize_history` 会把它写进 session.history（如果路径会落到 history），让下一轮 LLM 看到自己之前发给自己的系统话。
- 修复建议：用 `system` role 或在 message 上标记 `meta=True`，不进 session.history。

### T-10【中】Tavily 结果中的 `country` 与 `topic` 校验抢先返回
- 位置：`core/tool/tavily_search/tavily_search.py:41-45`
- 问题：当 `country` 非空但 `topic != "general"` 时直接报错。
  - 但 LLM 经常默认填 `country="cn"`，结果工具失败。
- 修复建议：要么忽略 `country`，要么自动把 topic 设回 `general` + 在 observation 给出提示。

### T-11【中】`PlanningTool` 的 `create/update` 命令实际上永远不会被 agent 执行
- 位置：`core/agent_service.py:653-662`、`core/tool/planning.py:80-130`
- 问题：agent_service 的 `_execute_planning_tool` 只支持 `get / mark_step`，而 `PlanningTool` 暴露给 LLM 的参数里有 `create / update`。
  - LLM 选择 `create` 时，进入 `_execute_planning_tool` → 返回 `"Planning command is not supported during step execution."`，但 LLM 视角并不能感知这是"上下文不允许"还是"参数错误"，可能反复尝试。
  - 同时 tool description 暴露 `create / update` 让 LLM 误以为可以自创计划。
- 修复建议：
  1. 给两套 schema：决策阶段用全功能 PlanningTool；step 执行阶段单独包一个 ReadonlyPlanningTool（只暴露 get/mark_step）。
  2. 或者在描述里明确"创建/更新计划由系统完成，本轮只能 get/mark_step"。

### T-12【低】`AskHuman.execute` 直接 echo 输入，没做截断
- 位置：`core/tool/ask_human.py:23-24`
- 问题：LLM 可以把整段长文塞进 inquire，让用户被洪水提问。
- 修复建议：截断到 200 字符并丢弃换行。

### T-13【低】`Terminate.execute` 返回字符串而非 `ToolResult`
- 位置：`core/tool/terminate.py:23-25`
- 问题：与 `BaseTool` 其它工具风格不一致；`tool_collection.execute` 期待 `ToolResult` 才能读 `error/output`。Terminate 返回的字符串会被 `getattr(result, "error", None)` 取到 None，巧合下能用，但若日后改 collection 逻辑会出错。
- 修复建议：包装为 `self.success_response(f"...status: {status}")`。

### T-14【低】CONFIRM 路径没暴露重新分类的机会
- 位置：`core/tool/computer/shell.py:62-71`
- 问题：用户同意一次后 `approved_once=True` 跳过分类。但若 LLM 微调命令（添加 `-Force`），仍跳过分类。原因在于 `agent_service` 通过外层比较 command 字符串决定 approval。一旦命中 `approved_shell_command` 比较且字符串恰好一致，就走 approved_once；若不一致就重新跑 `classify_command`。逻辑链条复杂、容易引入漏洞。
- 修复建议：把 approved 状态收敛到 ComputerShellTool 内部，外部传 token 即可。

---

## 3. 业务对话逻辑（Business Conversation Logic）

### B-01【高】图片描述异步写入导致 `prompt_image_context` 永远「迟一拍」
- 位置：`bot/telegram_channel.py:240-262`、`core/agent/context.py:38-40`
- 问题：`on_photo` 先 `publish_user_message`，再 `asyncio.create_task(_save_image_desc_async(...))`。
  - 当前轮：图片已经送进 LLM（多模态），prompt 里的 image_context 来自 **上一张图** 的缓存（因为代码 `if not images: prompt_image_context = await session.get_last_image_desc(user_id)`，本轮有图片所以跳过，但下一轮没图片时拿到的是旧值还是新值取决于 race）。
  - 下一轮（纯文字）：图片描述任务可能尚未完成 → 用户拿不到关于"刚才那张图"的回忆；或者完成了但用户又发了新图，描述被覆盖。
- 修复建议：
  1. 图片描述生成改为同步：放到 `_handle_message` 内部 await，落到 prompt 后再 publish outbound。
  2. 或者在 set/get 上加版本号 + 等待事件。

### B-02【高】`coerce_user_id` 对非数字 sender 使用进程内 hash
- 位置：`core/agent/helpers.py:124-128`
- 问题：Python `hash(str)` 默认开启随机化（`PYTHONHASHSEED=random`），每次进程重启 hash 值不同 → 用户 ID 完全错位，原本的历史/亲密度/记忆全部丢失。
- 修复建议：换成稳定散列，例如 `int(hashlib.sha1(value.encode()).hexdigest()[:8], 16)`，或者直接拒绝非数字 sender 并要求 channel 适配器统一映射。

### B-03【高】`_after_final_reply` 在 waiting_human 路径下完全跳过 history 落库
- 位置：`core/agent_service.py:199-211 / 270-282 / 359-369`
- 问题：进入 `waiting_human` 时 `if task.status != "waiting_human": await self._after_final_reply(...)` 跳过。
  - 用户的提问没写进 session.history；agent 提出的确认问题也没写进 history。
  - 下次恢复仅依赖 `task.messages`，但 `prepare_agent_context` 在 task 完成后重建 system prompt 时只从 session.history 取上下文。
  - 长 waiting_human 链路完成之后只保留首条 user message + 末条 reply，中间澄清细节全部不可回溯。
- 修复建议：
  1. 提问时也 append 到 history（标记 role='assistant', meta='question'），让长链路完整。
  2. 或者在 task 完成时把整段 task.messages 摘要后写进 history。

### B-04【高】`/reset` 把亲密度一起清掉
- 位置：`core/session/cleanup.py:14-21`、`core/session/state.py:14-22`
- 问题：`/reset` → `clear_history` → `del state_key(user_id)`。状态包含 `intimacy_level`，下一次 `get_state` 见 key 不存在，返回初始值 `INTIMACY_INIT`。用户清个上下文，养了几周的"亲密度"瞬间归零。
- 修复建议：
  1. `clear_history` 只清 conversation 表和 history cache，不动 state。
  2. 单独提供 `/forget_me` 显式重置全部信息。

### B-05【中】`/switch` 切角色也清空整段 state
- 位置：`bot/telegram_channel.py:205-209`
- 问题：与 B-04 同根。换角色调用 `clear_history` → 亲密度归零。是否该重置因业务而定，至少需要显式提示用户。
- 修复建议：可选项「保留亲密度切换 / 重置一切切换」由用户选；或写在角色 YAML 里。

### B-06【中】`bump_intimacy` 读改写无锁
- 位置：`core/session/state.py:40-47`
- 问题：高并发同一用户多条消息时（比如长消息被 Telegram 拆成多段），可能并发 `get + set`，造成丢失增量。
- 修复建议：用 Redis `HINCRBY` 直接原子加，再 `HSET min(...,100)` 兜底（或用 Lua 脚本 cap 在 100）。

### B-07【中】`emotion` 在 resume waiting_human 时基于最新短消息判断
- 位置：`core/agent_service.py:128 / 192`
- 问题：用户原始情绪是 `sad`，回复确认词 `好的`，emotion 重新识别为 `neutral`，整轮对话语气控制偏轻松。
- 修复建议：waiting_human resume 时复用 task 起始的 emotion，或对 ≤4 字的回复保留旧情绪。

### B-08【中】`MAX_HISTORY_TURNS` 死配置
- 位置：`config.py:68-69`
- 问题：`MAX_HISTORY_TURNS=12` 没被任何代码引用；真正生效的是 `MAX_HISTORY_MSGS=24`。当运维想"再多记一点历史"调高 TURNS 时不会生效，反而误导。
- 修复建议：移除 TURNS 或在 history 处按 turn pair 截断。

### B-09【中】`normalize_history` 丢弃 tool / tool_calls，跨轮工具上下文不可见
- 位置：`core/agent/helpers.py:56-63`
- 问题：每次新对话从 session.history 取上下文，但只保留 user/assistant content，工具调用历史全部丢。
  - 比如上一轮做了 tavily 搜索，本轮 LLM 不知道搜过哪些。
- 修复建议：在 assistant 文本里附加"我刚才搜了 X"的可读化轨迹；或在 history 表新增 tool_traces 字段。

### B-10【中】Telegram 输出消息走 HTML 但渲染器易产出无效 HTML
- 位置：`bot/telegram_channel.py:75-81`、`core/agent/formatter.py:60-108`
- 问题：`_to_html` 自定义实现 markdown→HTML，且通过 `re.sub(r"<b>(.*?)</b>", ...)` 互相转换。
  - 文本里包含未配对的 `<b>` 或包含 `<script>` 写法，会导致 Telegram 400 "can't parse entities"。
  - 出错时 `_on_outbound` 3 次重试用同一份内容，3 次都失败 → 用户看不到任何回复。
- 修复建议：
  1. 改用经过测试的 Markdown→HTML 库（`telegram.helpers.escape_markdown_v2` + MarkdownV2，或仅发纯文本）。
  2. 失败时 fallback 到纯文本 `parse_mode=None` 再发一次。

### B-11【中】单 worker 串行处理所有用户
- 位置：`main.py:74-79`
- 问题：`_agent_worker` 只起一个，一次只能处理一条 inbound。一个慢 LLM/慢 tool 把所有用户阻塞。
- 修复建议：起 N 个 worker（按 CPU/外部 API 限流配置），或按 chat_id 做 round-robin 分桶 + 独立队列。

### B-12【中】没有任何速率限制 / 滥用保护
- 位置：`bot/telegram_channel.py`
- 问题：用户可短时间内连续发图、长文本，触发大量外部 API 调用（Tavily 计费、Ollama GPU 占用、Telegram 出口 token 耗尽）。
- 修复建议：基于 Redis 实现 sliding window 限流（用户级 + 全局），超限直接回 "请稍候再试"。

### B-13【低】`on_message` 文本读取存在运算优先级写法陷阱
- 位置：`bot/telegram_channel.py:226`
- 问题：`text = (update.message.text if update.message else "" or "").strip()`
  - 期望是 `(update.message.text or "")`，实际等价于 `update.message.text if update.message else ""`。
  - `filters.TEXT` 多数情况保证 text 非空，但极端场景 text 可能是 None（比如服务消息），`.strip()` 会 AttributeError。
- 修复建议：改成 `text = ((update.message.text or "") if update.message else "").strip()`。

### B-14【低】图片体积没有上限校验
- 位置：`bot/telegram_channel.py:231-245`
- 问题：直接 `download_as_bytearray()` 然后整张 base64 编码持有在内存。Telegram 限 10MB 原始图片，base64 后 ~13.3MB；几路并发就会吃光小机器。
- 修复建议：先看 `photo.file_size` 大小或下载后判断，超阈值返回提示。

### B-15【低】memory 模块整体禁用但仍调用 build_memory_summary
- 位置：`core/agent_service.py:893-895`（注释）
- 问题：保存路径被注释，但每轮仍调用 `memory_service.build_memory_summary` 拼到 prompt（context.py: `memory_summary=...`）。
- 影响：summary 大概率是空字符串/默认值，prompt 多一段无用文本；如果 memory service 还在做 LLM 检索调用，会浪费成本。
- 修复建议：在 build_memory_summary 内短路返回 ""，或在 prepare_agent_context 中用 feature flag 完全跳过。

---

## 4. 其它横向问题

### X-01【中】Redis 失败时优雅降级不一致
- `load_task / save_task / get_history / clear_history` 各自只 log warning 然后返回 None / 空列表 / 静默成功。
  - 用户视角：消息看似正常处理，但 task 状态没真正持久化，下一次必然丢上下文。
- 修复建议：Redis 不可用时短路一条系统提示给用户 "我现在暂时记不住对话，请稍后再试"。

### X-02【中】SQLite 单文件并发写
- `core/session/history.py:54-67` 每条消息开/关一次 `aiosqlite.connect`，没有连接池，没启用 WAL。
  - 高频写入下会出现 `database is locked`。
- 修复建议：启用 `PRAGMA journal_mode=WAL`；或用单一长连接 + asyncio.Lock。

### X-03【中】PowerShell 子进程在 Windows 下无 chcp/UTF-8 设置
- `core/tool/computer/shell.py:90-101`
- 问题：Windows PowerShell 默认输出 GBK，`_decode` 用 utf-8 ignore replace，结果出现大量 `?` 字符，LLM 难以解读。
- 修复建议：在命令前加 `$OutputEncoding=[Console]::OutputEncoding=[Text.UTF8Encoding]::new();` 或 ensure command 加 `chcp 65001 > $null;`。

### X-04【低】LLM 模型温度配置但 `LLM_SEND_SAMPLING_PARAMS=False` 时不下发
- `llm/api.py:149-153`、`config.py:50-52`
- 现状：默认不下发 sampling 参数。某些第三方 API（DeepSeek）会用各自默认 temperature，行为与本地 Ollama 不一致。
- 修复建议：在文档/启动日志里明确提示当前是否发 sampling 参数；新增按 provider 自适配的开关。

### X-05【低】启动时 RAG scan 失败仅记 warning，丢失关键检索能力
- `main.py:49-60`
- 问题：scan_and_index 失败时不会重试也不会广播状态。若用户依赖 RAG 回答某类查询，会"静默没记忆"。
- 修复建议：失败时存一个全局标志，对应 prompt 里降级；并在 `/help` 之类命令里显示 RAG 状态。

### X-06【低】测试 `tests/test_agent_service_planning_resume.py` 用 `SimpleNamespace` 替代 service
- 现状：FakeSession 实现了 `get_history` 返回 []。但 `_handle_message` 走 `prepare_agent_context` 还会调用 `memory_service.build_memory_summary` 等多个方法，`SimpleNamespace()` 没有这些方法。
- 测试现状能跑通是因为大多数用例进入了 resume 分支，没走到 prepare_agent_context。
- 修复建议：补一份 FakeMemoryService / FakePromptEngine，让"首轮规划"的端到端测试也跑得起来；防止后续修改 prepare_agent_context 时把 resume 路径一起带坏。

---

## 建议优先级
高优先级（影响安全/正确性）：**P-01、P-02、T-01、T-02、T-03、T-04、T-05、B-01、B-02、B-03、B-04**。
中优先级（影响体验/可维护性）：P-03 ~ P-07、T-06 ~ T-11、B-05 ~ B-12、X-01 ~ X-03。
低优先级（小问题/可观测）：其余条目。

建议从 P-01（同意判定）、T-01/T-02/T-03/T-04（shell 安全）、B-01（图片 race）这条线先修，能消除最大的"做错事"风险。
