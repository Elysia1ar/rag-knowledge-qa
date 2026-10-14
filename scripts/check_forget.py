"""遗忘机制验证。

用法：
    python -m scripts.check_forget
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.memory import long_term
from app.memory.forget import run_forget_pipeline
from app.services.auth_service import get_user_by_username


# 造一些重复 / 老 / 低分的记忆
SAMPLE = [
    # 语义重复对
    ("用户偏好用表格对比技术选型", "preference", 0.80),
    ("用户偏好使用表格方式对比理解技术", "preference", 0.70),
    # 高重要性（保留）
    ("用户是字节跳动算法工程师", "fact", 0.90),
    ("用户在做 RAG 项目", "fact", 0.90),
    # 低重要性（可能被时间衰减，但新建的不删）
    ("用户今天问了一次天气", "event", 0.10),
    ("用户说过'哈哈'", "event", 0.10),
    # 又一个语义重复
    ("用户从事推荐算法相关工作", "fact", 0.75),
    ("用户主要做推荐系统方向的工作", "fact", 0.65),
]


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, "admin")
        if not user:
            print("⚠️  没有 admin 用户")
            return

        print(f"用户: {user.username} (id={user.id})\n")

        # 清空 + 重建
        await long_term.clear_user_memories(db, user.id)
        await long_term.save_extracted(db, user.id, [
            {"content": c, "type": t, "importance": i}
            for c, t, i in SAMPLE
        ])

        print(f"写入 {len(SAMPLE)} 条记忆\n")

        # 列出
        print("=" * 60)
        print("1. 遗忘前")
        print("=" * 60)
        for m in await long_term.list_memories(db, user.id):
            print(f"  [{m.id}] imp={m.importance:.2f} | {m.content}")

        # 跑遗忘
        print(f"\n{'=' * 60}")
        print("2. 运行遗忘流程")
        print("=" * 60)
        result = await run_forget_pipeline(db, user.id)
        print(f"\n结果: {result}")

        # 列出
        print(f"\n{'=' * 60}")
        print("3. 遗忘后")
        print("=" * 60)
        for m in await long_term.list_memories(db, user.id):
            print(f"  [{m.id}] imp={m.importance:.2f} | {m.content}")


if __name__ == "__main__":
    asyncio.run(main())