# RAG Knowledge QA

> 一个生产级 RAG 知识库问答系统。支持**混合检索 + 重排**、**多格式结构感知分块**、**ReAct / Plan-and-Solve Agent**、**短期摘要 + 长期向量记忆**，配套 Vue3 前端与 Docker 部署，并用 RAGAS 做**量化消融实验**。

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.4-1C3C3C)](https://python.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-FF6F00)](https://langchain-ai.github.io/langgraph/)
[![Vue](https://img.shields.io/badge/Vue-3.5-42B883)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 亮点

- **混合检索 + Cross-Encoder 重排**：向量 + BM25 双路召回，RRF 融合，BGE-Reranker 精排，形成漏斗式架构
- **量化评估**：基于 RAGAS 四指标的消融实验，每一层优化的贡献都可量化
- **多格式结构感知分块**：策略模式 Chunker，TXT 递归 / Markdown 按标题 / PDF 按页 / Word 按样式层级
- **双 Agent 模式**：基于 LangGraph 手写 ReAct 状态图与 Plan-and-Solve 三阶段图，思考链可视化
- **双层记忆系统**：短期滑动窗口 + LLM 增量摘要；长期向量化记忆 + 多因素综合评分 + 遗忘机制
- **可溯源**：每个回答带引用编号，引用卡片按文件类型展示页码 / 章节定位
- **防幻觉**：Prompt 强约束 + Rerank 分数阈值双段拒答
- **真流式输出**：SSE 转发 LLM 真实 token，首字节延迟 < 1s
- **幂等索引**：基于文件 MD5 的增量入库，未变更则跳过

## 消融实验结果

在 40 条 Golden Set 上的三种检索配置对比（DeepSeek + bge-small-zh + bge-reranker-base）：

| 配置 | Faithfulness | Answer Relevancy | **Context Precision** | **Context Recall** |
|------|--------------|------------------|----------------------|-------------------|
| baseline（纯向量） | 0.8671 | 0.8737 | 0.8017 | 0.8421 |
| + BM25（混合检索） | 0.9201 | 0.8906 | 0.8492 | 0.9231 |
| **+ Rerank（完整方案）** | 0.8351 | **0.9732** | **0.9252** | **0.9231** |

- 混合检索把 **Context Recall 提升 8.1%**（0.8421 → 0.9231）
- 重排在此基础上把 **Context Precision 再提升 7.6%**（0.8492 → 0.9252）
- 每一层优化都有独立可量化的贡献

> 详细样本和结果见 `data/eval/results/ablation.json`

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client (Vue3 / curl)                       │
├──────────────────────────────────────────────────────────────────┤
│                  FastAPI  (JWT / SSE / REST)                      │
├──────────────────────────────────────────────────────────────────┤
│  Chat Pipeline                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐        │
│  │ Condense │─▶│ Hybrid   │─▶│ Rerank   │─▶│ LLM       │        │
│  │ (改写)    │  │ Retrieval│  │(Cross-   │  │ Generate  │        │
│  │          │  │(向量+BM25│  │Encoder)  │  │ + Memory  │        │
│  └──────────┘  │ +RRF)    │  └──────────┘  └───────────┘        │
│                └──────────┘                                       │
│                                                                   │
│  Agent Modes (LangGraph)                                          │
│  ┌────────────────────┐  ┌─────────────────────────────┐         │
│  │ ReAct              │  │ Plan-and-Solve              │         │
│  │ Agent ⇄ Tools 循环 │  │ Planner → Executor → Solver │         │
│  └────────────────────┘  └─────────────────────────────┘         │
│                                                                   │
│  Memory System                                                    │
│  ┌──────────────────┐  ┌───────────────────────────────┐         │
│  │ 短期：窗口+摘要   │  │ 长期：向量库 + 综合评分 + 遗忘 │         │
│  └──────────────────┘  └───────────────────────────────┘         │
├──────────────────────────────────────────────────────────────────┤
│  Index Pipeline                                                   │
│  Load → Chunker(按类型分发) → Embed → Chroma                      │
├──────────────────────────────────────────────────────────────────┤
│  Storage                                                          │
│  Chroma (知识库 + 记忆库) │ SQLite (会话/文档/用户/记忆元数据)    │
│  BM25 (pickle)           │ HF Cache (模型)                       │
└──────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层 | 技术 |
|----|------|
| Web 框架 | FastAPI + Uvicorn |
| 编排框架 | LangChain 1.x（LCEL）+ LangGraph |
| 向量库 | ChromaDB（cosine + HNSW，双 collection） |
| Embedding | BAAI/bge-small-zh-v1.5（可切换 OpenAI / bge-large） |
| Reranker | BAAI/bge-reranker-base（Cross-Encoder） |
| LLM | DeepSeek / Qwen / OpenAI（OpenAI 兼容协议） |
| 关系库 | SQLAlchemy 2.0 + aiosqlite |
| 认证 | JWT (PyJWT) + bcrypt |
| 评估 | RAGAS |
| 前端 | Vue3 + TypeScript + Vite + Element Plus + Pinia |
| 部署 | Docker + docker-compose |
| 依赖管理 | uv |

## 快速开始

### 本地运行

```bash
# 1. 克隆
git clone https://github.com/Elysia1ar/rag-knowledge-qa.git
cd rag-knowledge-qa

# 2. 安装依赖
uv sync

# 3. 配置
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（DeepSeek 即可）

# 4. 索引示例文档
uv run python -m scripts.ingest

# 5. 启动服务
uv run uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`，默认管理员：`admin / admin123`。

### Docker 一键部署

```bash
docker compose up -d --build
```

首次启动会自动下载模型（约 3~5 分钟），之后秒级启动。健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

## API 示例

### 上传文档（需 admin 权限）

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@data/raw/rag_intro.txt"
```

### 普通问答（SSE 流式）

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "RAG 的典型管线包括哪些步骤？"}'
```

事件流：

```
event: progress   → {"stage": "retrieving"}
event: memory     → {"count": 2}
event: sources    → {"items": [...]}
event: progress   → {"stage": "generating"}
event: token      → {"text": "根"}
event: token      → {"text": "据"}
...
event: done       → {"session_id": "..."}
```

### Agent 模式

```bash
curl -N -X POST http://localhost:8000/api/v1/agent/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Chroma 和 Milvus 分别适合什么场景？", "agent_mode": "react"}'
```

`agent_mode` 可选 `react` 或 `plan`。

## 评估

```bash
# 快速验证（只跑 3 条）
uv run python -m scripts.run_eval --limit 3

# 完整消融实验（40 条 × 3 配置）
uv run python -m scripts.run_eval
```

结果落盘到 `data/eval/results/ablation.json`。

## 项目结构

```
rag-knowledge-qa/
├── app/
│   ├── api/                    # FastAPI 路由
│   ├── core/                   # 配置、日志、异常、安全
│   ├── db/                     # SQLAlchemy 模型与会话
│   ├── schemas/                # Pydantic 请求/响应
│   ├── services/               # 业务编排（会话、文档、问答、索引、统计）
│   ├── agent/                  # Agent 模块
│   │   ├── tools.py            # 工具集
│   │   ├── react_agent.py      # ReAct LangGraph
│   │   └── plan_solve_agent.py # Plan-and-Solve LangGraph
│   ├── memory/                 # 记忆系统
│   │   ├── short_term.py       # 滑动窗口 + 摘要压缩
│   │   ├── long_term.py        # 长期记忆存储与检索
│   │   ├── extractor.py        # 逐轮记忆提取
│   │   ├── consolidate.py      # 跨轮记忆固化
│   │   ├── scoring.py          # 综合评分
│   │   └── forget.py           # 遗忘机制
│   ├── rag/                    # RAG 核心
│   │   ├── loaders.py          # 多格式加载
│   │   ├── chunking/           # 策略模式 Chunker
│   │   ├── embeddings.py
│   │   ├── llm.py
│   │   ├── vectorstore.py      # Chroma 双 collection
│   │   ├── retrievers/         # 向量 / BM25 / 混合 / 重排
│   │   ├── chains/             # Prompt / QA / Condense
│   │   ├── pipeline/           # 索引 / 查询管线
│   │   └── evaluation/         # RAGAS 评估
│   └── utils/
├── data/
│   ├── raw/                    # 示例文档
│   ├── chroma/                 # 向量库持久化（gitignore）
│   ├── hf_cache/               # 模型缓存（gitignore）
│   └── eval/                   # Golden Set 和评估结果
├── frontend/                   # Vue3 前端
├── scripts/                    # CLI 工具
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 设计取舍

- **Chroma 而非 Milvus**：项目定位中小规模，Chroma 零运维；生产可无缝替换（接口抽象已就位）
- **bge-small 而非 bge-large**：开发阶段用轻量模型迭代快，`EMBEDDING_MODEL` 一行配置切换
- **Cross-Encoder 而非 LLM Rerank**：延迟低一个数量级，精度已足够
- **SQLite 而非 PostgreSQL**：单机零运维；SQLAlchemy 抽象下切换只需改 `DB_URL`
- **LangGraph 手写 StateGraph 而非 create_react_agent**：理解 Agent 循环的内部结构，便于自定义
- **知识库与记忆库独立 collection**：语义空间隔离，避免互相污染

## 常见追问

**Q：为什么不直接用向量检索，要做混合检索？**
A：向量擅长语义匹配，但对专有名词（如 `bge-reranker-large`）不敏感；BM25 擅长精确匹配但不懂语义。RRF 融合两者，Recall 提升 8 个点。

**Q：Agent 和普通 RAG 有什么本质区别？**
A：RAG 是固定管线，Agent 能自主决策——判断是否需要检索、拆成几个子问题、调用哪些工具。例如"现在几点了"这类问题，Agent 直接调时间工具，不走检索，节省一次 embedding + rerank。

**Q：长期记忆会不会越积越多？**
A：有完整的遗忘机制。语义去重（相似度 ≥ 0.85）、时间衰减（90 天且低分且从未访问）、容量淘汰（超 500 条按综合分淘汰）。

**Q：Rerank 分数阈值怎么定的？**
A：观察真实分布。相关问题的 Top-1 rerank 分数在 0.99+，无关问题（如"今天天气"）在 0.0018。阈值设 0.1 有很大余量。

## 后续规划

- [ ] HyDE 查询优化（假设文档嵌入）
- [ ] 用户反馈机制（点赞 / 点踩）
- [ ] 可观测性（Prometheus + Grafana）
- [ ] 速率限制与查询缓存
- [ ] 多模态支持（图片 OCR）

## License

MIT