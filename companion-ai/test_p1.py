"""P1 模块集成测试"""
import sys, os, asyncio
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── 1. 情绪检测 ────────────────────────────────────────────────────────────────
from core.emotion_detector import detect
print("=== 情绪检测 ===")
cases = ["今天好开心哈哈", "好累好烦", "喜欢你", "压力好大崩了", "今天吃了啥"]
for t in cases:
    r = detect(t)
    print(f"  [{r.tag:8s}] {t}")

# ── 2. Prompt Engine ───────────────────────────────────────────────────────────
from core.prompt_engine import PromptEngine
from core.emotion_detector import EmotionResult
print("\n=== Prompt Engine（sad + intimacy=45）===")
pe = PromptEngine()
prompt = pe.build_system_prompt("jiejie", "小明", EmotionResult("sad", "温柔安慰，放慢节奏"), 45)
print(prompt)

# ── 3. Redis + SessionManager ──────────────────────────────────────────────────
from db.models import init_db
from core.session_manager import SessionManager

async def test_session():
    await init_db()
    sm = SessionManager()
    uid = 88888

    # 清理旧数据
    from db.redis_client import get_redis
    r = get_redis()
    await r.delete(f"session:{uid}:history", f"session:{uid}:state")

    await sm.ensure_user(uid, "test_user")
    await sm.append_message(uid, "user", "我叫小明，喜欢打篮球", "neutral")
    await sm.append_message(uid, "assistant", "哦，小明，喜欢运动挺好的", "neutral")
    await sm.bump_intimacy(uid, "romantic")
    await sm.bump_intimacy(uid, "romantic")

    history = await sm.get_history(uid)
    intimacy = await sm.get_intimacy(uid)
    user = await sm.get_user(uid)

    print("\n=== Session Manager ===")
    print(f"  历史条数: {len(history)}")
    print(f"  历史内容: {history}")
    print(f"  亲密度:   {intimacy}（初始20，+5+5 应为30）")
    print(f"  用户记录: {user}")

asyncio.run(test_session())
print("\n✅ 全部测试通过")
