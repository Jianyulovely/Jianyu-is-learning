"""
回复内容格式化：
1. LaTeX 符号 → Unicode 等价字符
2. Markdown 表格 → 代码块（Telegram 等宽字体可读）
"""
import re

# ── LaTeX 符号映射表 ──────────────────────────────────────────────────────────

_SYMBOLS = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\theta": "θ", r"\lambda": "λ",
    r"\mu": "μ", r"\nu": "ν", r"\pi": "π", r"\sigma": "σ", r"\tau": "τ",
    r"\phi": "φ", r"\varphi": "φ", r"\psi": "ψ", r"\omega": "ω",
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Sigma": "Σ", r"\Lambda": "Λ",
    r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
    r"\infty": "∞", r"\sum": "∑", r"\prod": "∏", r"\int": "∫",
    r"\partial": "∂", r"\nabla": "∇", r"\sqrt": "√",
    r"\leq": "≤", r"\geq": "≥", r"\neq": "≠", r"\approx": "≈",
    r"\equiv": "≡", r"\sim": "∼", r"\propto": "∝",
    r"\rightarrow": "→", r"\leftarrow": "←", r"\leftrightarrow": "↔",
    r"\Rightarrow": "⟹", r"\Leftarrow": "⟸", r"\to": "→",
    r"\times": "×", r"\cdot": "·", r"\pm": "±", r"\mp": "∓",
    r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\cup": "∪", r"\cap": "∩",
    r"\forall": "∀", r"\exists": "∃",
    r"\ldots": "…", r"\cdots": "…",
}

_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUB = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")


def _to_sup(s: str) -> str:
    return s.translate(_SUP) if all(c in "0123456789+-=()n" for c in s) else f"^{s}"


def _to_sub(s: str) -> str:
    return s.translate(_SUB) if all(c in "0123456789+-=()aeoxhklmnpst" for c in s) else f"_{s}"


def _convert_latex(text: str) -> str:
    # \frac{a}{b} → (a/b)
    text = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1/\2)", text)

    # \mathbf{x}、\mathrm{x} 等 → 保留内容
    text = re.sub(r"\\math\w*\{([^}]+)\}", r"\1", text)

    # \text{...} → 保留内容
    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)

    # \operatorname{name} → name
    text = re.sub(r"\\operatorname\{([^}]+)\}", r"\1", text)

    # 上标：^{...} 或 ^x
    text = re.sub(r"\^\{([^}]+)\}", lambda m: _to_sup(m.group(1)), text)
    text = re.sub(r"\^([0-9+\-n])", lambda m: _to_sup(m.group(1)), text)

    # 下标：_{...} 或 _x
    text = re.sub(r"_\{([^}]+)\}", lambda m: _to_sub(m.group(1)), text)
    text = re.sub(r"_([0-9])", lambda m: _to_sub(m.group(1)), text)

    # 符号替换（从长到短，避免前缀误匹配）
    for cmd, sym in sorted(_SYMBOLS.items(), key=lambda x: -len(x[0])):
        text = text.replace(cmd, sym)

    # 去掉 $$ 和 $ 分隔符（保留内容）
    text = re.sub(r"\$\$([^$]*)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$([^$\n]+)\$", r"\1", text)

    # 清理剩余反斜杠命令和花括号
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)

    return text


# ── 表格 → 代码块 ─────────────────────────────────────────────────────────────

_TABLE_LINE = re.compile(r"^\s*\|.+\|\s*$")


def _wrap_tables(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    table_buf: list[str] = []

    def flush():
        if table_buf:
            result.append("```")
            result.extend(table_buf)
            result.append("```")
            table_buf.clear()

    for line in lines:
        if _TABLE_LINE.match(line):
            table_buf.append(line)
        else:
            flush()
            result.append(line)
    flush()

    return "\n".join(result)


# ── HTML 转换 ─────────────────────────────────────────────────────────────────

def _to_html(text: str) -> str:
    """代码块转 <pre>，**bold** 转 <b>，其余部分转义 HTML 实体。"""
    parts = re.split(r"(```[\s\S]*?```)", text)
    result = []
    for part in parts:
        if part.startswith("```"):
            inner = part[3:-3].strip()
            inner = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            result.append(f"<pre>{inner}</pre>")
        else:
            part = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # ## 标题 → <b>标题</b>
            part = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", part, flags=re.MULTILINE)
            part = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", part, flags=re.DOTALL)
            result.append(part)
    return "".join(result)


# ── 对外接口 ──────────────────────────────────────────────────────────────────

def format_reply(text: str) -> str:
    # 模型有时直接输出 HTML 标签而非 Markdown，统一规范化后再处理
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i>(.*?)</i>", r"_\1_", text, flags=re.DOTALL | re.IGNORECASE)
    text = _wrap_tables(text)
    text = _convert_latex(text)
    text = _to_html(text)
    return text
