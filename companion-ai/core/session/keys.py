def history_key(user_id: int) -> str:
    return f"session:{user_id}:history"


def state_key(user_id: int) -> str:
    return f"session:{user_id}:state"


def image_desc_key(user_id: int) -> str:
    return f"session:{user_id}:last_image_desc"
