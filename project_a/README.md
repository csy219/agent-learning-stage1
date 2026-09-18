# PDF 文档知识库问答 Agent

基于 RAG + LangGraph 的文档问答系统：上传 PDF，自动解析入库，提问时检索原文并给出带页码引用的回答。

## 功能

- PDF 上传与自动索引（按页解析、分块、向量化）
- 中文语义检索（BGE 向量 + Chroma）
- LangGraph Agent 自动决定是否调用检索工具
- 回答带原文引用：[文件名 第X页]
- 无相关资料时明确拒答，减少幻觉
- 多轮会话记忆（thread_id）
- 内置评测脚本，输出检索与回答准确率

## 架构

```text
用户
 ↓ 上传 PDF
FastAPI /upload
 ↓
pdf_rag.py：解析 → 分块 → BGE 向量化 → Chroma 入库
 ↓ 提问
FastAPI /ask
 ↓
agent.py：LangGraph Agent ⇄ search_knowledge 工具
 ↓
检索 top-k + 阈值过滤 → 原文片段（带页码）
 ↓
模型基于原文回答 → answer + citations
```

## 技术栈

- Python 3.12
- FastAPI / Uvicorn
- pypdf
- sentence-transformers（BAAI/bge-small-zh-v1.5）
- Chroma
- LangChain / LangGraph
- DeepSeek API

## 目录结构

```text
project_a/
├── app.py              FastAPI 接口
├── agent.py            LangGraph Agent
├── pdf_rag.py          PDF 解析、分块、向量化、检索
├── eval_project_a.py   评测脚本
├── requirements.txt    依赖
├── uploads/            上传目录（不入库 Git）
└── chroma_db/          向量库（不入库 Git）
```

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

配置 `.env`：

```env
DEEPSEEK_API_KEY=sk-你的key
```

启动：

```bash
uvicorn app:app --port 8000
```

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| POST | /upload | 上传 PDF 并建立索引 |
| POST | /ask | 提问，返回回答与引用 |

示例：

```bash
curl.exe -X POST http://127.0.0.1:8000/upload -F "file=@手册.pdf"

curl.exe -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"RAG 的完整流程是什么？\",\"thread_id\":\"user-1\"}"
```

返回：

```json
{
  "answer": "RAG 的完整流程是…… 引用：[手册.pdf 第2页]",
  "citations": [
    {"source": "手册.pdf", "page": 2, "distance": 0.31}
  ]
}
```

## 评测

```bash
python eval_project_a.py
```

输出通过率、检索命中率、回答正确率，明细见 `eval_report.json`。

## 已知限制

- 扫描版 PDF 无法提取文字，需要 OCR
- 目前使用字符窗口分块，后续可改语义分块
- 未接入 reranker 与混合检索
- Checkpointer 使用内存存储，生产建议换 PostgreSQL/SQLite

## 后续计划

- 混合检索（BM25 + 向量）
- Reranker 精排
- 流式输出（SSE）
- 评测接入 CI