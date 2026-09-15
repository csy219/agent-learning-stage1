# S48 多 Agent 设计笔记

## 一、核心原则

> 能用单 Agent + 好工具解决，就不要上多 Agent。

多 Agent 不是“更高级”，它的代价是：

- 调用次数成倍增加 → 成本更高；
- 多了协调和通信 → 延迟更大；
- 多份状态和上下文 → 一致性更难保证；
- 出错时很难定位是哪个 Agent 的问题 → 调试更难。

它只在单 Agent 出现**明确瓶颈**时才有价值。

## 二、判断流程

```text
1. 单 Agent + 好工具能不能做？
     能 → 就用单 Agent，别引入多 Agent
     不能 ↓
2. 瓶颈是什么？
     上下文过载 / 角色冲突 / 可并行 / 权限隔离 / 需要独立验证 / 任务过长
     ↓
3. 选择对应编排模式（见第三节）
     ↓
4. 定义六件事：接口、状态、权限、终止条件、可观测性、成本预算
     ↓
5. 先做最小版本，用评测验证是否真的比单 Agent 更好
```

## 三、五种常见编排模式

| 模式 | 结构 | 适用场景 | 优点 | 缺点 |
| --- | --- | --- | --- | --- |
| Supervisor（主管-工人） | 主管拆任务，分派给多个工人，再汇总 | 任务可拆成 2–4 个子任务 | 职责清晰、最常用、好扩展 | 主管容易成为瓶颈；接口要设计好 |
| Sequential（流水线） | A → B → C 顺序执行 | 阶段严格依赖上一阶段输出 | 流程简单、易调试 | 无法并行；一步慢全慢 |
| Parallel / Map-Reduce | 分发 → 并行处理 → 汇总 | 批量处理同类任务（多篇论文、多条评论） | 延迟低、吞吐高 | 需要汇总逻辑；注意限流与失败重试 |
| Generator + Critic | 生成 → 评审 → 不通过打回 | 质量要求高的内容（报告、代码、简历） | 质量提升明显 | 成本翻倍；必须设最大轮数 |
| Handoff / Swarm | 同级 Agent 互相转交控制权 | 复杂对话、角色切换 | 灵活 | 最难调试，容易失控 |

选择建议：

- 项目 A（文档知识库问答）：单 Agent + 检索工具即可，**不需要多 Agent**；
- 项目 B（论文阅读助手）：Supervisor + 3–4 个工人比较合适；
- 批量摘要/审核：Parallel；
- 代码审查、报告生成：Generator + Critic。

## 四、多 Agent 设计必须定清楚的六件事

### 1. 接口（输入 / 输出）

- 每个 Agent 的输入输出必须是**明确结构**，建议 Pydantic/JSON；
- 不要让 Agent 之间传自然语言长段落，容易丢信息、难校验；
- 示例：Retriever 的输出 = `{"chunks": [{"text": ..., "source": ..., "page": ...}]}`。

### 2. 状态（共享 vs 隔离）

- 共享状态越大，越容易互相污染、越难调试；
- 只共享必要字段，其余放各自的局部上下文；
- 示例：Supervisor 共享 `task`、`plan`、`results`；每个 Worker 只拿自己需要的子任务。

### 3. 权限（最小权限）

- 每个 Agent 只拿完成自己工作所需的工具；
- 只读 Agent 不给写权限；写文件/发消息的 Agent 单独隔离；
- 危险操作必须走 Human-in-the-loop（S42 的知识）。

### 4. 终止条件

- 循环上限：Supervisor 最多分派几轮；
- 重试上限：Critic 最多打回几次；
- 失败兜底：超时、工具连续失败、结果为空时如何退出；
- 没有终止条件的多 Agent = 烧钱机器。

### 5. 可观测性

- 每次调用要有 trace：谁调用了谁、输入输出、耗时、token、失败原因；
- 工具：LangSmith / Langfuse（S50 会专门学）；
- 没有 trace，多 Agent 出问题基本无法排查。

### 6. 成本与延迟预算

