# RAG Knowledge QA

> 一个生产级 RAG 知识库问答系统，支持混合检索、Cross-Encoder 重排、多轮对话、SSE 流式输出，并用 RAGAS 做量化评估与消融实验。

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.4-1C3C3C)](https://python.langchain.com/)

---

## 亮点

- **混合检索 + 重排**：向量召回 + BM25 关键词召回，RRF 融合，Cross-Encoder 精排，形成漏斗式检索
- **量化评估**：基于 RAGAS 四指标（Faithfulness / Answer Relevancy / Context Precision / Context Recall）的消融实验
- **可溯源**：每个回答带引用编号，对应到原始文档 chunk
- **防幻觉**：Prompt 强约束 + Rerank 分数阈值双段拒答
- **流式对话**：真·LLM token 级 SSE 流式，首字节延迟 < 1s
- **多轮会话**：基于 SQLite 持久化，自动进行问题改写指代消解
- **幂等索引**：基于文件 MD5 增量入库，文档未变则跳过

## 消融实验结果

在 40 条 Golden Set 上的三种配置对比（DeepSeek + bge-small + bge-reranker-base）：

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
┌──────────────────────────────────────────────────────────────┐
│                        Client (Web / curl)                    │
├──────────────────────────────────────────────────────────────┤
│                     FastAPI  (SSE / REST)                     │
├──────────────────────────────────────────────────────────────┤
│  Query Pipeline                                               │
│    ┌────────────┐   ┌──────────┐   ┌─────────┐   ┌────────┐  │
│    │ Condense   │──▶│ Hybrid   │──▶│ Rerank  │──▶│  LLM   │  │
│    │ (多轮改写)  │   │ Retrieval│   │(Cross-  │   │Generate│  │
│    │            │   │ (向量+BM25│   │Encoder) │   │        │  │
│    └────────────┘   └──────────┘   └─────────┘   └────────┘  │
├──────────────────────────────────────────────────────────────┤
│  Index Pipeline                                               │
│    Load → Split → Embed → Chroma (persist)                    │
├──────────────────────────────────────────────────────────────┤
│  Storage                                                      │
│    Chroma (向量) │ SQLite (会话/元数据) │ BM25 (pickle)      │
└──────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层 | 技术 |
|----|------|
| Web 框架 | FastAPI + Uvicorn |
| 编排框架 | LangChain 1.x（LCEL） |
| 向量库 | ChromaDB（cosine + HNSW） |
| Embedding | BAAI/bge-small-zh-v1.5（可切换 OpenAI / bge-large） |
| Reranker | BAAI/bge-reranker-base（Cross-Encoder） |
| LLM | DeepSeek / Qwen / OpenAI（OpenAI 兼容协议） |
| 关系库 | SQLAlchemy 2.0 + aiosqlite |
| 评估 | RAGAS |
| 部署 | Docker + docker-compose |
| 依赖管理 | uv |

## 快速开始

### 本地运行

```bash
# 1. 克隆
git clone <your-repo>
cd rag-knowledge-qa

# 2. 安装依赖
uv sync

# 3. 配置
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 4. 放入知识库文档
cp your-docs/* data/raw/

# 5. 索引文档
uv run python -m scripts.ingest

# 6. 启动服务
uv run uvicorn app.main:app --reload
```

访问 `http://localhost:8000/docs` 查看 API 文档。

### Docker 运行

```bash
# 构建 + 启动
docker compose up -d

# 查看日志（首次启动会下载模型，约 3~5 分钟）
docker compose logs -f

# 健康检查
curl http://localhost:8000/api/v1/health
```

## API 示例

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@data/raw/rag_intro.txt"
```

### 非流式问答

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "RAG 的典型管线包括哪些步骤？"}'
```

### 流式问答（SSE）

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Bi-Encoder 和 Cross-Encoder 有什么区别？"}'
```

事件流：

```
event: progress   → {"stage": "retrieving"}
event: sources    → {"items": [...]}
event: progress   → {"stage": "generating"}
event: token      → {"text": "Bi"}
event: token      → {"text": "-Encoder"}
...
event: done       → {"session_id": "..."}
```

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
│   ├── api/              # FastAPI 路由
│   ├── core/             # 配置、日志、异常
│   ├── db/               # SQLAlchemy 模型与会话
│   ├── schemas/          # Pydantic 请求/响应
│   ├── services/         # 业务编排（会话、文档、问答）
│   ├── rag/              # RAG 核心
│   │   ├── loaders.py
│   │   ├── splitter.py
│   │   ├── embeddings.py
│   │   ├── llm.py
│   │   ├── vectorstore.py
│   │   ├── retrievers/   # 向量 / BM25 / 混合 / 重排
│   │   ├── chains/       # Prompt / QA / Condense
│   │   ├── pipeline/     # 索引 / 查询管线
│   │   └── evaluation/   # RAGAS 评估
│   └── utils/
├── data/
│   ├── raw/              # 上传的文档
│   ├── chroma/           # 向量库持久化
│   ├── hf_cache/         # 模型缓存
│   └── eval/             # Golden Set 和评估结果
├── scripts/              # CLI 工具
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 设计取舍

- **为什么用 Chroma 而不是 Milvus**：项目定位是中小规模知识库，Chroma 零运维；生产部署可无缝替换为 Milvus/Qdrant（接口抽象已就位）
- **为什么用 bge-small 而不是 bge-large**：开发阶段用轻量模型迭代快；`EMBEDDING_MODEL` 一行配置即可切换
- **为什么 Rerank 用 Cross-Encoder 而不是 LLM Rerank**：Cross-Encoder 延迟低一个数量级，精度已足够；LLM Rerank 成本高、延迟大
- **为什么用 SQLite 而不是 PostgreSQL**：单机部署零运维；通过 SQLAlchemy 抽象，切换只需改 `DB_URL`
- **为什么评估单独跑脚本而不是集成到 API**：评估是离线任务，不应该占用线上资源

## 后续规划

- [ ] Web 前端（文档管理 + 对话界面）
- [ ] 一键重建索引 / 文档热更新
- [ ] 支持 Agent 思考模式（ReAct / Plan-and-Solve）
- [ ] 多租户与用户认证
- [ ] Alembic 数据库迁移

## License

MIT