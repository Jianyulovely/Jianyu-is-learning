import json

def decode_keywords(keywords_json: str) -> list[str]:
    """将字符串转换为字符串列表"""
    try:
        data = json.loads(keywords_json or "[]")
    except json.JSONDecodeError:
        return []
    results: list[str] = []
    for item in data:
        token = str(item).strip().lower()
        if token and token not in results:
            results.append(token)
    return results

def merge_keywords(exist_kw: list[str], new_kw: list[str]) -> list[str]:
    """更新相关记忆中的关键词内容"""
    merged: list[str] = []
    for token in exist_kw + new_kw:
        normalized = str(token).strip().lower()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged