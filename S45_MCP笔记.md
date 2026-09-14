# S45 MCP 笔记

## 一、MCP 是什么

MCP（Model Context Protocol，模型上下文协议）是一个**开放标准**，用来规范
“AI 应用如何连接外部工具和数据”。

它常被类比成 **AI 世界的 USB 接口**：

- 没有 MCP：每个 AI 应用都要自己写对接 GitHub、数据库、文件系统的代码，重复造轮子；
- 有了 MCP：工具方只需要写一个 MCP Server，任何支持 MCP 的 AI 应用都能直接接入。

MCP 由 Anthropic 提出并开源，基于 JSON-RPC 2.0，现在已被多家 AI 应用和工具支持。

## 二、三个角色

| 角色 | 是什么 | 例子 |
| --- | --- | --- |
| Host（宿主） | 用户实际使用的 AI 应用，负责发起请求、管理会话 | Codex、Claude Desktop、IDE 插件 |
| Client（客户端） | Host 内部负责连接某个 MCP Server 的组件，一次连接对应一个 Server | Host 为每个 Server 创建一个 Client |
| Server（服务端） | 对外提供工具/数据/提示模板的一方 | 文件系统 Server、GitHub Server、数据库 Server |

关系图：

```text
Host（AI 应用）
 ├── Client A ──> Server A（文件系统工具）
 ├── Client B ──> Server B（GitHub 工具）
 └── Client C ──> Server C（数据库工具）
```

要点：

- 一个 Host 可以连接多个 Client；
- 一个 Client 通常只连一个 Server；
- Server 可以是本地进程（stdio），也可以是远程服务（HTTP）。

## 三、Server 提供的三类能力

| 类型 | 作用 | 例子 |
| --- | --- | --- |
| Tools | 可被模型调用的函数，会执行动作 | 读文件、发请求、查数据库、发消息 |
| Resources | 可读取的数据，供模型作为上下文 | 文件内容、配置、日志、API 响应 |
| Prompts | 预置的提示模板，供用户选择 | “代码审查模板”“周报模板” |

现在阶段只需要重点掌握 **Tools**，因为它和已经学过的 function calling 直接对应。

## 四、通信方式（传输层）

| 传输方式 | 场景 | 说明 |
| --- | --- | --- |
| stdio | 本地工具 | Host 启动 Server 进程，通过标准输入输出通信 |
| Streamable HTTP | 远程工具 | 通过 HTTP 访问远程 Server（较新标准） |
| HTTP + SSE（旧） | 远程工具 | 早期方案，逐步被 Streamable HTTP 取代 |

## 五、一次 MCP 调用的流程

```text
1. Client 连接 Server，双方协商能力（initialize）
2. Client 获取工具清单（tools/list）
3. 模型根据清单决定调用某个工具（tool_calls）
4. Client 发起调用（tools/call），传参数
5. Server 执行工具并返回结果
6. 结果作为工具消息回传给模型
7. 模型继续判断：继续调用工具 / 给出最终答案
```

和手写工具调用的流程完全一致，区别只是“工具存在于 Server 里，通过协议调用”。

## 六、MCP 与手写 function calling 的对比

| 对比项 | 手写 function calling | MCP |
| --- | --- | --- |
| 工具定义 | 自己写 JSON Schema | Server 用标准协议声明 |
| 工具执行 | 在本程序里调函数 | Client 请求 Server 执行 |
| 复用范围 | 只在自己的程序里 | 任何支持 MCP 的 Host 都能用 |
| 传输 | 函数调用 | JSON-RPC（stdio 或 HTTP） |
| 能力发现 | 自己维护列表 | 通过 tools/list 动态发现 |
| 适用场景 | 单应用内部工具 | 跨应用、跨团队、可复用工具 |

相同点：**模型仍然只负责“决定调用”，真正执行在外部，结果必须回传。**

## 七、什么时候该用 MCP

适合：

- 工具要在多个 AI 应用之间复用；
- 想把本地能力（文件、Git、数据库、浏览器）标准化暴露给 Agent；
- 企业里做统一工具网关、权限和审计。

不需要：

- 只有一个应用、一个简单函数 → 直接写工具函数更简单；
- 工具调用逻辑非常定制、没有复用需求。

## 八、安全注意点

- 工具权限最小化：只暴露必要能力，不开放整盘目录；
- 参数校验：路径越界、命令注入都要在 Server 端拦截；
- 用户确认：危险操作（删除、发送、支付）必须人工审批；
- 防提示注入：工具返回的内容只能当数据，不能当指令；
- 密钥不进工具参数：敏感信息放在 Server 的受控环境里；
- 审计日志：记录谁在什么时候调用了什么工具。

## 九、后续会用到

- S46：接入一个现成的 MCP Server，让 Agent 调用外部工具；
- S47：自己写一个 MCP 工具 Server；
- 项目 A/B：把检索、文件读取等能力封装成工具，接入 Agent。

## 十、自测

1. Host、Client、Server 分别是什么？
2. MCP 解决的核心问题是什么？
3. MCP 的 Tools 和手写 tool calling 有什么相同和不同？
4. 什么情况下不需要用 MCP？
5. MCP 的安全风险有哪些？至少说出三条。

## 十一、自测参考答案

1. Host 是用户使用的 AI 应用；Client 是 Host 内部负责与 Server 通信的组件；
   Server 是提供工具/数据的一方。
2. 解决“AI 应用与外部工具对接方式不统一、无法复用”的问题，把工具标准化。
3. 相同：模型决定调用、外部执行、结果回传；不同：MCP 用标准协议动态发现和调用，
   工具可跨应用复用。
4. 单应用内部、简单定制功能，直接用函数或手写 tool calling 更省事。
5. 权限过大、参数注入、工具输出提示注入、密钥泄露、缺少审计与人工确认等。