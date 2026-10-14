"""Agent 冒烟测试。

用法：
    python -m scripts.check_agent
    python -m scripts.check_agent "自定义问题"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.react_agent import get_react_agent
from app.core.logging import setup_logging


DEFAULT_QUESTIONS = [
    # 单跳：一次检索即可
    "RAG 的典型管线包括哪些步骤？",

    # 多跳：需要多次检索（考察 Agent 规划能力）
    "Chroma 和 Milvus 分别适合什么场景？如果要处理十亿级向量该选哪个？",

    # 工具调用：时间
    "现在几点了？",

    # 工具调用：列文档
    "知识库里都有哪些文档？",

    # 拒答：知识库无相关内容
    "今天天气怎么样？",
]


def run_once(agent, question: str, verbose: bool = True) -> str:
    """跑一次 Agent，返回最终回答。"""
    print(f"\n{'=' * 72}\n❓ {question}\n{'=' * 72}")

    result = agent.invoke({
        "messages": [HumanMessage(content=question)],
        "iterations": 0,
    })

    # 遍历消息，展示思考过程
    if verbose:
        for msg in result["messages"]:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  🔧 调用工具: {tc['name']}")
                        print(f"     参数: {tc['args']}")
                elif msg.content:
                    print(f"\n💡 回答：\n{msg.content}")
            elif isinstance(msg, ToolMessage):
                preview = str(msg.content)[:150].replace("\n", " ")
                print(f"  📄 工具返回: {preview}...")

    # 最终回答 = 最后一条有内容的 AIMessage
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content

    return ""


def main() -> None:
    setup_logging()

    questions = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_QUESTIONS

    print("构建 Agent 中……")
    agent = get_react_agent()
    print("✅ Agent 就绪\n")

    for q in questions:
        run_once(agent, q)


if __name__ == "__main__":
    main()