# SourceLedger - 可验证的 RAG Runtime

**SourceLedger / 源证**

一个面向企业文档的可验证 RAG 运行时，覆盖文档索引、混合检索、上下文组装、引用追踪、安全防护、任务持久化和 FastAPI 服务化。

![SourceLedger Workbench](docs/source-ledger-workbench.png)

## 核心能力

- PDF 上传、解析、分块、向量化和 Chroma 索引
- fixed / structure / semantic / parent-child 分块消融
- Vector、BM25、RRF Hybrid 检索
- Query rewrite、metadata filter、候选池扩展
- CrossEncoder rerank 实验和回归分析
- Context packing：去重、来源多样性、token 预算
- v1/v2 冲突提示与 citation `[C1]` 追踪
- 直接/间接 Prompt Injection 防护
- 无证据拒答和伪造 citation 检查
- PostgreSQL Run 状态、Checkpoint 和跨进程恢复
- Redis 限流、分布式锁和请求幂等
- FastAPI 上传、会话、问答、任务查询和 SSE 流式接口
- 并发压测、p50/p95、上下文 token 和成本统计

## 架构

```text
React / Client
      |
      v
FastAPI API Layer
      |
      +--> Document Upload / Index
      |
      +--> RAG Runtime
              |
              +--> Query Rewrite
              +--> Metadata Filter
              +--> Vector + BM25 Hybrid
              +--> Rerank (experimental)
              +--> Context Packing / Citation
              |
              +--> PostgreSQL
              |     runs
              |     checkpoints
              |     tool_calls
              |     idempotency_keys
              |
              +--> Redis
                    rate limit
                    distributed lock
```

## 关键指标

检索：

```text
Hit@1              0.9762
Recall@4           0.9881
MRR                0.9881
nDCG@4             0.9763
```

Context Packing：

```text
46 条 case
invalid citation   0
citation recall    1.0
conflict covered   3/3
injection covered  2/2
context tokens avg 451
context tokens max 851
```

Rerank：

```text
修复 E33
回归 E31/E34
CPU 延迟明显上升
默认关闭，仅保留条件触发方向
```

安全回归：

```text
5/5 scenarios passed
```

并发压测：

```text
requests           20
concurrency        5
failed             0
p50                135.01 ms
p95                286.89 ms
context tokens     2400
all_passed         true
```

## API

```text
GET  /health
GET  /ready

POST /documents/upload

POST /sessions
POST /ask
POST /ask/stream
GET  /tasks/{run_id}
```

## 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r project_a\requirements.txt
pip install -r project_a\requirements-db.txt
pip install -r project_a\requirements-resilience.txt
```

配置根目录 `.env`：

```env
DEEPSEEK_API_KEY=your-key
DATABASE_URL=postgresql+psycopg://agent:agent_password@localhost:5433/agent_runtime
REDIS_URL=redis://localhost:6380/0
```

启动 PostgreSQL 和 Redis：

```powershell
cd project_a
docker compose -f .\docker-compose.db.yml up -d
```

应用数据库：

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

启动 FastAPI：

```powershell
.\.venv\Scripts\python.exe -m uvicorn runtime.api.S19_2_app:app --host 127.0.0.1 --port 8000
```

Swagger：

```text
http://127.0.0.1:8000/docs
```

## Workbench 前端

```powershell
cd project_a\frontend

npm.cmd install
npm.cmd run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

Workbench 提供：

- PDF 上传与索引状态
- 标准问答与 SSE 流式问答
- Citation、来源和页码展示
- Run 状态和 Checkpoint 信息
- p50、p95、token、引用召回和 injection 覆盖指标

## 评测

RAG Harness：

```powershell
.\.venv\Scripts\python.exe project_a\evaluation\harness\run_full_suite.py
```

安全回归：

```powershell
cd project_a
.\.venv\Scripts\python.exe -B -m runtime.security.S18_6_security_regression
```

并发压测：

```powershell
cd project_a
.\.venv\Scripts\python.exe -B -m runtime.api.S19_6_load_test --requests 20 --concurrency 5
```

## 已知限制

- Rerank 默认关闭，只保留条件触发研究方向
- 压测使用 fake ask，未包含真实大模型生成延迟
- 流式接口当前先得到完整回答再分片，尚未接入底层 token stream
- 认证、租户隔离和完整权限系统仍待完善
- Docker 沙箱、Coding Agent 和 RepoFix 属于后续项目
