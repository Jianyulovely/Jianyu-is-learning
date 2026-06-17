"""
Reply formatting for agent output:
1. Convert common LaTeX symbols to readable Unicode equivalents.
2. Wrap markdown tables as code blocks for fixed-width rendering.
3. Normalize simple markdown/HTML for Telegram-friendly output.
"""
import re

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
    r"\Rightarrow": "⇒", r"\Leftarrow": "⇐", r"\to": "→",
    r"\times": "×", r"\cdot": "·", r"\pm": "±", r"\mp": "∓",
    r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\cup": "∪", r"\cap": "∩",
    r"\forall": "∀", r"\exists": "∃",
    r"\ldots": "…", r"\cdots": "⋯",
}

_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUB = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")


def _to_sup(s: str) -> str:
    return s.translate(_SUP) if all(c in "0123456789+-=()n" for c in s) else f"^{s}"


def _to_sub(s: str) -> str:
    return s.translate(_SUB) if all(c in "0123456789+-=()aeoxhklmnpst" for c in s) else f"_{s}"


def _convert_latex(text: str) -> str:
    text = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1/\2)", text)
    text = re.sub(r"\\math\w*\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\operatorname\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\^\{([^}]+)\}", lambda m: _to_sup(m.group(1)), text)
    text = re.sub(r"\^([0-9+\-n])", lambda m: _to_sup(m.group(1)), text)
    text = re.sub(r"_\{([^}]+)\}", lambda m: _to_sub(m.group(1)), text)
    text = re.sub(r"_([0-9])", lambda m: _to_sub(m.group(1)), text)

    for cmd, sym in sorted(_SYMBOLS.items(), key=lambda x: -len(x[0])):
        text = text.replace(cmd, sym)

    text = re.sub(r"\$\$([^$]*)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$([^$\n]+)\$", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)
    return text


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


def _to_html(text: str) -> str:
    parts = re.split(r"(```[\s\S]*?```)", text)
    result = []
    for part in parts:
        if part.startswith("```"):
            inner = part[3:-3].strip()
            inner = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            result.append(f"<pre>{inner}</pre>")
        else:
            part = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            part = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", part, flags=re.MULTILINE)
            part = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", part, flags=re.DOTALL)
            result.append(part)
    return "".join(result)


def format_reply(text: str) -> str:
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i>(.*?)</i>", r"_\1_", text, flags=re.DOTALL | re.IGNORECASE)
    text = _wrap_tables(text)
    text = _convert_latex(text)
    text = _to_html(text)
    return text
