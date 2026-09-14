# 1.
# - asyncio：Python 标准库的异步框架。用它的原因见第 5 段（MCP 通信是异步的）。
# - Path：用面向对象方式表示文件路径，比字符串拼接可靠。
# - MultiServerMCPClient：LangChain 提供的 MCP 适配器，负责：
#   - 启动/连接 MCP Server；
#   - 向 Server 要工具清单；
#   - 把 MCP 工具转换成 LangChain 工具。
# 能得到什么：连接 MCP Server 所需的最小依赖，不涉及模型调用。

import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

# 2.
# - Path("sandbox")：相对当前工作目录的 sandbox 文件夹；
# - .resolve()：转成绝对路径，例如：
# C:\Users\ASUS\Desktop\agent-learningstage1\sandbox
# 为什么必须绝对路径：MCP Server 是独立进程，它的工作目录不一定和你一样；给相对路径它会找错地方。
# 为什么叫 SANDBOX：这是最小权限思想的体现——只把这个目录授权给 Server，它就不能读你电脑别的地方（对应 S35 的安全知识）。

SANDBOX=Path("sandbox").resolve()


# 3.
# - SERVER_CONFIG 是一个字典，key 是 Server 名字（"filesystem"），可以配置多个 Server；
# - "command": "cmd"：
#   - 告诉客户端“用什么程序启动 Server”；
#   - Windows 下不能用 npx（它是 .cmd 脚本，Python 子进程直接执行会失败），所以用 cmd；
# - "args" 是传给这个命令的参数列表：
#   - "/c"：让 cmd 执行完后面的命令后退出，这是 Windows 的固定写法；
#   - "npx"：真正要跑的包管理工具；
#   - "-y"：自动确认下载，不弹交互提示；
#   - "@modelcontextprotocol/server-filesystem"：官方文件系统 MCP Server 包名；
#   - str(SANDBOX)：只允许访问这个目录，其余一律拒绝；
# - "transport": "stdio"：
#   - 传输方式：客户端用标准输入输出和 Server 进程通信；
#   - stdio 适合本地工具；远程工具用 HTTP 传输。
# 能得到什么：一份“怎么启动 Server、授权哪些目录、用什么协议通信”的完整说明书。
# 等价的手写概念：你以前写 base_url 是告诉客户端“去哪找模型”；这里是告诉客户端“去哪启动工具服务”。

SERVER_CONFIG={
    "filename":{
        "command":"cmd",
        "args":[
            "/c",
            "npx",
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(SANDBOX),
        ],
        "transport":"stdio",
    }
}

# 4.
# async def：声明这是一个协程函数，里面可以用 await；
# client = MultiServerMCPClient(SERVER_CONFIG)：- 创建客户端对象；
# - 此时还没有启动 Server，只是拿着配置；
# - 真正启动发生在下一步 get_tools() 时（懒启动）。

async def main():
    client=MultiServerMCPClient(SERVER_CONFIG)

#     这一行内部发生了四件事：
# 1. 按配置启动 Server 进程（cmd /c npx -y ...）；
# 2. 通过 stdio 建立 JSON-RPC 通信；
# 3. 发送 tools/list 请求，问 Server “你有哪些工具”；
# 4. 把返回的 MCP 工具转换成 LangChain 工具对象，放进列表返回。
#    - await：等这一步完成再继续；没有它，拿到的是“未来的结果”而不是列表；
#    - tools：一个工具对象列表，每个对象都有 .name、.description、.ainvoke()。
# 能得到什么：Server 的能力清单。以后无论接哪个 MCP Server，第一步都是 get_tools()。
# 对应手写代码：等价于你 S28 里手写的 tools = [...]，只不过现在是动态从 Server 拿的。
    tools=await client.get_tools() 


    # .splitlines()[0]：只取第一行，因为描述可能很长，多行输出太乱；
    print(f"从 MCP Server 拿到 {len(tools)} 个工具：")
    for tool in tools:
        description = (tool.description or "").splitlines()[0]
        print(f"- {tool.name}: {description[:60]}")


#     if tool.name == "list_directory":：找到“列目录”这个工具；
# await tool.ainvoke({"path": str(SANDBOX)})：- ainvoke 是异步调用；
# - 参数用一个字典传，字典的 key 必须符合工具 schema；
# - list_directory 需要 path 参数，所以传目录路径；
# - await：等 Server 执行完并返回结果；
    for tool in tools:
        if tool.name == "list_directory":
            result = await tool.ainvoke({"path": str(SANDBOX)})
            print("\nlist_directory 返回：")
            print(result)
            break
    else:
        print("\n没有找到 list_directory,请检查上面的工具名。")
if __name__ == "__main__":
    asyncio.run(main())