- 先估算：Agent 数量 × 平均轮数 × 单次 token；
- 设置上限：最大轮数、最大 token、超时；
- 能并行的并行，能缓存的缓存（S36 的知识）；
- 多 Agent 的成本常常是单 Agent 的 3–10 倍，要能说清收益。

## 五、设计案例：论文阅读助手

**任务**：用户上传论文，Agent 能摘要、能问答、能指出不确定的地方。

**模式选择**：Supervisor + 3 个工人 + 1 个校验者。

```text
用户
 ↓
Supervisor（分析请求，决定分派）
 ├─ Retriever Agent（只读：论文检索工具）
 ├─ Summary Agent（生成：结构化摘要）
 ├─ QA Agent（生成：基于原文问答）
 └─ Verifier Agent（校验：答案是否有原文依据）
 ↓
Supervisor 汇总 → 最终回答
```

**接口定义**

- Supervisor 输入：`{"task": str, "doc_id": str}`
- Retriever 输出：`{"chunks": [{"text": str, "page": int, "score": float}]}`
- Summary 输出：`{"questions": str, "method": str, "conclusions": str}`
- QA 输出：`{"answer": str, "citations": [int]}`
- Verifier 输出：`{"ok": bool, "reason": str}`

**状态设计**

- 共享：`task`、`doc_id`、`plan`、`summary`、`answer`、`citations`
- 隔离：各 Agent 的中间推理过程不共享

**权限设计**

- Retriever：只读文档检索；
- Summary / QA：只能读缓存好的文本，不能访问文件系统；
- Verifier：只读，不给写权限；
- 没有任何 Agent 能删除或修改用户文件。

**终止条件**

- Supervisor 最多分派 3 轮；
- Verifier 最多打回 2 次；
- 超过 60 秒或 token 超预算直接返回已有结果并说明。

**可观测性**

- 每次 Agent 调用记录：角色、输入、输出摘要、耗时、token；
- 失败记录原因，便于复现。

## 六、反模式（要避免）

| 反模式 | 问题 |
| --- | --- |
| 简单任务也上多 Agent | 成本高、收益低 |
| Agent 越多越好 | 协调复杂度爆炸，延迟不可控 |
| 共享一个巨大的 State | 互相污染，问题难以定位 |
| 没有终止条件 | 可能无限循环烧钱 |
| 所有 Agent 共享全部工具 | 权限过大，安全风险 |
| 没有追踪 | 出错无法定位 |
| Agent 之间传自然语言长文 | 信息丢失、难校验、难测试 |

## 七、单 Agent → 多 Agent 的演进路径

```text
第 1 步：单 Agent + 若干工具（S43 已掌握）
第 2 步：单 Agent + 检索/记忆等专用工具
第 3 步：拆出 1 个专职子 Agent（如 Retriever）
第 4 步：Supervisor 统一分派与汇总
第 5 步：加 Verifier 做质量校验
第 6 步：用评测数据验证“多 Agent 是否真的更好”
```

不要跳过第 6 步——没有数据支撑的多 Agent 只是增加了复杂度和成本。

## 八、看什么资料

- B 站搜：多 Agent 编排、LangGraph 多智能体，看 15–30 分钟概念；
- LangGraph 官方文档：Multi-agent；
- Anthropic《Building Effective Agents》：重点看 Workflows vs Agents。

## 九、自测

1. 为什么单 Agent 能解决就别用多 Agent？
2. Supervisor、Sequential、Parallel 分别适合什么场景？
3. 为什么共享状态越大越危险？
4. 设计多 Agent 必须定义哪六件事？
5. 论文阅读助手的 Supervisor 模式里，哪些 Agent 只读、哪些能写？

## 十、自测参考答案

1. 多 Agent 带来更高成本、更长延迟、更难调试；没有明确瓶颈就不值得。
2. Supervisor：任务可拆成 2–4 个子任务；Sequential：阶段严格依赖；
   Parallel：批量处理同类任务。
3. 共享状态越大，Agent 之间越容易互相覆盖、污染上下文，出错难定位。
4. 接口、状态、权限、终止条件、可观测性、成本预算。
5. Retriever 和 Verifier 只读；Summary 和 QA 只在受控文本上生成内容，
   不直接写文件；任何 Agent 都不能删改用户文件。