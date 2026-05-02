import re
import unicodedata


def _clean(text: str) -> str:
    """去除 PDF 中常见的控制字符和 Unicode 私用区字符，保留可读内容。"""
    # 去除 ASCII 控制字符（保留 \t \n）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # 去除 Unicode 私用区（PDF 字体映射常用）
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    # NFKC 规范化（合字 ﬁ→fi 等）
    text = unicodedata.normalize("NFKC", text)
    return text.strip()