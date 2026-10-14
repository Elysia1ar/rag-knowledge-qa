"""RAG Prompt 模板：强约束防幻觉 + 引用溯源。"""
from langchain_core.prompts import ChatPromptTemplate


SYSTEM_PROMPT = """你是一个严谨的知识库问答助手。你的任务是根据提供的【参考资料】回答用户问题。

严格遵守以下规则：
1. 只依据【参考资料】中的内容作答，不得依赖你的先验知识或编造信息。
2. 如果【参考资料】不足以回答该问题，直接回答："根据现有知识库，我无法回答该问题。"不要猜测。
3. 回答时，在引用了具体资料的地方，用 [编号] 标注来源，例如：[1]、[2]。
4. 如果多条资料相互矛盾，如实指出矛盾，并说明各自的说法。
5. 回答要简明扼要，条理清晰，优先使用列表或分点方式。
6. 使用中文回答。"""


USER_PROMPT = """【参考资料】
{context}

【用户问题】
{question}

请根据上述资料作答："""


def build_qa_prompt(memory_block: str = "") -> ChatPromptTemplate:
    """动态构造 QA Prompt。

    有 memory_block 时追加到 system 段，
    让 LLM 知道"关于用户的已知信息"。
    """
    system = SYSTEM_PROMPT
    if memory_block.strip():
        system = f"{SYSTEM_PROMPT}\n\n{memory_block}"

    return ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", USER_PROMPT),
    ])


# 向后兼容：无记忆的默认 Prompt
QA_PROMPT = build_qa_prompt()


CONDENSE_SYSTEM = """你是一个问题改写助手。
根据对话历史，将用户的最新提问改写为一个独立、完整、不依赖上下文的问题。
只输出改写后的问题，不要解释，不要加引号。"""

CONDENSE_USER = """【对话历史】
{chat_history}

【最新提问】
{question}

改写后的独立问题："""

CONDENSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONDENSE_SYSTEM),
    ("human", CONDENSE_USER),
])